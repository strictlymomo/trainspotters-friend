# Trainspotter's Friend Web Interface

A React web app for browsing and filtering DJ mix tracklists and their digital music store search results.

## Features

- **Artist Search**: Input an artist name to load their dig results
- **Tracklist Display**: View the original tracklist from the DJ mix
- **Interactive Table**: Browse all search results with multiple filters
- **Live Filtering**: Filter by artist, title, remix info, or platform
- **Clickable Links**: Track info links directly to the music store result pages
- **Price Display**: See pricing information when available

## Setup

1. Install dependencies:
```bash
yarn
```

2. Copy your data files to the public directory:
```bash
mkdir -p public/data
cp -r ../data/20251120_122551 public/data/
```

3. Start the development server:
```bash
yarn dev
```

4. Open your browser to the URL shown (typically http://localhost:5173)

## Usage

### Loading Data

The app currently loads data from `/data/20251120_122551/` directory. To use different data:

1. Copy your data directory to `public/data/[your-directory-name]`
2. Update the `dataPath` in `src/App.jsx` line 24 to point to your data directory

For example:
```bash
cp -r ../data/20251120_122551 public/data/
```

### Using the Interface

1. **Load Results**: The app will automatically try to load the data from the configured path
2. **View Tracklist**: Scroll through the original mix tracklist in the top section
3. **Filter Results**: Use the filter inputs to narrow down results by:
   - Artist name
   - Track title
   - Remix information
   - Platform (Bandcamp, etc.)
4. **Click Tracks**: Click any track link to open the music store page in a new tab
5. **Clear Filters**: Click "Clear Filters" to reset all filters

## Data Format

The app expects two files in the data directory:

### combined_tracklist.txt
Plain text file with the original DJ mix tracklist, one track per line.

### music_search_results.csv
CSV file with the following columns:
- `timestamp`: Time in mix when track plays
- `original_artist`: Artist from tracklist
- `original_title`: Track title from tracklist
- `remix_info`: Remix/version information
- `platform`: Music store platform (e.g., Bandcamp)
- `found_artist`: Artist name found in search results
- `found_title`: Track title found in search results
- `url`: Link to the music store page
- `price`: Price if available

## Development

Built with:
- React 18
- Vite
- PapaParse (CSV parsing)

To modify the app:
- Edit `src/App.jsx` for functionality
- Edit `src/App.css` for styling
