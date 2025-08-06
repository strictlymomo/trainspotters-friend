from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import uvicorn
import os
from music_store_search import parse_tracklist, MusicStoreSearcher, save_results_to_csv, generate_stats, ensure_data_directory

app = FastAPI()

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    tracklist: str

class SearchResultRow(BaseModel):
    timestamp: str
    original_artist: str
    original_title: str
    remix_info: str
    platform: str
    found_artist: str
    found_title: str
    url: str
    price: str

@app.post("/search")
def search_tracks(request: SearchRequest):
    try:
        # Parse tracklist
        tracks = parse_tracklist(request.tracklist)
        if not tracks:
            raise HTTPException(status_code=400, detail="No valid tracks found in input.")
        searcher = MusicStoreSearcher()
        all_results = searcher.search_all(tracks)
        # Save to files as before
        run_dir = ensure_data_directory()
        save_results_to_csv(tracks, all_results, run_dir)
        generate_stats(tracks, all_results, run_dir / "stats.txt")
        # Prepare results as JSON
        results_json = []
        for i, track in enumerate(tracks):
            track_results = all_results.get(i, {})
            if not track_results:
                results_json.append({
                    "timestamp": track.timestamp,
                    "original_artist": track.artist,
                    "original_title": track.title,
                    "remix_info": track.remix_info,
                    "platform": "No results found",
                    "found_artist": "",
                    "found_title": "",
                    "url": "",
                    "price": ""
                })
            else:
                for platform, results in track_results.items():
                    for result in results:
                        results_json.append({
                            "timestamp": track.timestamp,
                            "original_artist": track.artist,
                            "original_title": track.title,
                            "remix_info": track.remix_info,
                            "platform": result.platform,
                            "found_artist": result.artist,
                            "found_title": result.title,
                            "url": result.url,
                            "price": result.price
                        })
        return {"results": results_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
