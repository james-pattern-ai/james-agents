import os
import requests
import logging
import time
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from typing import Union, Optional
from models import SessionLocal, Source, Series, Issue, SourceXref, init_db, GradedPrice, MarketListing, PriceSnapshot
from cachetools import TTLCache, cached

# --- Environment Setup & Logging ---
API_USER_AGENT = "RooComicAgent/1.0"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Caching ---
# Cache API responses for 1 hour to reduce redundant lookups
api_cache = TTLCache(maxsize=1024, ttl=3600)

# --- Database Session Management ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Source Management ---
def get_or_create_source(db: Session, name: str, url: str) -> Source:
    """Gets or creates a data source record with robust error handling."""
    try:
        source = db.query(Source).filter(Source.name == name).first()
        if not source:
            logging.info(f"Creating new source: {name}")
            source = Source(name=name, url=url)
            db.add(source)
            db.commit()
            db.refresh(source)
        return source
    except SQLAlchemyError as e:
        logging.error(f"Database error while getting or creating source '{name}': {e}")
        db.rollback()
        raise

# --- API Request Abstraction with Retry Logic ---
def _make_api_request(url: str, params: dict, headers: dict) -> dict:
    """Makes an API request with caching, error handling, and retries."""
    cache_key = f"{url}?{str(sorted(params.items()))}"
    
    if cache_key in api_cache:
        logging.info(f"Returning cached response for {url}")
        return api_cache[cache_key]

    for attempt in range(3): # Retry up to 3 times
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            api_cache[cache_key] = data # Cache successful response
            return data
        except requests.exceptions.HTTPError as e:
            logging.warning(f"HTTP Error: {e.response.status_code} for URL {url} on attempt {attempt + 1}")
            if e.response.status_code in [401, 403, 404]:
                break # Don't retry on auth or not found errors
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed for {url} on attempt {attempt + 1}: {e}")
        
        time.sleep(2 ** attempt) # Exponential backoff

    logging.error(f"API request failed for {url} after multiple retries.")
    return {}

# --- Comic Vine Integration ---
def search_comicvine_volume(series_title: str) -> list:
    """Searches for a volume (series) on Comic Vine."""
    api_key = os.getenv("COMICVINE_KEY")
    if not api_key:
        logging.error("COMICVINE_KEY environment variable not set.")
        return []
        
    params = {
        "api_key": api_key, "format": "json", "query": series_title, "resources": "volume",
    }
    data = _make_api_request("https://comicvine.gamespot.com/api/search/", params, {"User-Agent": API_USER_AGENT})
    return data.get("results", [])

def get_comicvine_issues_for_volume(volume_id: int) -> list:
    """Gets all issues for a specific Comic Vine volume ID."""
    api_key = os.getenv("COMICVINE_KEY")
    if not api_key:
        logging.error("COMICVINE_KEY environment variable not set.")
        return []

    params = {
        "api_key": api_key, "format": "json", "filter": f"volume:{volume_id}", "sort": "issue_number:asc",
    }
    data = _make_api_request("https://comicvine.gamespot.com/api/issues/", params, {"User-Agent": API_USER_AGENT})
    return data.get("results", [])

def get_or_create_issue_from_comicvine(
    db: Session, series_title: str, issue_number: str
) -> Optional[Issue]:
    """
    High-level function to reliably find or create comic records from Comic Vine
    and persist them in the local database. Optimizes database lookups.
    """
    try:
        # Optimized lookup for existing issue
        issue = (
            db.query(Issue)
            .join(Series)
            .filter(Series.title.ilike(f"%{series_title}%"), Issue.issue_number == issue_number)
            .options(joinedload(Issue.series)) # Eager load relationships
            .first()
        )
        if issue:
            logging.info(f"Found existing issue for '{series_title} #{issue_number}' in DB.")
            return issue

        # Find or create the series
        series = _get_or_create_series_from_comicvine(db, series_title)
        if not series:
            return None # Error logged in helper

        # Find or create the issue for that series
        return _get_or_create_issue_for_series(db, series, issue_number)

    except SQLAlchemyError as e:
        logging.error(f"Database error during Comic Vine lookup for '{series_title} #{issue_number}': {e}")
        db.rollback()
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during Comic Vine lookup: {e}", exc_info=True)
        db.rollback()
        return None

def _get_or_create_series_from_comicvine(db: Session, series_title: str) -> Optional[Series]:
    """Helper to find a series in the DB or create it from Comic Vine data."""
    series = db.query(Series).filter(Series.title.ilike(f"%{series_title}%")).first()
    if series:
        return series

    logging.info(f"Series '{series_title}' not in DB. Searching Comic Vine.")
    volumes = search_comicvine_volume(series_title)
    if not volumes:
        logging.warning(f"Could not find volume for '{series_title}' on Comic Vine.")
        return None

    cv_volume = volumes[0]  # Assume first result is correct
    try:
        series = Series(
            title=cv_volume.get("name", series_title),
            publisher=cv_volume.get("publisher", {}).get("name"),
            start_year=int(cv_volume.get("start_year")) if cv_volume.get("start_year") else None,
            cover_url=cv_volume.get("image", {}).get("original_url"),
        )
        db.add(series)
        db.flush()  # Use flush to get series.id for the xref

        cv_source = get_or_create_source(db, name="Comic Vine", url="https://comicvine.gamespot.com")
        xref = SourceXref(
            source_id=cv_source.id, entity_type='series', entity_id=series.id, external_id=str(cv_volume['id'])
        )
        db.add(xref)
        db.commit()
        logging.info(f"Created new series '{series.title}' (ID: {series.id}) from Comic Vine.")
        return series
    except SQLAlchemyError as e:
        logging.error(f"DB error creating series '{series_title}': {e}")
        db.rollback()
        return None


def _get_or_create_issue_for_series(db: Session, series: Series, issue_number: str) -> Optional[Issue]:
    """Helper to create a specific issue for a known series from Comic Vine data."""
    cv_source = get_or_create_source(db, name="Comic Vine", url="https://comicvine.gamespot.com")
    xref_series = db.query(SourceXref).filter_by(source_id=cv_source.id, entity_type='series', entity_id=series.id).first()

    if not xref_series:
        logging.warning(f"Could not find Comic Vine cross-reference for series '{series.title}'")
        return None

    cv_issues = get_comicvine_issues_for_volume(int(xref_series.external_id))
    found_cv_issue = next((iss for iss in cv_issues if iss.get("issue_number") == issue_number), None)

    if not found_cv_issue:
        logging.warning(f"Could not find issue #{issue_number} for '{series.title}' on Comic Vine.")
        return None

    try:
        issue = Issue(
            series_id=series.id,
            issue_number=found_cv_issue.get("issue_number", issue_number),
            cover_date=found_cv_issue.get("cover_date"),
            cover_url=found_cv_issue.get("image", {}).get("original_url"),
        )
        db.add(issue)
        db.flush()

        xref = SourceXref(
            source_id=cv_source.id, entity_type='issue', entity_id=issue.id, external_id=str(found_cv_issue['id'])
        )
        db.add(xref)
        db.commit()
        logging.info(f"Created new issue '{series.title} #{issue.issue_number}' (ID: {issue.id}) from Comic Vine.")
        return issue
    except SQLAlchemyError as e:
        logging.error(f"DB error creating issue '{series.title} #{issue_number}': {e}")
        db.rollback()
        return None


# --- GoCollect & eBay Integration ---
@cached(cache=api_cache)
def get_gocollect_pricing(comic_id: str, grade: str) -> dict:
    """Fetches pricing data from GoCollect, with caching and error handling."""
    api_key = os.getenv("GOCOLLECT_KEY")
    if not api_key:
        logging.error("GOCOLLECT_KEY environment variable not set.")
        return {}
    
    params = {"grade": grade}
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": API_USER_AGENT}
    return _make_api_request(f"https://api.gocollect.com/v1/insights/item/{comic_id}", params, headers)

@cached(cache=api_cache)
def search_ebay_listings(query: str) -> list:
    """Searches for comic listings on eBay, with caching and error handling."""
    api_key = os.getenv("EBAY_TOKEN")
    if not api_key:
        logging.error("EBAY_TOKEN environment variable not set.")
        return []

    params = {"q": query, "category_ids": "63", "limit": "50"} # Increased limit for better sampling
    headers = {"Authorization": f"Bearer {api_key}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"}
    data = _make_api_request("https://api.ebay.com/buy/browse/v1/item_summary/search", params, headers)
    return data.get("itemSummaries", [])

def update_pricing_for_issue(db: Session, issue: Issue, grade_guess: float):
    """
    Fetches and stores pricing from GoCollect and eBay with improved robustness.
    """
    grade_str = f"{grade_guess:.1f}"
    
    # 1. Update from GoCollect
    _update_gocollect_pricing(db, issue, grade_str)

    # 2. Update from eBay
    _update_ebay_listings(db, issue)

def _update_gocollect_pricing(db: Session, issue: Issue, grade_str: str):
    """Helper to handle GoCollect pricing updates."""
    gocollect_source = get_or_create_source(db, name="GoCollect", url="https://gocollect.com")
    xref = db.query(SourceXref).filter_by(source_id=gocollect_source.id, entity_type='issue', entity_id=issue.id).first()
    
    if not xref:
        logging.warning(f"GoCollect cross-reference not found for '{issue.series.title} #{issue.issue_number}'. Skipping pricing.")
        return

    try:
        pricing_data = get_gocollect_pricing(xref.external_id, grade_str)
        if not pricing_data:
             logging.warning(f"No GoCollect pricing data returned for ID {xref.external_id}.")
             return

        fmv = pricing_data.get('value')
        if not fmv:
            logging.info(f"No GoCollect FMV found for {issue.series.title} #{issue.issue_number} at grade {grade_str}.")
            return

        snapshot = PriceSnapshot(issue_id=issue.id, source_id=gocollect_source.id, payload=pricing_data)
        db.add(snapshot)
        db.flush()

        conservative_value = float(fmv) * 0.8
        graded_price = GradedPrice(
            snapshot_id=snapshot.id, grade_label=grade_str, fmv_usd=fmv, conservative_value_usd=conservative_value
        )
        db.add(graded_price)
        db.commit()
        logging.info(f"Successfully logged GoCollect pricing for {issue.series.title} #{issue.issue_number} [{grade_str}]")
    except SQLAlchemyError as e:
        logging.error(f"DB error updating GoCollect pricing: {e}")
        db.rollback()
    except Exception as e:
        logging.error(f"Unexpected error during GoCollect update: {e}", exc_info=True)
        db.rollback()

def _update_ebay_listings(db: Session, issue: Issue):
    """Helper to handle eBay listing updates."""
    try:
        search_query = f'"{issue.series.title}" "{issue.issue_number}"'
        ebay_listings = search_ebay_listings(search_query)
        
        if not ebay_listings:
            logging.info(f"No eBay listings found for '{search_query}'.")
            return

        ebay_source = get_or_create_source(db, name="eBay", url="https://www.ebay.com")
        snapshot = PriceSnapshot(
            issue_id=issue.id, source_id=ebay_source.id, payload={"listings": ebay_listings}
        )
        db.add(snapshot)
        db.flush()

        for item in ebay_listings:
            price_info = item.get("price", {})
            listing = MarketListing(
                snapshot_id=snapshot.id,
                listing_id=item.get("itemId"),
                title=item.get("title"),
                url=item.get("itemWebUrl"),
                price_usd=price_info.get("value"),
                currency=price_info.get("currency"),
                condition=item.get("condition"),
            )
            db.add(listing)
        db.commit()
        logging.info(f"Successfully logged {len(ebay_listings)} eBay listings for {issue.series.title} #{issue.issue_number}")
    except SQLAlchemyError as e:
        logging.error(f"DB error updating eBay listings: {e}")
        db.rollback()
    except Exception as e:
        logging.error(f"Unexpected error during eBay update: {e}", exc_info=True)
        db.rollback()

if __name__ == "__main__":
    logging.info("Running data_manager tests...")
    init_db() 
    db = next(get_db())

    # --- Test Case 1: Fetch a known comic ---
    comic_series = "Amazing Spider-Man"
    comic_issue = "101"
    logging.info(f"--- Attempting to fetch '{comic_series} #{comic_issue}' ---")

    # Ensure API keys are set for the test
    if not all(os.getenv(key) for key in ["COMICVINE_KEY", "GOCOLLECT_KEY", "EBAY_TOKEN"]):
        logging.warning("API keys not set. Skipping live API tests.")
    else:
        # Get issue from Comic Vine
        issue_obj = get_or_create_issue_from_comicvine(db, comic_series, comic_issue)

        if issue_obj:
            logging.info(f"Successfully fetched or created issue: {issue_obj.series.title} #{issue_obj.issue_number}")
            
            # Manually create a GoCollect cross-ref for testing since search is a placeholder
            gocollect_source = get_or_create_source(db, name="GoCollect", url="https://gocollect.com")
            xref = db.query(SourceXref).filter_by(source_id=gocollect_source.id, entity_type='issue', entity_id=issue_obj.id).first()
            if not xref:
                logging.info("Creating mock GoCollect cross-reference for testing.")
                mock_gocollect_id = "93358" # Real ID for ASM #101
                xref = SourceXref(source_id=gocollect_source.id, entity_type='issue', entity_id=issue_obj.id, external_id=mock_gocollect_id)
                db.add(xref)
                db.commit()

            # Update pricing information
            logging.info("--- Updating pricing information ---")
            update_pricing_for_issue(db, issue_obj, 8.0)
            
            # Verify data
            price_entry = db.query(GradedPrice).join(PriceSnapshot).filter(PriceSnapshot.issue_id == issue_obj.id).first()
            if price_entry:
                logging.info(f"Verified pricing entry: Grade {price_entry.grade_label}, FMV: ${price_entry.fmv_usd}")
            else:
                logging.error("Failed to create a pricing entry for the test issue.")
                
        else:
            logging.error(f"Could not fetch or create the test issue '{comic_series} #{comic_issue}'.")

    # --- Test Case 2: Handle a non-existent comic ---
    logging.info("\n--- Attempting to fetch a non-existent comic ---")
    non_existent_issue = get_or_create_issue_from_comicvine(db, "Totally Fake Comic Series 123", "1")
    if not non_existent_issue:
        logging.info("Correctly handled non-existent comic lookup.")
    else:
        logging.error("Test failed: A non-existent comic should not return an issue object.")

    db.close()
    logging.info("\n--- data_manager tests complete ---")
