from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    artist_name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")  # pending, scraping, searching, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Progress tracking
    total_mixes = Column(Integer, default=0)
    mixes_scraped = Column(Integer, default=0)
    total_tracks = Column(Integer, default=0)
    tracks_searched = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Relationships
    tracks = relationship("Track", back_populates="job", cascade="all, delete-orphan")


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)

    timestamp = Column(String, nullable=False)  # HH:MM:SS format
    artist = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    remix_info = Column(String, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="tracks")
    search_results = relationship("SearchResult", back_populates="track", cascade="all, delete-orphan")


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)

    platform = Column(String, nullable=False, index=True)
    found_artist = Column(String, nullable=True)
    found_title = Column(String, nullable=True)
    url = Column(Text, nullable=False)
    price = Column(String, nullable=True)

    # Relationships
    track = relationship("Track", back_populates="search_results")
