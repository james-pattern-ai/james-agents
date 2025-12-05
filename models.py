# models.py
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Numeric,
    BIGINT,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import os

# Use JSON for sqlite since JSONB is postgres-specific
from sqlalchemy.types import JSON

Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./comics.db")

# Use JSON for SQLite compatibility, and JSONB for Postgres
if DATABASE_URL.startswith("postgresql"):
    JsonType = JSONB
else:
    JsonType = JSON

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

class Source(Base):
    __tablename__ = 'source'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    url = Column(Text, nullable=False)

class Series(Base):
    __tablename__ = 'series'
    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_id = Column(String, unique=True)
    title = Column(String, nullable=False)
    publisher = Column(String)
    start_year = Column(Integer)
    cover_url = Column(Text)
    issues = relationship("Issue", back_populates="series")

class Issue(Base):
    __tablename__ = 'issue'
    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(BIGINT, ForeignKey('series.id', ondelete='CASCADE'), nullable=False)
    issue_number = Column(String, nullable=False)
    cover_date = Column(DateTime)
    cover_url = Column(Text)
    series = relationship("Series", back_populates="issues")
    __table_args__ = (UniqueConstraint('series_id', 'issue_number', name='_series_issue_uc'),)

class SourceXref(Base):
    __tablename__ = 'source_xref'
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey('source.id'), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(BIGINT, nullable=False)
    external_id = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('source_id', 'entity_type', 'external_id', name='_source_entity_external_uc'),)

class PriceSnapshot(Base):
    __tablename__ = 'price_snapshot'
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    issue_id = Column(BIGINT, ForeignKey('issue.id', ondelete='CASCADE'), nullable=False)
    source_id = Column(Integer, ForeignKey('source.id'), nullable=False)
    observed_at = Column(DateTime(timezone=True), server_default=func.now())
    payload = Column(JsonType, nullable=False)
    graded_prices = relationship("GradedPrice", back_populates="snapshot")
    market_listings = relationship("MarketListing", back_populates="snapshot")

class GradedPrice(Base):
    __tablename__ = 'graded_price'
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    snapshot_id = Column(BIGINT, ForeignKey('price_snapshot.id', ondelete='CASCADE'), nullable=False)
    grade_label = Column(String, nullable=False)
    fmv_usd = Column(Numeric(12, 2))
    conservative_value_usd = Column(Numeric(12, 2)) # New field for 80% value
    snapshot = relationship("PriceSnapshot", back_populates="graded_prices")

class MarketListing(Base):
    __tablename__ = 'market_listing'
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    snapshot_id = Column(BIGINT, ForeignKey('price_snapshot.id', ondelete='CASCADE'), nullable=False)
    listing_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(Text)
    price_usd = Column(Numeric(12, 2))
    currency = Column(String)
    condition = Column(String)
    ended_at = Column(DateTime(timezone=True))
    snapshot = relationship("PriceSnapshot", back_populates="market_listings")

def init_db():
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized.")