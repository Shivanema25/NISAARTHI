import React from 'react';

export default function Header({ healthStatus, systemStatus, onRetryHealth }) {
  const isHealthy = healthStatus && healthStatus.status === 'healthy';
  const isConnecting = !healthStatus && !systemStatus;

  return (
    <header>
      {/* Prominent Seeded Demonstration Disclaimer */}
      <div className="disclaimer-banner">
        <div>
          <span className="disclaimer-badge">DEMO MODE</span>
          <span style={{ marginLeft: '0.6rem', fontWeight: 600 }}>
            SEEDED DEMO DATA — NOT LIVE NAVIGATION
          </span>
          <span style={{ display: 'block', fontSize: '0.78rem', color: '#fde68a', marginTop: '0.15rem' }}>
            Nagpur demonstration dataset. Live OSRM routing, Open-Meteo weather, and live GTFS telemetry are reserved for future phases.
          </span>
        </div>
        <span style={{ fontSize: '0.75rem', opacity: 0.85 }}>Nagpur, Asia/Kolkata</span>
      </div>

      <div className="header-panel">
        <div className="brand-section">
          <h1>Nisaarthi</h1>
          <p className="tagline">Smarter decisions for the journey after dark.</p>
          <p className="subtext">
            Problem Statement 1.1: The City That Sleeps While You Work &mdash; Phase 1 Deterministic Engine
          </p>
        </div>

        <div className="system-status-badges">
          {/* Health Badge */}
          {isHealthy ? (
            <div className="status-badge connected" title="FastAPI backend connected at /api/health">
              <span className="dot"></span>
              Backend Healthy (v{healthStatus?.version || '0.1.0'})
            </div>
          ) : isConnecting ? (
            <div className="status-badge connecting">
              <span className="dot"></span>
              Connecting...
            </div>
          ) : (
            <div
              className="status-badge error"
              onClick={onRetryHealth}
              style={{ cursor: 'pointer' }}
              title="Click to retry backend connection"
            >
              <span className="dot"></span>
              Backend Unavailable (Retry)
            </div>
          )}

          {/* Engine Data Mode Badge */}
          <div className="status-badge mode">
            <span>City: Nagpur</span> &bull; <span>Mode: {systemStatus?.data_mode || 'SEEDED_DEMO'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
