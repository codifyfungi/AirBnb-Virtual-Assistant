export default function ThreadBox({ Name, selected, onClick }) {
    return (
        <div
          onClick={onClick}
          style={{
            padding: "12px",
            marginBottom: "8px",
            background: selected ? "#e5f0ff" : "#fff",
            border: selected ? "1px solid #3b82f6" : "1px solid #ddd",
            borderRadius: "6px",
            textAlign: "center",
            cursor: "pointer",
            userSelect: "none",
          }}
          aria-pressed={selected}
          role="button"
          tabIndex={0}
        >
          {Name}
        </div>
      );
  }