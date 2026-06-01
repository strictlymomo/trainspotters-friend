# Trainspotter's Friend API

FastAPI-based REST API for scraping DJ mix tracklists from MixesDB and searching digital music stores.

## Features

- **Async Architecture**: Non-blocking I/O for scraping and searching
- **Background Tasks**: Long-running jobs don't block HTTP requests
- **WebSocket Support**: Real-time progress updates during scraping
- **SQLite Database**: Stores all jobs, tracks, and search results
- **Auto-generated Docs**: OpenAPI/Swagger docs at `/docs`

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. The database will be created automatically on first run

## Running the Server

### Option 1: Direct uvicorn
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Using the script
```bash
./run_server.sh
```

### Option 3: Using yarn
```bash
yarn server
```

The API will be available at: http://localhost:8000

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Jobs

#### POST /api/jobs/scrape
Create a new scraping job for an artist.

**Request:**
```json
{
  "artist_name": "Haruka"
}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "artist_name": "Haruka",
  "status": "pending",
  "created_at": "2025-11-20T13:00:00"
}
```

#### GET /api/jobs/{job_id}
Get job status and progress.

**Response:**
```json
{
  "job_id": "uuid",
  "artist_name": "Haruka",
  "status": "searching",
  "created_at": "2025-11-20T13:00:00",
  "completed_at": null,
  "progress": {
    "mixes_scraped": 5,
    "total_mixes": 5,
    "tracks_searched": 45,
    "total_tracks": 120
  },
  "error_message": null
}
```

**Status values:**
- `pending`: Job created, not started yet
- `scraping`: Scraping mixes from MixesDB
- `searching`: Searching digital music stores
- `completed`: Job finished successfully
- `failed`: Job failed with error

#### GET /api/jobs
List all jobs with pagination.

**Query params:**
- `limit`: Max results (default: 50, max: 100)
- `offset`: Offset for pagination (default: 0)

### Tracks

#### GET /api/jobs/{job_id}/tracks
Get all parsed tracks from a job.

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "00:10:00",
    "artist": "Regis",
    "title": "A Hollow Moment",
    "remix_info": "[Downwards]"
  }
]
```

### Results

#### GET /api/jobs/{job_id}/results
Get search results with optional filters.

**Query params:**
- `platform`: Filter by platform (Bandcamp, Beatport, etc.)
- `artist`: Filter by artist name (partial match)
- `title`: Filter by track title (partial match)

**Response:**
```json
[
  {
    "timestamp": "00:10:00",
    "original_artist": "Regis",
    "original_title": "A Hollow Moment",
    "remix_info": "[Downwards]",
    "results": [
      {
        "id": 1,
        "track_id": 1,
        "platform": "Bandcamp",
        "found_artist": "Regis",
        "found_title": "A Hollow Moment (Dub Version)",
        "url": "https://semanticarecords.bandcamp.com/...",
        "price": ""
      }
    ]
  }
]
```

#### GET /api/jobs/{job_id}/export
Export results as CSV or JSON.

**Query params:**
- `format`: `csv` or `json` (default: csv)

Downloads a file with all results.

### WebSocket

#### WS /ws/jobs/{job_id}
Real-time progress updates.

**Message types:**
- `mixes_found`: Number of mixes discovered
- `mix_scraped`: A mix was scraped
- `parsing_complete`: All tracks parsed
- `track_searched`: A track was searched
- `job_complete`: Job finished successfully
- `job_failed`: Job failed with error

**Example message:**
```json
{
  "type": "track_searched",
  "data": {
    "track_number": 45,
    "total_tracks": 120,
    "results_found": 3
  }
}
```

## Architecture

```
Client Request
    ↓
FastAPI Endpoint
    ↓
Background Task (non-blocking)
    ↓
┌─────────────────────────┐
│ 1. Scrape MixesDB       │ → WebSocket updates
│ 2. Parse Tracklists     │ → WebSocket updates
│ 3. Search Music Stores  │ → WebSocket updates
│ 4. Save to SQLite       │ → WebSocket updates
└─────────────────────────┘
    ↓
Job Complete
```

## Database Schema

### jobs
- `id`: UUID primary key
- `artist_name`: Artist being scraped
- `status`: Job status
- `created_at`, `completed_at`: Timestamps
- `total_mixes`, `mixes_scraped`: Progress tracking
- `total_tracks`, `tracks_searched`: Progress tracking
- `error_message`: Error details if failed

### tracks
- `id`: Auto-increment primary key
- `job_id`: Foreign key to jobs
- `timestamp`, `artist`, `title`, `remix_info`: Track data

### search_results
- `id`: Auto-increment primary key
- `track_id`: Foreign key to tracks
- `platform`, `found_artist`, `found_title`, `url`, `price`: Search result data

## Rate Limiting

- **MixesDB scraping**: 2 second delay between requests
- **Music store searching**: 1 second delay per track (across all platforms)

This ensures respectful usage of external services.

## Error Handling

- Jobs that fail are marked with `status="failed"`
- `error_message` field contains the error details
- WebSocket sends `job_failed` message with error info

## Development

The API uses:
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM with async support
- **aiosqlite**: Async SQLite driver
- **httpx**: Async HTTP client
- **BeautifulSoup4**: HTML parsing
- **Pydantic**: Request/response validation
