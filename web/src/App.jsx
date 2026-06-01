import { useState, useEffect, useRef } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'
const RESULTS_PER_PAGE = 50

function App() {
  const [artist, setArtist] = useState('')
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [progress, setProgress] = useState(null)
  const [tracks, setTracks] = useState([])
  const [results, setResults] = useState([])
  const [filteredResults, setFilteredResults] = useState([])
  const [filters, setFilters] = useState({
    artist: '',
    title: '',
    platform: ''
  })
  const [recentJobs, setRecentJobs] = useState([])
  const [ws, setWs] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingJobs, setLoadingJobs] = useState(true)
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
  const [currentPage, setCurrentPage] = useState(1)
  const pollIntervalRef = useRef(null)
  const wsRef = useRef(null)

  // Load recent jobs on mount
  useEffect(() => {
    loadRecentJobs()
  }, [])

  // Cleanup WebSocket and polling on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  // Filter results whenever filters or results change
  useEffect(() => {
    if (results.length === 0) {
      setFilteredResults([])
      setCurrentPage(1)
      return
    }

    const filtered = results.filter(result => {
      const matchesArtist = filters.artist === '' ||
        result.original_artist?.toLowerCase().includes(filters.artist.toLowerCase())
      const matchesTitle = filters.title === '' ||
        result.original_title?.toLowerCase().includes(filters.title.toLowerCase())
      const matchesPlatform = filters.platform === '' ||
        result.results.some(r => r.platform.toLowerCase().includes(filters.platform.toLowerCase()))

      return matchesArtist && matchesTitle && matchesPlatform
    })

    setFilteredResults(filtered)
    setCurrentPage(1) // Reset to first page when filters change
  }, [filters, results])

  const loadRecentJobs = async () => {
    try {
      setLoadingJobs(true)
      const response = await fetch(`${API_URL}/api/jobs?limit=10`)
      if (!response.ok) {
        throw new Error('Failed to load recent jobs')
      }
      const data = await response.json()
      setRecentJobs(data)
    } catch (err) {
      console.error('Error loading recent jobs:', err)
      setError('Failed to load recent jobs. Make sure the API server is running.')
    } finally {
      setLoadingJobs(false)
    }
  }

  const handleStartScraping = async () => {
    if (!artist.trim()) {
      setError('Please enter an artist name')
      return
    }

    setError(null)
    setTracks([])
    setResults([])
    setFilteredResults([])
    setProgress(null)
    setLoading(true)
    setCurrentPage(1)

    // Close existing WebSocket if any
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Clear existing polling interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }

    try {
      // Create scraping job
      const response = await fetch(`${API_URL}/api/jobs/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artist_name: artist.trim() })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to create scraping job')
      }

      const data = await response.json()
      setJobId(data.job_id)
      setJobStatus(data.status)

      // Connect to WebSocket for progress updates
      const websocket = new WebSocket(`ws://localhost:8000/ws/jobs/${data.job_id}`)
      wsRef.current = websocket

      websocket.onopen = () => {
        console.log('WebSocket connected')
      }

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleWebSocketMessage(message)
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        setError('WebSocket connection error. Progress updates may be limited.')
      }

      websocket.onclose = () => {
        console.log('WebSocket connection closed')
        wsRef.current = null
      }

      setWs(websocket)

      // Poll for job status
      pollJobStatus(data.job_id)

    } catch (err) {
      console.error('Error starting scraping:', err)
      setError(err.message || 'Failed to start scraping job. Make sure the API server is running.')
      setLoading(false)
    }
  }

  const handleWebSocketMessage = (message) => {
    console.log('WebSocket message:', message)

    switch (message.type) {
      case 'mixes_found':
        setProgress(prev => ({
          ...prev,
          totalMixes: message.data.total_mixes
        }))
        break

      case 'mix_scraped':
        setProgress(prev => ({
          ...prev,
          mixesScraped: message.data.mix_number,
          totalMixes: message.data.total_mixes,
          currentMix: message.data.mix_title
        }))
        break

      case 'parsing_complete':
        setProgress(prev => ({
          ...prev,
          totalTracks: message.data.total_tracks
        }))
        break

      case 'track_searched':
        setProgress(prev => ({
          ...prev,
          tracksSearched: message.data.track_number,
          totalTracks: message.data.total_tracks
        }))
        break

      case 'job_complete':
        setJobStatus('completed')
        break

      case 'job_failed':
        setJobStatus('failed')
        setError(message.data.error)
        break
    }
  }

  const pollJobStatus = async (id) => {
    // Clear any existing interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/jobs/${id}`)
        if (!response.ok) {
          throw new Error('Failed to fetch job status')
        }
        const data = await response.json()

        setJobStatus(data.status)

        if (data.progress) {
          setProgress({
            mixesScraped: data.progress.mixes_scraped,
            totalMixes: data.progress.total_mixes,
            tracksSearched: data.progress.tracks_searched,
            totalTracks: data.progress.total_tracks
          })
        }

        if (data.status === 'completed') {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
          setLoading(false)
          await loadJobResults(id)
          loadRecentJobs()
          if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
          }
        } else if (data.status === 'failed') {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
          setLoading(false)
          setError(data.error_message || 'Job failed')
          if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err)
        // Don't set error here to avoid overwriting other errors
      }
    }, 2000)
  }

  const loadJobResults = async (id) => {
    try {
      setLoading(true)
      // Load tracks
      const tracksResponse = await fetch(`${API_URL}/api/jobs/${id}/tracks`)
      if (!tracksResponse.ok) {
        throw new Error('Failed to load tracks')
      }
      const tracksData = await tracksResponse.json()
      setTracks(tracksData)

      // Load results
      const resultsResponse = await fetch(`${API_URL}/api/jobs/${id}/results`)
      if (!resultsResponse.ok) {
        throw new Error('Failed to load results')
      }
      const resultsData = await resultsResponse.json()
      setResults(resultsData)
      setFilteredResults(resultsData)
    } catch (err) {
      console.error('Error loading job results:', err)
      setError(err.message || 'Failed to load results')
    } finally {
      setLoading(false)
    }
  }

  const loadExistingJob = async (job) => {
    setJobId(job.job_id)
    setJobStatus(job.status)
    setArtist(job.artist_name)
    setError(null)
    setCurrentPage(1)
    await loadJobResults(job.job_id)
  }

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }))
  }

  const clearFilters = () => {
    setFilters({ artist: '', title: '', platform: '' })
    setCurrentPage(1)
  }

  const handleSort = (key) => {
    let direction = 'asc'
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc'
    }
    setSortConfig({ key, direction })
  }

  const getSortedResults = () => {
    if (!sortConfig.key) {
      return filteredResults
    }

    const sorted = [...filteredResults].sort((a, b) => {
      let aVal, bVal

      switch (sortConfig.key) {
        case 'timestamp':
          aVal = a.timestamp || ''
          bVal = b.timestamp || ''
          break
        case 'artist':
          aVal = a.original_artist || ''
          bVal = b.original_artist || ''
          break
        case 'title':
          aVal = a.original_title || ''
          bVal = b.original_title || ''
          break
        case 'platform':
          aVal = a.results[0]?.platform || ''
          bVal = b.results[0]?.platform || ''
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })

    return sorted
  }

  const getPaginatedResults = () => {
    const sorted = getSortedResults()
    const startIndex = (currentPage - 1) * RESULTS_PER_PAGE
    const endIndex = startIndex + RESULTS_PER_PAGE
    return sorted.slice(startIndex, endIndex)
  }

  const totalPages = Math.ceil(filteredResults.length / RESULTS_PER_PAGE)

  const downloadCSV = async () => {
    if (!jobId) return

    try {
      const response = await fetch(`${API_URL}/api/jobs/${jobId}/export?format=csv`)
      if (!response.ok) {
        throw new Error('Failed to download CSV')
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${artist || 'results'}_results.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Error downloading CSV:', err)
      setError('Failed to download CSV file')
    }
  }

  const getProgressText = () => {
    if (!jobStatus) return ''

    if (jobStatus === 'pending') return 'Starting...'
    if (jobStatus === 'scraping') {
      return `Scraping mixes... (${progress?.mixesScraped || 0}/${progress?.totalMixes || '?'})`
    }
    if (jobStatus === 'searching') {
      return `Searching tracks... (${progress?.tracksSearched || 0}/${progress?.totalTracks || '?'})`
    }
    if (jobStatus === 'completed') return 'Complete!'
    if (jobStatus === 'failed') return 'Failed'

    return jobStatus
  }

  const getProgressPercentage = () => {
    if (!progress) return 0

    if (jobStatus === 'scraping' && progress.totalMixes > 0) {
      return (progress.mixesScraped / progress.totalMixes) * 100
    }
    if (jobStatus === 'searching' && progress.totalTracks > 0) {
      return (progress.tracksSearched / progress.totalTracks) * 100
    }
    return 0
  }

  return (
    <div className="app">
      <header>
        <h1>Trainspotter's Friend</h1>
        <p>DJ Mix Tracklist Digger</p>
      </header>

      <div className="search-section">
        <input
          type="text"
          placeholder="Enter artist name..."
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleStartScraping()}
          disabled={jobStatus && jobStatus !== 'completed' && jobStatus !== 'failed'}
        />
        <button
          onClick={handleStartScraping}
          disabled={jobStatus && jobStatus !== 'completed' && jobStatus !== 'failed'}
        >
          {jobStatus && jobStatus !== 'completed' && jobStatus !== 'failed' ? 'Scraping...' : 'Start Scraping'}
        </button>
      </div>

      {jobStatus && jobStatus !== 'completed' && jobStatus !== 'failed' && (
        <div className="progress-section">
          <div className="progress-text">{getProgressText()}</div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${getProgressPercentage()}%` }}
            />
          </div>
          {progress?.currentMix && (
            <div className="current-mix">Current: {progress.currentMix}</div>
          )}
        </div>
      )}

      {error && (
        <div className="error-section">
          <strong>Error:</strong> {error}
        </div>
      )}

      {loadingJobs && !jobId && (
        <div className="recent-jobs-section">
          <h2>Recent Jobs</h2>
          <div className="loading-message">Loading recent jobs...</div>
        </div>
      )}

      {!loadingJobs && recentJobs.length > 0 && !jobId && (
        <div className="recent-jobs-section">
          <h2>Recent Jobs</h2>
          <div className="jobs-list">
            {recentJobs.map(job => (
              <div
                key={job.job_id}
                className="job-item"
                onClick={() => loadExistingJob(job)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    loadExistingJob(job)
                  }
                }}
                aria-label={`Load job for ${job.artist_name}`}
              >
                <div className="job-artist">{job.artist_name}</div>
                <div className="job-info">
                  <span className={`job-status ${job.status}`}>{job.status}</span>
                  <span className="job-tracks">{job.total_tracks} tracks</span>
                  <span className="job-date">
                    {new Date(job.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loadingJobs && recentJobs.length === 0 && !jobId && (
        <div className="recent-jobs-section">
          <h2>Recent Jobs</h2>
          <div className="empty-state">No recent jobs found. Start a new scraping job above!</div>
        </div>
      )}

      {loading && jobId && tracks.length === 0 && (
        <div className="tracklist-section">
          <h2>Tracklist</h2>
          <div className="loading-message">Loading tracklist...</div>
        </div>
      )}

      {tracks.length > 0 && (
        <div className="tracklist-section">
          <h2>Tracklist ({tracks.length} tracks)</h2>
          <div className="tracklist">
            {tracks.slice(0, 20).map((track) => (
              <div key={track.id} className="track-item">
                {track.timestamp && `[${track.timestamp}] `}
                {track.artist} - {track.title}
                {track.remix_info && ` ${track.remix_info}`}
              </div>
            ))}
            {tracks.length > 20 && (
              <div className="track-item more">... and {tracks.length - 20} more</div>
            )}
          </div>
        </div>
      )}

      {loading && jobId && results.length === 0 && (
        <div className="results-section">
          <h2>Search Results</h2>
          <div className="loading-message">Loading search results...</div>
        </div>
      )}

      {results.length > 0 && (
        <div className="results-section">
          <div className="results-header">
            <h2>Search Results ({filteredResults.length} of {results.length} tracks)</h2>
            <button onClick={downloadCSV} className="download-btn" aria-label="Download results as CSV">
              Download CSV
            </button>
          </div>

          <div className="filters">
            <input
              type="text"
              placeholder="Filter by artist..."
              value={filters.artist}
              onChange={(e) => handleFilterChange('artist', e.target.value)}
              aria-label="Filter by artist name"
            />
            <input
              type="text"
              placeholder="Filter by title..."
              value={filters.title}
              onChange={(e) => handleFilterChange('title', e.target.value)}
              aria-label="Filter by track title"
            />
            <input
              type="text"
              placeholder="Filter by platform..."
              value={filters.platform}
              onChange={(e) => handleFilterChange('platform', e.target.value)}
              aria-label="Filter by platform"
            />
            <button onClick={clearFilters} aria-label="Clear all filters">Clear Filters</button>
          </div>

          {filteredResults.length === 0 && (
            <div className="empty-state">No results match your filters. Try adjusting your search criteria.</div>
          )}

          {filteredResults.length > 0 && (
            <>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>
                        <button
                          className="sort-button"
                          onClick={() => handleSort('timestamp')}
                          aria-label="Sort by timestamp"
                        >
                          Time
                          {sortConfig.key === 'timestamp' && (
                            <span className="sort-indicator">
                              {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                            </span>
                          )}
                        </button>
                      </th>
                      <th>
                        <button
                          className="sort-button"
                          onClick={() => handleSort('artist')}
                          aria-label="Sort by artist"
                        >
                          Track Info
                          {sortConfig.key === 'artist' && (
                            <span className="sort-indicator">
                              {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                            </span>
                          )}
                        </button>
                      </th>
                      <th>
                        <button
                          className="sort-button"
                          onClick={() => handleSort('platform')}
                          aria-label="Sort by platform"
                        >
                          Platform
                          {sortConfig.key === 'platform' && (
                            <span className="sort-indicator">
                              {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
                            </span>
                          )}
                        </button>
                      </th>
                      <th>Found As</th>
                      <th>Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getPaginatedResults().map((track, idx) => {
                      const trackInfo = [
                        track.original_artist,
                        track.original_title,
                        track.remix_info
                      ].filter(Boolean).join(' - ')

                      return track.results.map((result, resultIdx) => (
                        <tr key={`${idx}-${resultIdx}`}>
                          {resultIdx === 0 && (
                            <>
                              <td className="timestamp" rowSpan={track.results.length}>
                                {track.timestamp}
                              </td>
                              <td className="track-info" rowSpan={track.results.length}>
                                <span className="original-track">{trackInfo}</span>
                              </td>
                            </>
                          )}
                          <td className="platform">{result.platform}</td>
                          <td className="found-as">
                            <a href={result.url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${result.found_artist} - ${result.found_title} on ${result.platform}`}>
                              <div className="found-artist">{result.found_artist}</div>
                              <div className="found-title">{result.found_title}</div>
                            </a>
                          </td>
                          <td className="price">{result.price || '-'}</td>
                        </tr>
                      ))
                    })}
                  </tbody>
                </table>
              </div>

              {totalPages > 1 && (
                <div className="pagination">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    aria-label="Previous page"
                  >
                    Previous
                  </button>
                  <span className="page-info">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    aria-label="Next page"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default App
