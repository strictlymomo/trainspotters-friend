import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_database
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.database import Base, Job, Track, SearchResult


# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./trainspotters.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


class DatabaseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, artist_name: str) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            artist_name=artist_name,
            status="pending",
            created_at=datetime.utcnow()
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[Job]:
        job = await self.get_job(job_id)
        if job:
            job.status = status
            if error_message:
                job.error_message = error_message
            if completed_at:
                job.completed_at = completed_at
            await self.session.commit()
            await self.session.refresh(job)
        return job

    async def update_job_progress(
        self,
        job_id: str,
        total_mixes: Optional[int] = None,
        mixes_scraped: Optional[int] = None,
        total_tracks: Optional[int] = None,
        tracks_searched: Optional[int] = None
    ) -> Optional[Job]:
        job = await self.get_job(job_id)
        if job:
            if total_mixes is not None:
                job.total_mixes = total_mixes
            if mixes_scraped is not None:
                job.mixes_scraped = mixes_scraped
            if total_tracks is not None:
                job.total_tracks = total_tracks
            if tracks_searched is not None:
                job.tracks_searched = tracks_searched
            await self.session.commit()
            await self.session.refresh(job)
        return job

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> List[Job]:
        result = await self.session.execute(
            select(Job)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def create_track(
        self,
        job_id: str,
        timestamp: str,
        artist: str,
        title: str,
        remix_info: Optional[str] = None
    ) -> Track:
        track = Track(
            job_id=job_id,
            timestamp=timestamp,
            artist=artist,
            title=title,
            remix_info=remix_info
        )
        self.session.add(track)
        await self.session.commit()
        await self.session.refresh(track)
        return track

    async def create_tracks_bulk(self, tracks: List[Track]):
        self.session.add_all(tracks)
        await self.session.commit()

    async def get_job_tracks(self, job_id: str) -> List[Track]:
        result = await self.session.execute(
            select(Track)
            .where(Track.job_id == job_id)
            .order_by(Track.timestamp)
        )
        return result.scalars().all()

    async def create_search_result(
        self,
        track_id: int,
        platform: str,
        found_artist: Optional[str],
        found_title: Optional[str],
        url: str,
        price: Optional[str] = None
    ) -> SearchResult:
        result = SearchResult(
            track_id=track_id,
            platform=platform,
            found_artist=found_artist,
            found_title=found_title,
            url=url,
            price=price
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def create_search_results_bulk(self, results: List[SearchResult]):
        self.session.add_all(results)
        await self.session.commit()

    async def get_job_results(
        self,
        job_id: str,
        platform: Optional[str] = None,
        artist: Optional[str] = None,
        title: Optional[str] = None
    ) -> List[Track]:
        query = (
            select(Track)
            .where(Track.job_id == job_id)
            .options(selectinload(Track.search_results))
            .order_by(Track.timestamp)
        )

        if artist:
            query = query.where(Track.artist.ilike(f"%{artist}%"))
        if title:
            query = query.where(Track.title.ilike(f"%{title}%"))

        result = await self.session.execute(query)
        tracks = result.scalars().all()

        if platform:
            for track in tracks:
                track.search_results = [
                    r for r in track.search_results
                    if r.platform.lower() == platform.lower()
                ]

        return tracks
