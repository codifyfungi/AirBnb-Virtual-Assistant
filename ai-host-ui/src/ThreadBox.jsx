export default function ThreadBox({ Name, image, selected, onClick, guestType, checkIn, checkOut }) {
    return (
        <div
          onClick={onClick}
          style={{
            padding: "12px",
            marginBottom: "8px",
            display: "flex",
            alignItems: "center",
            background: selected ? "#e5f0ff" : "#fff",
            border: selected ? "1px solid #3b82f6" : "1px solid #ddd",
            borderRadius: "6px",
            cursor: "pointer",
            userSelect: "none",
          }}
          aria-pressed={selected}
          role="button"
          tabIndex={0}
        >
          {image && (
            <img
              src={image}
              alt="avatar"
              style={{ width: 32, height: 32, borderRadius: '50%', marginRight: 8 }}
            />
          )}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {/* Guest name always visible */}
            <div style={{ marginBottom: 6, fontWeight: '600', fontSize: '0.9rem', color: '#111' }}>
              {Name}
            </div>
            {/* Guest type and dates */}
            {(guestType || (checkIn && checkOut)) && (
              <div style={{ display: 'flex', gap: '4px' }}>
                {guestType && (
                  <div style={{ border: '1px solid #ddd', padding: '4px 6px', borderRadius: '4px', color: '#6b7280', fontSize: '0.75rem' }}>
                    {guestType}
                  </div>
                )}
                {checkIn && checkOut && (
                  <div style={{ border: '1px solid #ddd', padding: '4px 6px', borderRadius: '4px', color: '#6b7280', fontSize: '0.75rem' }}>
                    {checkIn} – {checkOut}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      );
  }