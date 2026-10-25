import React, { useState } from 'react';

export default function RouteCard({ route, index }) {
  const [showEvidence, setShowEvidence] = useState(false);

  const isOperationallyFeasible = route.operational_feasibility;

  return (
    <div
      className={`route-card ${
        isOperationallyFeasible
          ? 'feasible'
          : !route.deadline_feasible
          ? 'infeasible'
          : 'constrained'
      }`}
    >
      <div className="route-card-top">
        <div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>
            ALTERNATIVE #{index + 1} &bull; {route.origin} &rarr; {route.destination}
          </div>
          <h3 className="route-title">{route.route_name}</h3>
        </div>

        <div className="badges-row">
          {/* Overall Operational Feasibility Badge */}
          {isOperationallyFeasible ? (
            <span className="badge-tag feasible">✓ Operationally Feasible</span>
          ) : (
            <span className="badge-tag infeasible">✕ Operationally Infeasible</span>
          )}

          {/* Time-Only Deadline Feasibility Badge */}
          {route.deadline_feasible ? (
            <span className="badge-tag feasible">⏱️ Meets Deadline</span>
          ) : (
            <span className="badge-tag infeasible">⏱️ Exceeds Deadline</span>
          )}

          {/* Transport Boarding Availability Badge */}
          {!route.transport_available && (
            <span className="badge-tag warning">⚠️ Transport Offline at Boarding</span>
          )}

          {/* Closure Constraint Badge */}
          {route.closure_constraints.length > 0 && (
            <span className="badge-tag warning">🚧 Active Closure</span>
          )}

          {/* Confidence Badge (Scenario-Scoped) */}
          <span
            className="badge-tag"
            style={{
              backgroundColor: 'rgba(99, 102, 241, 0.2)',
              color: '#818cf8',
              border: '1px solid rgba(99, 102, 241, 0.3)',
            }}
          >
            {route.confidence_indicator}
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-row">
        <div className="metric-item">
          <span className="metric-label">Total Duration</span>
          <span className="metric-val">{route.total_duration} min</span>
          <span className="metric-sub">
            Walk {route.walking_time}m &bull; Wait {route.waiting_time}m &bull; Transit {route.transport_time}m
          </span>
        </div>

        <div className="metric-item">
          <span className="metric-label">Estimated Arrival</span>
          <span className="metric-val">{route.estimated_arrival}</span>
          <span className="metric-sub">
            {route.arrival_day_offset === 0 ? 'Same calendar day' : '+1 day (Overnight rollover)'}
          </span>
        </div>

        <div className="metric-item">
          <span className="metric-label">Feasibility Status</span>
          <span
            className="metric-val"
            style={{
              fontSize: '0.85rem',
              color: isOperationallyFeasible ? '#34d399' : '#fb7185',
            }}
          >
            {route.feasibility_status}
          </span>
          <span className="metric-sub">Hard Constraint Check</span>
        </div>

        <div className="metric-item">
          <span className="metric-label">Provenance</span>
          <span className="metric-val" style={{ fontSize: '0.9rem', color: '#38bdf8' }}>
            {route.data_origin}
          </span>
          <span className="metric-sub">Deterministic Model</span>
        </div>
      </div>

      {/* Journey Legs Timeline Schematic with Chronological Boarding Time */}
      {route.legs && route.legs.length > 0 && (
        <div className="timeline-section">
          <div className="timeline-title">Journey Leg Sequence & Boarding Schedule</div>
          <div className="legs-sequence">
            {route.legs.map((leg, legIdx) => (
              <div key={legIdx} className="leg-node">
                <span className="leg-mode-pill">{leg.mode.toUpperCase()}</span>
                <span className="leg-text">
                  {leg.instruction}
                  {leg.scheduled_boarding_time && (
                    <span
                      style={{
                        display: 'block',
                        fontSize: '0.75rem',
                        marginTop: '0.15rem',
                        color: leg.transport_available_at_boarding ? '#34d399' : '#fb7185',
                      }}
                    >
                      🕒 Scheduled Boarding: {leg.scheduled_boarding_time} &bull; Service Window: {leg.transit_operating_hours || 'N/A'}{' '}
                      ({leg.transport_available_at_boarding ? 'Active' : 'Offline at Boarding'})
                    </span>
                  )}
                </span>
                <span className="leg-duration">{leg.duration_minutes} min</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decision Reasons */}
      <div style={{ marginTop: '0.75rem' }}>
        <strong style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase' }}>
          Decision Rationale
        </strong>
        <ul className="reasons-list">
          {route.reasons.map((reason, rIdx) => (
            <li key={rIdx}>{reason}</li>
          ))}
        </ul>
      </div>

      {/* Nocturnal Warnings */}
      {route.warnings && route.warnings.length > 0 && (
        <div className="warning-callout">
          <strong>⚠️ Nocturnal Advisory:</strong>
          <ul style={{ paddingLeft: '1rem', marginTop: '0.25rem' }}>
            {route.warnings.map((w, wIdx) => (
              <li key={wIdx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence & Trust Engine Section */}
      {route.evidence && route.evidence.length > 0 && (
        <div className="evidence-section">
          <button
            type="button"
            className="evidence-toggle-btn"
            onClick={() => setShowEvidence(!showEvidence)}
          >
            <span>{showEvidence ? '▼ Hide' : '▶ Show'} Data Trust Engine Evidence ({route.evidence.length} facts)</span>
          </button>

          {showEvidence && (
            <table className="evidence-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Fact / Observation</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Freshness / Age</th>
                  <th>Provenance</th>
                  <th>Deterministic Reason</th>
                </tr>
              </thead>
              <tbody>
                {route.evidence.map((ev, evIdx) => (
                  <tr key={evIdx}>
                    <td style={{ fontWeight: 600 }}>{ev.subject}</td>
                    <td>{String(ev.value)}</td>
                    <td>
                      <span className={`trust-badge ${ev.status}`}>{ev.status}</span>
                    </td>
                    <td style={{ color: '#94a3b8' }}>{ev.source}</td>
                    <td style={{ fontSize: '0.72rem', color: '#38bdf8' }}>
                      {ev.freshness_limit || 'Threshold unavailable'}
                      {ev.observed_age_minutes !== null && ev.observed_age_minutes !== undefined
                        ? ` (Age: ${ev.observed_age_minutes}m)`
                        : ' (Seeded/Unmeasured)'}
                    </td>
                    <td>
                      <span className="provenance-tag">{ev.data_origin}</span>
                    </td>
                    <td style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>{ev.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
