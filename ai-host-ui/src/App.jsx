import { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL
//const API_BASE_URL = 'http://localhost:5000'// default to localhost if env var is not set
function App() {
  const [threadId, setThreadId] = useState(null)
  const [threadInfo, setThreadInfo] = useState(null)
  const [threadMessages, setThreadMessages] = useState([])
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [questions, setQuestions] = useState([])
  const [currentQIndex, setCurrentQIndex] = useState(0)
  const [hostAnswers, setHostAnswers] = useState([])

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
    //const payload = { threadId: threadId.id, messages: [...threadMessages, { role: 'user', content: query }] }
    try {
      // GET request to query endpoint without payload
      const res = await fetch(`${API_BASE_URL}/api/getquestions`)
      if (!res.ok) throw new Error('Failed to send query')
      const data = await res.json()
      setResponse(data.response)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGetQuestions = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/getquestions`)
      if (!res.ok) throw new Error('Failed to fetch questions')
      const data = await res.json()
      setQuestions(data.questions || [])
      setCurrentQIndex(0)
      setHostAnswers([])
      setQuery('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAnswerSubmit = () => {
    if (!query.trim()) return
    setHostAnswers(prev => [...prev, query.trim()])
    setQuery('')
    setCurrentQIndex(prev => prev + 1)
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
      <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>
        {/* Left panel: messages */}
        <div style={{ flex: 1, minHeight: 0, padding: '20px', overflowY: 'auto' }}>
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
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', borderLeft: '1px solid #ddd' }}>
          {/* current question and host answer */}
          <div style={{ flex: 1, minHeight: 0, padding: '20px', overflowY: 'auto' }}>
            {questions.length === 0 ? (
              <p style={{ color: '#888', textAlign: 'center' }}>No questions generated.</p>
            ) : currentQIndex < questions.length ? (
              <div style={{ marginBottom: '16px' }}>
                <p style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  {questions[currentQIndex]}
                </p>
                {hostAnswers[currentQIndex] && (
                  <div style={{ backgroundColor: '#e6f7ff', padding: '8px', borderRadius: '4px' }}>
                    {hostAnswers[currentQIndex]}
                  </div>
                )}
              </div>
            ) : (
              <p style={{ textAlign: 'center' }}>All questions answered.</p>
            )}
          </div>
          {/* search bar / Q&A at bottom */}
          <div style={{ padding: '20px', borderTop: '1px solid #ddd', textAlign: 'center' }}>
            {loading && <p>Loading...</p>}
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {questions.length === 0 ? (
              <button onClick={handleGetQuestions} style={{ padding: '8px 16px' }}>
                Generate Questions
              </button>
            ) : currentQIndex < questions.length ? (
              <>
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder='Your answer'
                  style={{ width: '80%', padding: '8px' }}
                />
                <button onClick={handleAnswerSubmit} style={{ marginLeft: '8px', padding: '8px 16px' }}>
                  Submit Answer
                </button>
              </>
            ) : (
              <p>All questions answered.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
