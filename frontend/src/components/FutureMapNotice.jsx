import React from 'react';

export default function FutureMapNotice() {
  return (
    <div className="future-map-box">
      <strong>🗺️ Interactive Geospatial Map (Scheduled for Phase 3)</strong>
      <p style={{ marginTop: '0.35rem', fontSize: '0.8rem' }}>
        Per the Nisaarthi development roadmap, Leaflet + OpenStreetMap integration with live corridor overlays
        will be introduced in <strong>Phase 3</strong>. Phase 1 focuses strictly on core deterministic routing logic,
        deadline arithmetic, and the Data Trust Engine.
      </p>
    </div>
  );
}
