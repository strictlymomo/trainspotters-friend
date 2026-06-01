import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io

from app.db.database import init_db, get_session, DatabaseService
from app.models.database import Track as DBTrack, SearchResult as DBSearchResult
from app.models.schemas import (
    ScrapeJobRequest, JobResponse, JobListItem, TrackResponse,
    SearchResultResponse, JobProgress, TrackWithResults
)
from app.services.scraper import AsyncMixesDBScraper
from app.services.searcher import AsyncMusicStoreSearcher
from app.services.parser import parse_tracklist
from app.websocket.manager import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="Trainspotter's Friend API",
    description="API for scraping DJ mix tracklists and searching digital music stores",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def run_scraping_job(job_id: str, artist_name: str):
    """Background task to scrape and search for tracks"""
    async for session in get_session():
        db = DatabaseService(session)

        async def progress_callback(message_type: str, data: dict):
            """Callback to send progress updates via WebSocket"""
            await manager.broadcast_progress(job_id, message_type, data)

        try:
            # Update job status to scraping
            await db.update_job_status(job_id, "scraping")

            # Initialize scraper with progress callback
            scraper = AsyncMixesDBScraper(progress_callback=progress_callback)

            # Scrape tracklists
            logger.info(f"Starting scraping for artist: {artist_name}")
            tracklists = await scraper.scrape_artist_tracklists(artist_name)

            if not tracklists:
                await db.update_job_status(
                    job_id,
                    "failed",
                    error_message="No mixes found for this artist"
                )
                await manager.broadcast_progress(job_id, "job_failed", {
                    "error": "No mixes found for this artist"
                })
                return

            # Update progress
            await db.update_job_progress(
                job_id,
                total_mixes=len(tracklists),
                mixes_scraped=len(tracklists)
            )

            # Combine and parse tracklists
            combined_tracklist = scraper.combine_tracklists(tracklists)
            tracks = parse_tracklist(combined_tracklist)

            if not tracks:
                await db.update_job_status(
                    job_id,
                    "failed",
                    error_message="No valid tracks found in tracklists"
                )
                await manager.broadcast_progress(job_id, "job_failed", {
                    "error": "No valid tracks found"
                })
                return

            # Save tracks to database
            db_tracks = [
                DBTrack(
                    job_id=job_id,
                    timestamp=track.timestamp,
                    artist=track.artist,
                    title=track.title,
                    remix_info=track.remix_info
                )
                for track in tracks
            ]
            await db.create_tracks_bulk(db_tracks)

            await db.update_job_progress(
                job_id,
                total_tracks=len(tracks)
            )

            await manager.broadcast_progress(job_id, "parsing_complete", {
                "total_tracks": len(tracks)
            })

            # Update status to searching
            await db.update_job_status(job_id, "searching")

            # Initialize searcher with progress callback
            searcher = AsyncMusicStoreSearcher(progress_callback=progress_callback)

            # Search for each track
            for idx, (db_track, parsed_track) in enumerate(zip(db_tracks, tracks)):
                search_results = await searcher.search_all_platforms(parsed_track)

                # Save search results
                if search_results:
                    db_results = [
                        DBSearchResult(
                            track_id=db_track.id,
                            platform=result.platform,
                            found_artist=result.artist,
                            found_title=result.title,
                            url=result.url,
                            price=result.price
                        )
                        for result in search_results
                    ]
                    await db.create_search_results_bulk(db_results)

                # Update progress
                await db.update_job_progress(
                    job_id,
                    tracks_searched=idx + 1
                )

                await manager.broadcast_progress(job_id, "track_searched", {
                    "track_number": idx + 1,
                    "total_tracks": len(tracks),
                    "results_found": len(search_results)
                })

            # Mark job as completed
            await db.update_job_status(
                job_id,
                "completed",
                completed_at=datetime.utcnow()
            )

            await manager.broadcast_progress(job_id, "job_complete", {
                "total_tracks": len(tracks)
            })

            logger.info(f"Scraping job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Error in scraping job {job_id}: {e}")
            await db.update_job_status(
                job_id,
                "failed",
                error_message=str(e)
            )
            await manager.broadcast_progress(job_id, "job_failed", {
                "error": str(e)
            })


@app.post("/api/jobs/scrape", response_model=JobResponse)
async def create_scrape_job(
    request: ScrapeJobRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Create a new scraping job for an artist"""
    db = DatabaseService(session)

    # Create job in database
    job = await db.create_job(request.artist_name)

    # Start background task
    background_tasks.add_task(run_scraping_job, job.id, request.artist_name)

    return JobResponse(
        job_id=job.id,
        artist_name=job.artist_name,
        status=job.status,
        created_at=job.created_at
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    """Get job status and details"""
    db = DatabaseService(session)
    job = await db.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.id,
        artist_name=job.artist_name,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        progress=JobProgress(
            mixes_scraped=job.mixes_scraped,
            total_mixes=job.total_mixes,
            tracks_searched=job.tracks_searched,
            total_tracks=job.total_tracks
        ),
        error_message=job.error_message
    )


@app.get("/api/jobs", response_model=List[JobListItem])
async def list_jobs(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session)
):
    """List all scraping jobs"""
    db = DatabaseService(session)
    jobs = await db.list_jobs(limit=limit, offset=offset)

    return [
        JobListItem(
            job_id=job.id,
            artist_name=job.artist_name,
            status=job.status,
            created_at=job.created_at,
            total_tracks=job.total_tracks
        )
        for job in jobs
    ]


@app.get("/api/jobs/{job_id}/tracks", response_model=List[TrackResponse])
async def get_job_tracks(job_id: str, session: AsyncSession = Depends(get_session)):
    """Get all tracks for a job"""
    db = DatabaseService(session)

    # Verify job exists
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tracks = await db.get_job_tracks(job_id)

    return [
        TrackResponse(
            id=track.id,
            timestamp=track.timestamp,
            artist=track.artist,
            title=track.title,
            remix_info=track.remix_info
        )
        for track in tracks
    ]


@app.get("/api/jobs/{job_id}/results", response_model=List[TrackWithResults])
async def get_job_results(
    job_id: str,
    platform: Optional[str] = Query(None),
    artist: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """Get search results for a job with optional filters"""
    db = DatabaseService(session)

    # Verify job exists
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tracks = await db.get_job_results(
        job_id=job_id,
        platform=platform,
        artist=artist,
        title=title
    )

    return [
        TrackWithResults(
            timestamp=track.timestamp,
            original_artist=track.artist,
            original_title=track.title,
            remix_info=track.remix_info,
            results=[
                SearchResultResponse(
                    id=result.id,
                    track_id=result.track_id,
                    platform=result.platform,
                    found_artist=result.found_artist,
                    found_title=result.found_title,
                    url=result.url,
                    price=result.price
                )
                for result in track.search_results
            ]
        )
        for track in tracks
    ]


@app.get("/api/jobs/{job_id}/export")
async def export_job_results(
    job_id: str,
    format: str = Query("csv", regex="^(csv|json)$"),
    session: AsyncSession = Depends(get_session)
):
    """Export job results as CSV or JSON"""
    db = DatabaseService(session)

    # Verify job exists
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tracks = await db.get_job_results(job_id=job_id)

    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "timestamp", "original_artist", "original_title", "remix_info",
            "platform", "found_artist", "found_title", "url", "price"
        ])

        for track in tracks:
            for result in track.search_results:
                writer.writerow([
                    track.timestamp,
                    track.artist,
                    track.title,
                    track.remix_info,
                    result.platform,
                    result.found_artist,
                    result.found_title,
                    result.url,
                    result.price
                ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={job.artist_name}_{job_id}.csv"}
        )


@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates"""
    await manager.connect(websocket, job_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Trainspotter's Friend API",
        "docs": "/docs",
        "version": "1.0.0"
    }
