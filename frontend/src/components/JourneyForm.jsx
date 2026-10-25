import React from 'react';

const SUPPORTED_ORIGINS = [
  'Sitabuldi Interchange',
];

const SUPPORTED_DESTINATIONS = [
  { value: 'Dharampeth Extension', label: 'Dharampeth Extension (Aapli Bus / Auto)' },
  { value: 'Khapri / MIHAN', label: 'Khapri / MIHAN (Metro Orange Line)' },
  { value: 'Airport South & MIHAN', label: 'Airport South & MIHAN (Wardha Road Express)' },
  { value: 'Hingna Industrial Area', label: 'Hingna Industrial Area (Perimeter Transit)' },
];

const AVAILABLE_NEEDS = [
  { id: 'transport', label: '🚌 Public Transit' },
  { id: 'pharmacy', label: '💊 24/7 Pharmacy' },
  { id: 'hospital', label: '🏥 Emergency Care' },
  { id: 'well_lit', label: '💡 Lit Corridor' },
];

export default function JourneyForm({
  formData,
  onChange,
  onSubmit,
  loading,
  formError,
}) {
  const toggleNeed = (needId) => {
    const currentNeeds = formData.needs || [];
    if (currentNeeds.includes(needId)) {
      onChange({
        ...formData,
        needs: currentNeeds.filter((n) => n !== needId),
      });
    } else {
      onChange({
        ...formData,
        needs: [...currentNeeds, needId],
      });
    }
  };

  const handleScenarioChange = (scenario) => {
    let newOrigin = formData.origin;
    let newDest = formData.destination;
    let newDep = formData.departure_time;
    let newDead = formData.deadline;

    if (scenario === 'normal') {
      newOrigin = 'Sitabuldi Interchange';
      newDest = 'Dharampeth Extension';
      newDep = '02:15';
      newDead = '03:00';
    } else if (scenario === 'overnight_rollover') {
      newOrigin = 'Sitabuldi Interchange';
      newDest = 'Dharampeth Extension';
      newDep = '23:40';
      newDead = '00:30';
    } else if (scenario === 'impossible_deadline') {
      newOrigin = 'Sitabuldi Interchange';
      newDest = 'Dharampeth Extension';
      newDep = '02:15';
      newDead = '02:25';
    } else if (scenario === 'transport_unavailable') {
      newOrigin = 'Sitabuldi Interchange';
      newDest = 'Khapri / MIHAN';
      newDep = '02:15';
      newDead = '03:30';
    } else if (scenario === 'closure') {
      newOrigin = 'Sitabuldi Interchange';
      newDest = 'Airport South & MIHAN';
      newDep = '02:15';
      newDead = '03:30';
    }

    onChange({
      ...formData,
      origin: newOrigin,
      destination: newDest,
      departure_time: newDep,
      deadline: newDead,
      demo_scenario: scenario,
    });
  };

  return (
    <div className="form-card">
      <h2>
        <span>🧭</span> Journey Planner
      </h2>

      {formError && (
        <div style={{ color: '#fb7185', fontSize: '0.8rem', marginBottom: '0.75rem', fontWeight: 600 }}>
          ⚠️ {formError}
        </div>
      )}

      <form onSubmit={onSubmit}>
        <div className="form-group">
          <label htmlFor="origin">Origin (Nagpur Demonstration Network)</label>
          <select
            id="origin"
            className="form-select"
            value={formData.origin}
            onChange={(e) => onChange({ ...formData, origin: e.target.value })}
            required
          >
            {SUPPORTED_ORIGINS.map((orig) => (
              <option key={orig} value={orig}>
                {orig}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="destination">Destination (Supported Demonstration Corridors)</label>
          <select
            id="destination"
            className="form-select"
            value={formData.destination}
            onChange={(e) => onChange({ ...formData, destination: e.target.value })}
            required
          >
            {SUPPORTED_DESTINATIONS.map((dest) => (
              <option key={dest.value} value={dest.value}>
                {dest.label}
              </option>
            ))}
          </select>
        </div>

        <div className="time-row">
          <div className="form-group">
            <label htmlFor="departure_time">Departure (HH:MM)</label>
            <input
              id="departure_time"
              type="text"
              className="form-input"
              value={formData.departure_time}
              onChange={(e) => onChange({ ...formData, departure_time: e.target.value })}
              placeholder="02:15"
              pattern="^([01]\d|2[0-3]):([0-5]\d)$"
              title="24-hour time HH:MM (e.g. 02:15, 23:40)"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="deadline">Deadline (HH:MM)</label>
            <input
              id="deadline"
              type="text"
              className="form-input"
              value={formData.deadline}
              onChange={(e) => onChange({ ...formData, deadline: e.target.value })}
              placeholder="03:00"
              pattern="^([01]\d|2[0-3]):([0-5]\d)$"
              title="24-hour time HH:MM (e.g. 03:00, 00:30)"
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label>Nocturnal Needs</label>
          <div className="needs-grid">
            {AVAILABLE_NEEDS.map((need) => (
              <span
                key={need.id}
                className={`need-chip ${(formData.needs || []).includes(need.id) ? 'active' : ''}`}
                onClick={() => toggleNeed(need.id)}
              >
                {need.label}
              </span>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="demo_scenario">Evaluation Scenario</label>
          <select
            id="demo_scenario"
            className="form-select"
            value={formData.demo_scenario || 'normal'}
            onChange={(e) => handleScenarioChange(e.target.value)}
          >
            <option value="normal">Normal Journey (02:15 → 03:00, Sitabuldi → Dharampeth)</option>
            <option value="overnight_rollover">Midnight Rollover (23:40 → 00:30, +1 Day)</option>
            <option value="impossible_deadline">Impossible Deadline (Strict 10m window)</option>
            <option value="transport_unavailable">Transport Unavailable (Metro off-hours at boarding)</option>
            <option value="closure">Road Closure (Ajni Flyover Maintenance)</option>
          </select>
        </div>

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? 'Evaluating Deterministic Routes...' : 'Evaluate Nocturnal Journey'}
        </button>
      </form>
    </div>
  );
}
