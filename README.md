# Trainspotter's Friend

DJ mix tracklist digger and digital music store finder

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
cd web && yarn && cd ..
yarn

# Start everything (API + Web UI)
yarn dev
```

Then visit: **http://localhost:5173**

## Features

- 🎵 Scrapes DJ mix tracklists from MixesDB
- 🔍 Searches 4 digital music stores (Bandcamp, Beatport, Traxsource, Hardwax)
- 📊 Real-time progress updates via WebSocket
- 💾 Persistent SQLite database
- 🎨 Modern React web interface
- 📥 CSV export functionality
- 🕒 Browse job history

## Available Commands

```bash
# Start API server + React frontend together
yarn dev

# Start API server only
yarn server

# Start React frontend only (in web/ directory)
cd web && yarn dev

# Legacy CLI commands (still work!)
python digger.py "Artist Name"
python music_store_search.py tracklist.txt
```

## Documentation

- **QUICKSTART.md** - Detailed setup guide
- **API_README.md** - API documentation
- **IMPLEMENTATION_SUMMARY.md** - Technical overview

## Requirements

- Python 3.8+
- Node.js 16+ (with yarn)

## How It Works

1. Enter an artist name in the web UI
2. API scrapes all mixes from MixesDB.com
3. Parses tracklists into structured data
4. Searches 4 music platforms for each track
5. Results stored in SQLite and displayed in filterable table
6. Export results as CSV

## Architecture

- **Backend**: FastAPI (async Python web framework)
- **Frontend**: React with real-time WebSocket updates
- **Database**: SQLite with SQLAlchemy ORM
- **Scraping**: httpx (async HTTP) + BeautifulSoup4

## Legacy Usage (CLI)

The original CLI tools still work:

### Search from tracklist file

1. Copy tracklist to `./tracklist.txt`
2. Run `python music_store_search.py`
3. See `/data` for results

### Scrape artist from MixesDB

```bash
python digger.py "Artist Name"
```
