import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Presets, { DEMO_PRESETS } from './components/Presets';
import JourneyForm from './components/JourneyForm';
import RouteCard from './components/RouteCard';
import ServicesPanel from './components/ServicesPanel';
import FutureMapNotice from './components/FutureMapNotice';

const DEFAULT_FORM_DATA = {
  origin: 'Sitabuldi Interchange',
  destination: 'Dharampeth Extension',
  departure_time: '02:15',
  deadline: '03:00',
  needs: ['transport'],
  risk_preference: 'balanced',
  demo_scenario: 'normal',
};

function App() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [services, setServices] = useState([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [servicesError, setServicesError] = useState(null);

  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [activePreset, setActivePreset] = useState('normal');

  const [planResult, setPlanResult] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState(null);
  const [formValidationError, setFormValidationError] = useState(null);

  // 1. Fetch Backend Health
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setHealthStatus(data);
    } catch (err) {
      setHealthStatus(null);
    }
  }, []);

  // 2. Fetch System Status
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSystemStatus(data);
    } catch (err) {
      setSystemStatus(null);
    }
  }, []);

  // 3. Fetch Seeded Services
  const fetchServices = useCallback(async () => {
    setServicesLoading(true);
    setServicesError(null);
    try {
      const res = await fetch('/api/services');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setServices(data.services || []);
    } catch (err) {
      setServicesError(err.message || 'Failed to fetch services');
    } finally {
      setServicesLoading(false);
    }
  }, []);

  // 4. Submit Journey Plan to Backend POST /api/plan
  const submitPlan = async (payload) => {
    setPlanLoading(true);
    setPlanError(null);
    setFormValidationError(null);

    // Strict front-end validation check
    const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
    if (!timeRegex.test(payload.departure_time) || !timeRegex.test(payload.deadline)) {
      setFormValidationError('Departure and deadline times must be valid 24-hour HH:MM format (e.g. 02:15, 23:40).');
      setPlanLoading(false);
      return;
    }

    try {
      const res = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorJson = await res.json().catch(() => null);
        const errorMsg = errorJson?.detail || `HTTP ${res.status} error`;
        throw new Error(errorMsg);
      }

      const data = await res.json();
      setPlanResult(data);
    } catch (err) {
      setPlanError(err.message || 'Failed to evaluate journey plan');
      setPlanResult(null);
    } finally {
      setPlanLoading(false);
    }
  };

  // Handle Preset selection
  const handleSelectPreset = (preset) => {
    setActivePreset(preset.id);
    setFormData(preset.params);
    submitPlan(preset.params);
  };

  // Handle Form Submission
  const handleFormSubmit = (e) => {
    e.preventDefault();
    submitPlan(formData);
  };

  // Initial load
  useEffect(() => {
    checkHealth();
    fetchStatus();
    fetchServices();
    // Prepopulate initial evaluation using real backend API
    submitPlan(DEFAULT_FORM_DATA);
  }, [checkHealth, fetchStatus, fetchServices]);

  return (
    <div className="app-container">
      {/* Header */}
      <Header
        healthStatus={healthStatus}
        systemStatus={systemStatus}
        onRetryHealth={() => {
          checkHealth();
          fetchStatus();
          fetchServices();
        }}
      />

      {/* Demonstration Presets Bar */}
      <Presets activePreset={activePreset} onSelectPreset={handleSelectPreset} />

      {/* Main Grid: Form on left, Results on right */}
      <div className="dashboard-grid">
        <aside>
          <JourneyForm
            formData={formData}
            onChange={(newData) => {
              setFormData(newData);
              setActivePreset(null);
            }}
            onSubmit={handleFormSubmit}
            loading={planLoading}
            formError={formValidationError}
          />
        </aside>

        <main className="results-column">
          {planLoading && (
            <div className="loading-box">
              <span className="dot" style={{ display: 'inline-block', marginRight: '0.5rem' }}></span>
              Running deterministic route evaluation against Nagpur demonstration graph...
            </div>
          )}

          {planError && !planLoading && (
            <div className="error-box">
              <h3>Planning Engine Error</h3>
              <p>{planError}</p>
              <button
                type="button"
                className="retry-btn"
                onClick={() => submitPlan(formData)}
              >
                Retry Plan Evaluation
              </button>
            </div>
          )}

          {!planLoading && !planError && planResult && (
            <>
              {/* Results Top Header */}
              <div className="results-header-bar">
                <span className="results-count">
                  {planResult.route_options.length} Candidate Route Alternatives Evaluated
                </span>
                <span className="window-metric">
                  Available Window: {planResult.available_time_minutes} min (
                  {planResult.deadline_day_offset === 0 ? 'Same Day' : '+1 Day Midnight Rollover'})
                </span>
              </div>

              {/* Route Alternative Cards */}
              {planResult.route_options.length === 0 && (
                <div className="empty-box">
                  <p style={{ fontWeight: 600, color: '#f59e0b', marginBottom: '0.5rem' }}>
                    No Matching Demonstration Routes
                  </p>
                  <p style={{ fontSize: '0.85rem' }}>{planResult.limitations_disclaimer}</p>
                </div>
              )}

              {planResult.route_options.map((route, idx) => (
                <RouteCard key={route.route_id || idx} route={route} index={idx} />
              ))}

            </>
          )}

          {!planLoading && !planError && !planResult && (
            <div className="empty-box">
              Select a scenario or fill out the form and submit to calculate deterministic nocturnal routes.
            </div>
          )}
        </main>
      </div>

      {/* Essential 24/7 Services Panel */}
      <ServicesPanel
        services={services}
        loading={servicesLoading}
        error={servicesError}
        onRetry={fetchServices}
      />

      {/* Future Phase 3 Notice */}
      <FutureMapNotice />
    </div>
  );
}

export default App;
