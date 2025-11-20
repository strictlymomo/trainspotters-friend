import { useState, useEffect } from 'react'
import Papa from 'papaparse'
import './App.css'

function App() {
  const [artist, setArtist] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [tracklist, setTracklist] = useState([])
  const [filteredResults, setFilteredResults] = useState([])
  const [filters, setFilters] = useState({
    artist: '',
    title: '',
    remix: '',
    platform: ''
  })

  const handleArtistSearch = async (artistName) => {
    setArtist(artistName)

    // Find the latest data directory for this artist
    try {
      // For now, we'll need to manually specify the data path
      // In a real app, you'd query available directories
      const dataPath = '/data/20251120_122551'

      // Load CSV
      const csvResponse = await fetch(`${dataPath}/music_search_results.csv`)
      const csvText = await csvResponse.text()

      Papa.parse(csvText, {
        header: true,
        complete: (results) => {
          setSearchResults(results.data)
          setFilteredResults(results.data)
        }
      })

      // Load tracklist
      const tracklistResponse = await fetch(`${dataPath}/combined_tracklist.txt`)
      const tracklistText = await tracklistResponse.text()
      const tracks = tracklistText.split('\n').filter(line => line.trim())
      setTracklist(tracks)
    } catch (error) {
      console.error('Error loading data:', error)
      alert('Could not load data. Make sure the data files exist in the data directory.')
    }
  }

  // Auto-load data on mount
  useEffect(() => {
    handleArtistSearch('')
  }, [])

  useEffect(() => {
    if (searchResults.length === 0) return

    const filtered = searchResults.filter(row => {
      if (!row.original_artist) return false

      return (
        (filters.artist === '' || row.original_artist?.toLowerCase().includes(filters.artist.toLowerCase())) &&
        (filters.title === '' || row.original_title?.toLowerCase().includes(filters.title.toLowerCase())) &&
        (filters.remix === '' || row.remix_info?.toLowerCase().includes(filters.remix.toLowerCase())) &&
        (filters.platform === '' || row.platform?.toLowerCase().includes(filters.platform.toLowerCase()))
      )
    })

    setFilteredResults(filtered)
  }, [filters, searchResults])

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }))
  }

  const clearFilters = () => {
    setFilters({ artist: '', title: '', remix: '', platform: '' })
  }

  return (
    <div className="app">
      <header>
        <h1>Trainspotter's Friend</h1>
      </header>

      <div className="search-section">
        <input
          type="text"
          placeholder="Enter artist name..."
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleArtistSearch(artist)}
        />
        <button onClick={() => handleArtistSearch(artist)}>Search</button>
      </div>

      {tracklist.length > 0 && (
        <div className="tracklist-section">
          <h2>Tracklist</h2>
          <div className="tracklist">
            {tracklist.map((track, idx) => (
              <div key={idx} className="track-item">
                {track}
              </div>
            ))}
          </div>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="results-section">
          <h2>Search Results ({filteredResults.length} tracks)</h2>

          <div className="filters">
            <input
              type="text"
              placeholder="Filter by artist..."
              value={filters.artist}
              onChange={(e) => handleFilterChange('artist', e.target.value)}
            />
            <input
              type="text"
              placeholder="Filter by title..."
              value={filters.title}
              onChange={(e) => handleFilterChange('title', e.target.value)}
            />
            <input
              type="text"
              placeholder="Filter by remix..."
              value={filters.remix}
              onChange={(e) => handleFilterChange('remix', e.target.value)}
            />
            <input
              type="text"
              placeholder="Filter by platform..."
              value={filters.platform}
              onChange={(e) => handleFilterChange('platform', e.target.value)}
            />
            <button onClick={clearFilters}>Clear Filters</button>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Track Info</th>
                  <th>Platform</th>
                  <th>Found As</th>
                  <th>Price</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((row, idx) => {
                  if (!row.original_artist) return null

                  const trackInfo = [
                    row.original_artist,
                    row.original_title,
                    row.remix_info
                  ].filter(Boolean).join(' - ')

                  return (
                    <tr key={idx}>
                      <td className="timestamp">{row.timestamp}</td>
                      <td className="track-info">
                        {row.url && row.url !== '' ? (
                          <a href={row.url} target="_blank" rel="noopener noreferrer">
                            {trackInfo}
                          </a>
                        ) : (
                          <span className="no-result">{trackInfo}</span>
                        )}
                      </td>
                      <td className="platform">{row.platform}</td>
                      <td className="found-as">
                        {row.found_artist && (
                          <>
                            <div className="found-artist">{row.found_artist}</div>
                            <div className="found-title">{row.found_title}</div>
                          </>
                        )}
                      </td>
                      <td className="price">{row.price || '-'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
