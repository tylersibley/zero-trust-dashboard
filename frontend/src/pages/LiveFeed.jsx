import { useEffect, useState, useRef } from 'react';
import { fetchEvents } from '../api/client';
import { Activity, RefreshCw, Circle } from 'lucide-react';

const severityColor = (eventType) => {
  if (!eventType) return 'var(--text-muted)';
  const t = eventType.toLowerCase();
  if (t.includes('failure') || t.includes('denied') || t.includes('suspend') || t.includes('locked')) return 'var(--risk-high)';
  if (t.includes('warn') || t.includes('mfa') || t.includes('factor')) return 'var(--risk-medium)';
  if (t.includes('success') || t.includes('login') || t.includes('create')) return 'var(--risk-low)';
  return 'var(--text-muted)';
};

const severityLabel = (eventType) => {
  if (!eventType) return 'INFO';
  const t = eventType.toLowerCase();
  if (t.includes('failure') || t.includes('denied') || t.includes('suspend') || t.includes('locked')) return 'HIGH';
  if (t.includes('warn') || t.includes('mfa') || t.includes('factor')) return 'MED';
  return 'LOW';
};

function EventRow({ event }) {
  const color = severityColor(event.event_type ?? event.type);
  const label = severityLabel(event.event_type ?? event.type);
  const time = event.published ?? event.timestamp ?? event.created;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '60px 160px 1fr 180px',
      alignItems: 'center',
      gap: 16,
      padding: '12px 20px',
      borderBottom: '1px solid var(--border)',
      transition: 'background 0.1s',
    }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-raised)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      {/* Severity badge */}
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        letterSpacing: '0.06em', color,
        background: color + '22', border: `1px solid ${color}44`,
        borderRadius: 4, padding: '2px 6px', textAlign: 'center',
      }}>{label}</span>

      {/* Event type */}
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 11,
        color: 'var(--text-secondary)', whiteSpace: 'nowrap',
        overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {event.event_type ?? event.type ?? '—'}
      </span>

      {/* Actor / message */}
      <div style={{ overflow: 'hidden' }}>
        <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {event.actor ?? event.display_message ?? event.message ?? '—'}
        </div>
        {event.target && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {event.target}
          </div>
        )}
      </div>

      {/* Timestamp */}
      <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textAlign: 'right' }}>
        {time ? new Date(time).toLocaleString() : '—'}
      </span>
    </div>
  );
}

export default function LiveFeed() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const loadEvents = (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    fetchEvents(100)
      .then(r => {
        const raw = r.data;
        const list = Array.isArray(raw) ? raw : (raw.value ?? raw.events ?? []);
        setEvents(list);
        setLastUpdated(new Date());
        setError(null);
      })
      .catch(e => setError(e.message))
      .finally(() => { setLoading(false); setRefreshing(false); });
  };

  useEffect(() => {
    loadEvents();
    // Auto-refresh every 30 seconds
    intervalRef.current = setInterval(() => loadEvents(true), 30000);
    return () => clearInterval(intervalRef.current);
  }, []);

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>Live Feed</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
            Real-time Okta system log events · auto-refreshes every 30s
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {lastUpdated && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={() => loadEvents(true)}
            disabled={refreshing}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              borderRadius: 6, color: refreshing ? 'var(--text-muted)' : 'var(--text-secondary)',
              fontSize: 12, fontWeight: 500, padding: '7px 14px', cursor: refreshing ? 'not-allowed' : 'pointer',
            }}
          >
            <RefreshCw size={13} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 16px', marginBottom: 16,
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 6,
      }}>
        <Circle size={8} fill="var(--risk-low)" color="var(--risk-low)"
          style={{ animation: 'pulse 2s ease-in-out infinite' }} />
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Connected to Okta System Log
        </span>
        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
          {events.length} events loaded
        </span>
      </div>

      {/* Event table */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>

        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: '60px 160px 1fr 180px',
          gap: 16, padding: '10px 20px',
          background: 'var(--bg-raised)', borderBottom: '1px solid var(--border)',
        }}>
          {['Level', 'Event Type', 'Details', 'Time'].map(h => (
            <span key={h} style={{
              fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
              color: 'var(--text-muted)', textTransform: 'uppercase',
            }}>{h}</span>
          ))}
        </div>

        {loading ? (
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-muted)' }}>
            Fetching events…
          </div>
        ) : error ? (
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--risk-high)' }}>
            {error}
          </div>
        ) : events.length === 0 ? (
          <div style={{ padding: '64px 20px', textAlign: 'center' }}>
            <Activity size={32} color="var(--text-muted)" style={{ marginBottom: 16 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
              No events in the last 24 hours
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 400, margin: '0 auto', lineHeight: 1.6 }}>
              Events will appear here as users log in, trigger MFA challenges, or cause policy decisions in your Okta org.
              Try logging in or out of your Okta dev org to generate activity.
            </div>
          </div>
        ) : (
          events.map((event, i) => <EventRow key={event.uuid ?? event.id ?? i} event={event} />)
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
      `}</style>
    </div>
  );
}
