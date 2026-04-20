import React from 'react';
import { useVenueStore } from '../store/useStore';
import { Map } from '../components/Map';
import { ShieldAlert, Activity, Users } from 'lucide-react';

export const StaffDashboard: React.FC = () => {
  const { zones, staffAlerts } = useVenueStore();
  const criticalZones = Object.values(zones).filter((z) => (z.weight || 0) > 7.0);

  return (
    <div className="staff-dashboard app-container">
      <header role="banner" style={{ padding: '1rem', borderBottom: '1px solid var(--bg-secondary)', display: 'flex', justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--accent-primary)' }}>EventFlow: Command Center</h1>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} color="var(--status-clear)" />
            <span>System: Optimal</span>
          </div>
        </div>
      </header>

      <main>
        {/* Left: Spatial Intelligence */}
        <section aria-labelledby="map-heading">
          <h2 id="map-heading" className="sr-only">Live Venue Heatmap</h2>
          <Map />
        </section>

        {/* Right: Automated Triage & Alerts */}
        <aside aria-labelledby="alerts-heading">
          <h2 id="alerts-heading" style={{ fontSize: '1.1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert size={20} color="var(--status-critical)" />
            AI Dispersal Triage
          </h2>
          
          {/* Critical ARIA Live Region for Screen Readers */}
          <div 
            role="alert" 
            aria-live="assertive" 
            className={`aria-live-region ${criticalZones.length > 0 ? 'alert-assertive' : 'alert-polite'}`}
          >
            {criticalZones.length > 0 
              ? `CRITICAL: ${criticalZones.length} zones exceeding safety threshold. AI protocol generating...`
              : "All zones report nominal congestion."}
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {staffAlerts.map((alert, i) => (
              <div key={i} style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', borderLeft: `4px solid ${alert.severity === 'CRITICAL' ? 'var(--status-critical)' : 'var(--accent-primary)'}` }}>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{alert.severity} Broadcast</p>
                <p style={{ margin: '0.5rem 0' }}>{alert.broadcast_message}</p>
                {alert.protocol && (
                  <ul style={{ fontSize: '0.8rem', paddingLeft: '1.2rem' }}>
                    {alert.protocol.map((step, si) => (
                      <li key={si}>{step.action} at Node {step.zone_id}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>

          <div style={{ marginTop: '2rem' }}>
            <h3 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Users size={18} />
              Zone Capacity Stats
            </h3>
            <div style={{ fontSize: '0.85rem' }}>
              {Object.values(zones).map(z => (
                <div key={z.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--bg-secondary)' }}>
                  <span>Node {z.id}</span>
                  <span style={{ color: (z.weight || 0) > 5 ? 'var(--status-moderate)' : 'inherit' }}>
                    Weight: {z.weight?.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
};
