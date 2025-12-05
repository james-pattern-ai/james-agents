#!/usr/bin/env python3
import os
import logging
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import custom modules
from data_manager import get_db, get_or_create_issue_from_comicvine, update_pricing_for_issue
from models import init_db, Issue, GradedPrice, Series, PriceSnapshot
from sqlalchemy.orm import joinedload

# --- Configuration & Initialization ---
IMAGE_FOLDER = 'sample_comics'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_database():
    """Initializes the database and returns a session."""
    logging.info("Initializing database...")
    # Use a local SQLite DB by default
    os.environ.setdefault('DATABASE_URL', 'sqlite:///./comics.db')
    init_db()
    logging.info("Database ready.")
    return next(get_db())

# --- Placeholder for Gemma Vision Processing ---
def process_comic_image_mock(image_name: str) -> dict:
    """
    Placeholder for Gemma vision processing.
    Returns mock data based on filename for testing purposes.
    """
    logging.info(f"Processing image with mock vision model: {image_name}")
    details = {
        'series_title': 'Amazing Spider-Man', 'issue_number': '101', 'publisher': 'Marvel',
        'publication_year': '1971', 'defects': 'spine_tick', 'condition_confidence': 0.85
    }
    if "Batman" in image_name:
        details.update({'series_title': 'Batman', 'issue_number': '555', 'defects': 'spine_tick, corner_blunt'})
    elif "Muse" in image_name:
        details.update({'series_title': 'Muse', 'issue_number': '1', 'defects': 'crease_light', 'condition_confidence': 0.90})
    elif "Soul_Saga_1" in image_name:
        details.update({'series_title': 'Soul Saga', 'issue_number': '1', 'defects': 'no_defects', 'condition_confidence': 0.98})
    
    return details
    
def list_image_files(folder_path: str) -> list:
    """Lists image files in a specified folder, handling errors gracefully."""
    try:
        return [
            {'id': os.path.join(folder_path, f), 'name': f}
            for f in os.listdir(folder_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
    except FileNotFoundError:
        logging.error(f"Image directory not found at '{folder_path}'.")
        return []

# --- Grading Logic ---
def apply_grading_rules(defects: str) -> float:
    """Calculates a grade based on detected defects."""
    base_grade = 10.0
    deductions = {'spine_tick': -0.5, 'rubbing_light': -0.5, 'crease_light': -1.0, 'corner_blunt': -0.5, 'no_defects': 0.0}
    total_deduction = sum(deductions.get(d.strip(), 0) for d in defects.split(','))
    return max(0.0, base_grade + total_deduction)

# --- Core Workflow Functions ---
def process_single_comic(db: Session, image_file: dict):
    """Orchestrates the processing for a single comic book image."""
    logging.info(f"--- Processing {image_file['name']} ---")
    
    try:
        # 1. Get comic details from vision model (mock)
        vision_data = process_comic_image_mock(image_file['name'])
        logging.info(f"Vision Result: {vision_data['series_title']} #{vision_data['issue_number']}, Defects: {vision_data['defects']}")

        # 2. Get or create the issue record from Comic Vine
        issue = get_or_create_issue_from_comicvine(db, vision_data['series_title'], vision_data['issue_number'])
        
        if not issue:
            logging.warning(f"Failed to get or create issue for {image_file['name']}. Skipping pricing.")
            return

        # 3. Apply grading and update pricing
        grade_guess = apply_grading_rules(vision_data['defects'])
        logging.info(f"Auto Grade Guess: {grade_guess:.1f}")
        
        update_pricing_for_issue(db, issue, grade_guess)
        
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing {image_file['name']}: {e}", exc_info=True)
        db.rollback()

def verify_processed_data(db: Session):
    """Queries and prints the processed data for verification."""
    logging.info("\n--- Verification Step ---")
    
    try:
        issues = (db.query(Issue)
                    .join(Series)
                    .options(joinedload(Issue.series))
                    .order_by(Series.title, Issue.issue_number)
                    .all())
        if not issues:
            logging.info("No issues found in the database to verify.")
            return

        for issue in issues:
            logging.info(f"\nVerifying data for: {issue.series.title} #{issue.issue_number}")
            
            # Eager load pricing data to avoid N+1 queries
            prices = (db.query(GradedPrice)
                        .join(PriceSnapshot)
                        .filter(PriceSnapshot.issue_id == issue.id)
                        .all())
            
            if prices:
                logging.info("  Found Graded Pricing Data:")
                for p in prices:
                    logging.info(f"    - Grade: {p.grade_label}, FMV: ${p.fmv_usd}, Conservative: ${p.conservative_value_usd}")
            else:
                logging.info("  No graded pricing found for this issue.")

    except Exception as e:
        logging.error(f"An error occurred during verification: {e}", exc_info=True)

# --- Main Execution ---
def main():
    """Main function to run the comic processing workflow."""
    db_session = None
    try:
        if not all(os.getenv(k) for k in ['COMICVINE_KEY', 'GOCOLLECT_KEY', 'EBAY_TOKEN']):
            logging.warning("One or more API keys are not set. Please create a .env file or set them manually.")
        
        db_session = setup_database()
        image_files = list_image_files(IMAGE_FOLDER)
        logging.info(f"Found {len(image_files)} image files to process.")
        
        for file in image_files:
            process_single_comic(db_session, file)
            
        verify_processed_data(db_session)
        
    finally:
        if db_session:
            db_session.close()
        logging.info("\n--- Workflow Complete ---")

if __name__ == "__main__":
    main()