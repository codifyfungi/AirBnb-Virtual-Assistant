import { useState, useEffect, useRef } from 'react'
import './App.css'
import ThreadBox from "./ThreadBox";

// API base URL - change this if your Flask server runs on a different port
const API_BASE_URL = import.meta.env.VITE_API_URL;
//const API_BASE_URL = "http://127.0.0.1:5000";

function App() {
  const [threads, setThreads] = useState({});
  const [messages, setMessages] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [generatedResponse, setGeneratedResponse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const lastMessageIdRef = useRef(0);

  // Fetch threads and messages from API
  useEffect(() => {
    const fetchData = async () => {
      try {
        const watchResp = await fetch(`${API_BASE_URL}/api/watch-inbox`, {
          method: "POST",               // match your Flask route
          // no headers/body → avoids CORS preflight during dev
        });
        if (!watchResp.ok) {
          throw new Error('Failed to watch inbox');
        }
        const response = await fetch(
          `${API_BASE_URL}/api/threads?last_message_id=${lastMessageIdRef.current}`
        );
        if (!response.ok) {
          throw new Error('Failed to fetch data');
        }
        const data = await response.json();
        if (lastMessageIdRef.current === 0) {
          setThreads(data.threads);
          setMessages(data.messages);
          const firstId = Object.keys(data.threads)[0];
          if (firstId) {
            setSelectedId(firstId);
          }
          setLoading(false);
        } else {
          setThreads((prev) => ({ ...prev, ...data.threads }));
          setMessages((prev) => {
            const updated = { ...prev };
            for (const [threadId, msgs] of Object.entries(data.messages)) {
              const combined = [...(updated[threadId] || []), ...msgs];
              // trim to last 100 messages
              updated[threadId] = combined.length > 100 ? combined.slice(-100) : combined;
            }
            return updated;
          });
        }
        lastMessageIdRef.current = data.last_message_id;
        console.log(data.last_message_id)
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const currentMessages = selectedId ? (messages[selectedId] ?? []) : [];

  const handleGenerateResponse = async () => {
    if (selectedId) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            threadId: selectedId,
            messages: currentMessages  
          })
        });

        if (!response.ok) {
          throw new Error('Failed to generate response');
        }

        const data = await response.json();
        console.log('AI Response:', data.response);
        
        // Set the generated response in state
        setGeneratedResponse({
          text: data.response,
          time: 'Just now',
          name: 'Tina'
        });
      } catch (err) {
        console.error('Error generating response:', err);
        alert('Failed to generate response. Please try again.');
      }
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
        <div>Loading threads...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "red" }}>Error: {error}</div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh" , width: "100%"}}>
      {/* Sidebar on the left */}
      <div style={{
        width: "200px",
        borderRight: "1px solid #ccc",
        padding: "8px",
        background: "#f9f9f9",
        overflowY: "auto"
      }}>
        {Object.entries(threads).map(([id, name]) => (
          <ThreadBox key={id} Name={name} selected={selectedId === id} onClick={() => setSelectedId(id)} />
        ))}
      </div>

      {/* Main content area */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", background: "#fff" }}>
        {/* Messages Section */}
        <div style={{ flex: 1, padding: "16px", overflowY: "auto" }}>
          <h3 style={{ margin: "0 0 16px 0", color: "#374151", fontSize: "18px" }}>Conversation History</h3>
          {currentMessages.map((m, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                marginBottom: "12px",
              }}
            >
              <div
                style={{
                  padding: "10px 12px",
                  borderRadius: "12px",
                  background: m.role === "host" ? "#dbeafe" : "#f3f4f6",
                  maxWidth: "70%",
                }}
              >
                <div style={{ 
                  fontSize: "0.75rem", 
                  color: "#6b7280", 
                  marginBottom: "4px",
                  fontWeight: "500"
                }}>
                  {m.name}
                </div>
                {m.text}
                <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "4px" }}>
                  {m.time}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {/* Generated Response Section */}
        {generatedResponse && (
          <div style={{
            borderTop: "2px solid #e5e7eb",
            padding: "20px",
            background: "#f0f9ff"
          }}>
            <h3 style={{ margin: "0 0 16px 0", color: "#374151", fontSize: "18px" }}>Generated Response</h3>
            <div style={{
              padding: "16px",
              borderRadius: "12px",
              background: "#dbeafe",
              border: "1px solid #93c5fd"
            }}>
              <div style={{ 
                fontSize: "0.75rem", 
                color: "#6b7280", 
                marginBottom: "8px",
                fontWeight: "500"
              }}>
                {generatedResponse.name}
              </div>
              <div style={{ fontSize: "14px", lineHeight: "1.5" }}>
                {generatedResponse.text}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "8px" }}>
                {generatedResponse.time}
              </div>
            </div>
          </div>
        )}
        
        {/* Generate Response Section */}
        <div style={{
          borderTop: "2px solid #e5e7eb",
          padding: "20px",
          background: "#f9fafb"
        }}>
          <h3 style={{ margin: "0 0 16px 0", color: "#374151", fontSize: "18px" }}>AI Response Generator</h3>
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
            <button
              onClick={handleGenerateResponse}
              disabled={!selectedId}
              style={{
                padding: "12px 24px",
                backgroundColor: selectedId ? "#3b82f6" : "#9ca3af",
                color: "white",
                border: "none",
                borderRadius: "8px",
                cursor: selectedId ? "pointer" : "not-allowed",
                fontSize: "14px",
                fontWeight: "500",
                minWidth: "150px"
              }}
            >
              Generate Response
            </button>
            {selectedId && (
              <div style={{ 
                fontSize: "14px", 
                color: "#6b7280",
                fontStyle: "italic"
              }}>
                Click to generate an AI response for the selected conversation
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
