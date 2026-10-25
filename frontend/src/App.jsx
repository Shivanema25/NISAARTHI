import { useState, useEffect } from 'react';

function App() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/health');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setHealthData(data);
    } catch (err) {
      setError(err.message || 'Failed to connect to backend');
      setHealthData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="card">
      <header className="header">
        <h1>Nisaarthi</h1>
        <p className="subtitle">
          Problem Statement 1.1: The City That Sleeps While You Work &mdash; Phase 0 Scaffold
        </p>
      </header>

      <section>
        {loading && (
          <div className="badge badge-loading">
            <span className="dot"></span>
            Connecting to backend at /api/health...
          </div>
        )}

        {!loading && error && (
          <>
            <div className="badge badge-error">
              <span className="dot"></span>
              Backend Unavailable
            </div>
            <div className="error-box">
              <strong>Connection Error:</strong> {error}
              <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                Ensure the FastAPI backend server is running on <code>http://127.0.0.1:8000</code>.
              </p>
            </div>
          </>
        )}

        {!loading && !error && healthData && (
          <>
            <div className="badge badge-healthy">
              <span className="dot"></span>
              Backend Healthy
            </div>
            <pre className="response-box">
              {JSON.stringify(healthData, null, 2)}
            </pre>
          </>
        )}

        <div className="actions">
          <button onClick={fetchHealth} disabled={loading}>
            {loading ? 'Checking...' : 'Re-check Health Endpoint'}
          </button>
        </div>

        <div className="endpoint-info">
          Target endpoint: <code>GET /api/health</code> via Vite Proxy &rarr; <code>http://127.0.0.1:8000/api/health</code>
        </div>
      </section>
    </div>
  );
}

export default App;
