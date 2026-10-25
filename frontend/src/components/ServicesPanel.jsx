import React from 'react';

export default function ServicesPanel({ services, loading, error, onRetry }) {
  return (
    <section className="services-card">
      <div className="services-title">
        <span>🏥 Nagpur 24/7 Essential Nocturnal Services (Seeded Catalog)</span>
        {error && (
          <button
            type="button"
            onClick={onRetry}
            style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', background: '#e11d48' }}
          >
            Retry Services
          </button>
        )}
      </div>

      <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
        Published hospital casualty centers, round-the-clock pharmacies, and police assistance desks.
        Operating hours represent published directories (<strong>PROBABLE</strong>), not live occupancy or staffing.
      </p>

      {loading && (
        <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Loading seeded essential services...</div>
      )}

      {error && !loading && (
        <div style={{ color: '#fb7185', fontSize: '0.85rem' }}>
          Failed to load essential services from /api/services: {error}
        </div>
      )}

      {!loading && !error && services && services.length > 0 && (
        <div className="services-grid">
          {services.map((svc) => (
            <div key={svc.id} className="service-item">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="service-name">{svc.name}</span>
                <span className={`trust-badge ${svc.evidence_status}`}>{svc.evidence_status}</span>
              </div>
              <span className="service-meta">{svc.service_type}</span>
              <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>📍 {svc.address}</span>
              <span className="service-hours">🕒 Published Hours: {svc.published_hours}</span>
              <span className="service-limitation">
                <em>Provenance: {svc.data_origin} &bull; {svc.limitations}</em>
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
