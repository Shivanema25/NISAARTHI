import React from 'react';

export const DEMO_PRESETS = [
  {
    id: 'normal',
    title: '🌙 Normal Journey',
    desc: 'Sitabuldi → Dharampeth (02:15 → 03:00, 45m window, meets deadline)',
    params: {
      origin: 'Sitabuldi Interchange',
      destination: 'Dharampeth Extension',
      departure_time: '02:15',
      deadline: '03:00',
      needs: ['transport'],
      risk_preference: 'balanced',
      demo_scenario: 'normal',
    },
  },
  {
    id: 'overnight_rollover',
    title: '🕛 Midnight Rollover',
    desc: 'Sitabuldi → Dharampeth (23:40 → 00:30, 50m window across midnight, +1 day)',
    params: {
      origin: 'Sitabuldi Interchange',
      destination: 'Dharampeth Extension',
      departure_time: '23:40',
      deadline: '00:30',
      needs: ['transport'],
      risk_preference: 'balanced',
      demo_scenario: 'overnight_rollover',
    },
  },
  {
    id: 'impossible_deadline',
    title: '⏳ Impossible Deadline',
    desc: 'Sitabuldi → Dharampeth (02:15 → 02:25, 10m window, all routes infeasible)',
    params: {
      origin: 'Sitabuldi Interchange',
      destination: 'Dharampeth Extension',
      departure_time: '02:15',
      deadline: '02:25',
      needs: ['transport'],
      risk_preference: 'balanced',
      demo_scenario: 'impossible_deadline',
    },
  },
  {
    id: 'transport_unavailable',
    title: '🚫 Transport Offline',
    desc: 'Sitabuldi → Khapri (Metro offline at boarding time 02:24)',
    params: {
      origin: 'Sitabuldi Interchange',
      destination: 'Khapri / MIHAN',
      departure_time: '02:15',
      deadline: '03:30',
      needs: ['transport'],
      risk_preference: 'balanced',
      demo_scenario: 'transport_unavailable',
    },
  },
  {
    id: 'closure',
    title: '🚧 Road Closure',
    desc: 'Sitabuldi → Airport South (Ajni Flyover nocturnal maintenance active)',
    params: {
      origin: 'Sitabuldi Interchange',
      destination: 'Airport South & MIHAN',
      departure_time: '02:15',
      deadline: '03:30',
      needs: ['transport'],
      risk_preference: 'balanced',
      demo_scenario: 'closure',
    },
  },
];

export default function Presets({ activePreset, onSelectPreset }) {
  return (
    <section className="presets-section">
      <div className="presets-header">
        <span>Quick Demonstration Presets (Seeded Scenarios)</span>
        <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Click to populate & plan</span>
      </div>
      <div className="presets-grid">
        {DEMO_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={`preset-btn ${activePreset === preset.id ? 'active' : ''}`}
            onClick={() => onSelectPreset(preset)}
          >
            <span className="preset-title">{preset.title}</span>
            <span className="preset-desc">{preset.desc}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
