export default function ThreadBox({ Name, image, selected, onClick }) {
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
          <span>{Name}</span>
        </div>
      );
  }