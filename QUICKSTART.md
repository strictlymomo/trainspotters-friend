# Trainspotter's Friend - Quick Start Guide

Complete setup guide for the API server and web interface.

## Prerequisites

- Python 3.8+
- Node.js 16+ (with yarn)
- pip (Python package manager)

## 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- SQLAlchemy (database ORM)
- httpx (async HTTP client)
- BeautifulSoup4 (HTML parsing)
- And other dependencies...

## 2. Install Frontend Dependencies

```bash
cd web
yarn
cd ..
```

## 3. Install Root Dependencies

```bash
# Install concurrently for running multiple services
yarn
```

## 4. Start the Application

### Option A: Run Both Server and Frontend Together (Recommended)

```bash
# From the project root
yarn dev
```

This runs both:
- API server at http://localhost:8000
- React app at http://localhost:5173

### Option B: Run Separately

**Terminal 1 - API Server:**
```bash
./run_server.sh
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - React App:**
```bash
cd web
yarn dev
```

## 5. Using the Application

1. Open http://localhost:5173 in your browser
2. Enter an artist name (e.g., "Haruka")
3. Click "Start Scraping"
4. Watch the real-time progress bar
5. Browse results in the filterable table
6. Click "Download CSV" to export

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **API README**: See `API_README.md`

## How It Works

```
1. User enters artist name
   ↓
2. API creates background job
   ↓
3. Scrapes MixesDB.com for all artist's mixes
   (WebSocket sends progress updates)
   ↓
4. Parses tracklists into structured data
   (Saved to SQLite database)
   ↓
5. Searches 4 music platforms for each track
   (Bandcamp, Beatport, Traxsource, Hardwax)
   (WebSocket sends progress updates)
   ↓
6. Results displayed in React table
   ↓
7. Export as CSV or browse in UI
```

## Features

- **Real-time Progress**: WebSocket updates show scraping progress
- **Background Processing**: No request timeouts - jobs run in background
- **Persistent Storage**: SQLite stores all jobs and results
- **Job History**: Browse and reload past scraping jobs
- **Advanced Filtering**: Filter results by artist, title, or platform
- **CSV Export**: Download results for offline use
- **Responsive UI**: Clean, modern interface

## Troubleshooting

### Port Already in Use

If port 8000 or 5173 is already in use:

**Change API port:**
```bash
uvicorn app.main:app --reload --port 8001
```

Then update `web/src/App.jsx` line 4:
```javascript
const API_URL = 'http://localhost:8001'
```

**Change React port:**
```bash
cd web
PORT=3000 yarn dev
```

### Database Issues

Delete the SQLite database to start fresh:
```bash
rm trainspotters.db
```

The database will be recreated on next server start.

### WebSocket Connection Failed

Make sure:
1. API server is running on port 8000
2. No firewall blocking WebSocket connections
3. Browser console shows no CORS errors

## File Structure

```
trainspotters-friend/
├── app/                      # FastAPI application
│   ├── main.py              # Entry point with routes
│   ├── models/              # Database & Pydantic models
│   ├── services/            # Business logic (scraper, searcher)
│   ├── db/                  # Database queries
│   └── websocket/           # WebSocket manager
├── web/                      # React frontend
│   ├── src/
│   │   ├── App.jsx          # Main component
│   │   └── App.css          # Styles
│   └── package.json
├── requirements.txt          # Python dependencies
├── run_server.sh            # Server startup script
├── API_README.md            # Detailed API documentation
└── QUICKSTART.md            # This file
```

## Development Tips

### Test API Endpoints

Use the Swagger UI at http://localhost:8000/docs to test endpoints directly.

### View Database

```bash
sqlite3 trainspotters.db
.tables
SELECT * FROM jobs;
.quit
```

### Monitor Logs

API logs appear in the terminal running the server. Watch for:
- Scraping progress
- Search results
- Errors

### Hot Reload

Both the API server (`--reload`) and React app support hot reload - changes are reflected immediately.

## Next Steps

- Read `API_README.md` for detailed API documentation
- Check out the original `digger.py` for standalone scraping
- Explore the database schema in `app/models/database.py`
- Customize the UI in `web/src/App.jsx` and `web/src/App.css`

## Support

For issues or questions:
1. Check the logs in the terminal
2. Visit Swagger docs at `/docs`
3. Review the API_README.md file
