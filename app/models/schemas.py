from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ScrapeJobRequest(BaseModel):
    artist_name: str = Field(..., min_length=1, description="Artist name to scrape from MixesDB")


class JobProgress(BaseModel):
    mixes_scraped: int
    total_mixes: int
    tracks_searched: int
    total_tracks: int


class JobResponse(BaseModel):
    job_id: str
    artist_name: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    progress: Optional[JobProgress] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    job_id: str
    artist_name: str
    status: str
    created_at: datetime
    total_tracks: int

    class Config:
        from_attributes = True


class TrackResponse(BaseModel):
    id: int
    timestamp: str
    artist: str
    title: str
    remix_info: Optional[str] = None

    class Config:
        from_attributes = True


class SearchResultResponse(BaseModel):
    id: int
    track_id: int
    platform: str
    found_artist: Optional[str] = None
    found_title: Optional[str] = None
    url: str
    price: Optional[str] = None

    class Config:
        from_attributes = True


class TrackWithResults(BaseModel):
    timestamp: str
    original_artist: str
    original_title: str
    remix_info: Optional[str] = None
    results: List[SearchResultResponse]


class WebSocketMessage(BaseModel):
    type: str
    data: dict


class ExportFormat(str):
    CSV = "csv"
    JSON = "json"
