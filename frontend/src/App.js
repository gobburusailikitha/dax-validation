import { useState } from "react";

function App() {
  const [dax, setDax] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const validateDax = async () => {
    if (!dax.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dax }),
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h2>DAX Validator</h2>
      <textarea
        rows="4"
        cols="50"
        value={dax}
        onChange={(e) => setDax(e.target.value)}
        placeholder="Enter DAX expression..."
      />
      <br />
      <button
        onClick={validateDax}
        disabled={loading || !dax.trim()}
        style={{ marginTop: "10px" }}
      >
        {loading ? "Validating..." : "Validate"}
      </button>

      {error && (
        <div style={{ marginTop: "20px", color: "red" }}>
          ⚠️ Error: {error}
        </div>
      )}

      {result && (
        <pre style={{ marginTop: "20px", background: "#f3f3f3", padding: "10px" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default App;