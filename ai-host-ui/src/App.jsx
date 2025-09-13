import { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL

function App() {
  const [threadId, setThreadId] = useState(null)
  const [threadInfo, setThreadInfo] = useState(null)
  const [threadMessages, setThreadMessages] = useState([])
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // combined polling: get current thread, ingest new emails, refresh thread details
  useEffect(() => {
    const pollBackend = async () => {
      try {
        const resCT = await fetch(`${API_BASE_URL}/api/current-thread`)
        if (resCT.ok) {
          const { threadId: newId } = await resCT.json()
          setThreadId(newId)
          if (!newId) return
          await fetch(`${API_BASE_URL}/api/watch-inbox`, { method: 'POST' })
          const { thread, messages } = await (await fetch(`${API_BASE_URL}/api/thread`)).json()
          setThreadInfo(thread)
          setThreadMessages(messages)
          setResponse('')
        }
      } catch (err) {
        console.error('Polling error:', err)
        setError(err.message)
      } finally {
        // disable loading spinner only once after first poll
        setLoading(false)
      }
    }

    // show loading spinner on initial fetch
    setLoading(true)
    setError(null)
    pollBackend()
    const intervalId = setInterval(pollBackend, 500)
    return () => clearInterval(intervalId)
  }, [])

  const handleSend = async () => {
    if (!threadId) return
    setLoading(true)
    setError(null)
    const payload = { threadId: threadId.id, messages: [...threadMessages, { role: 'user', content: query }] }
    try {
      const res = await fetch(`${API_BASE_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error('Failed to send query')
      const data = await res.json()
      setResponse(data.response)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* fixed header */}
      <div style={{ padding: '20px', borderBottom: '1px solid #ddd', textAlign: 'center', flexShrink: 0 }}>
        {threadInfo && (
          <>  
            <img src={threadInfo.guest_image} alt='avatar' style={{ width: 80, height: 80, borderRadius: '50%' }} />
            <h2>{threadInfo.guest_name}</h2>
          </>
        )}
      </div>
      {/* main content: two panels side by side */}
      <div style={{ flex: 1, display: 'flex' }}>
        {/* Left panel: messages */}
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
          {loading && <p>Loading...</p>}
          {error && <p style={{ color: 'red' }}>{error}</p>}
          {threadInfo ? (
            <div style={{ textAlign: 'left' }}>
              {threadMessages.map((msg, idx) => (
                <div key={idx} style={{
                  backgroundColor: msg.role === 'guest' ? '#f5f5f5' : '#e6f7ff',
                  padding: '8px',
                  borderRadius: '8px',
                  marginBottom: '8px'
                }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                    {msg.role === 'guest' ? msg.name : 'You'}
                  </div>
                  <div>{msg.text}</div>
                </div>
              ))}
              {response && (
                <div style={{
                  backgroundColor: '#d9f7be',
                  padding: '8px',
                  borderRadius: '8px',
                  marginBottom: '8px'
                }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Assistant</div>
                  <div>{response}</div>
                </div>
              )}
            </div>
          ) : (
            !loading && <p style={{ textAlign: 'center', marginTop: '40px' }}>No conversation selected.</p>
          )}
        </div>
        {/* Right panel: query section */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderLeft: '1px solid #ddd' }}>
          {/* query results or context */}
          <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
            {/* Search results will appear here */}
          </div>
          {/* search bar at bottom */}
          <div style={{ padding: '20px', borderTop: '1px solid #ddd' }}>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder='Type your query'
              style={{ width: '80%', padding: '8px' }}
            />
            <button onClick={handleSend} style={{ marginLeft: '8px', padding: '8px 16px' }}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
