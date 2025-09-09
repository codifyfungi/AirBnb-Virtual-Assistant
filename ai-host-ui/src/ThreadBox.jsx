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
            <span>{Name}</span>
            {guestType && <small style={{ color: '#6b7280' }}>{guestType}</small>}
            {checkIn && checkOut && (
              <small style={{ color: '#6b7280' }}>
                {checkIn} – {checkOut}
              </small>
            )}
          </div>
        </div>
      );
  }