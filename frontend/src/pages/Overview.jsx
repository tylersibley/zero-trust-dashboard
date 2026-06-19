import { useEffect, useState } from 'react';
import { fetchSummary, fetchAtRiskUsers } from '../api/client';
import StatCard from '../components/StatCard';
import RiskGauge from '../components/RiskGauge';
import { AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const riskColor = (score) =>
  score >= 80 ? 'var(--risk-critical)' :
  score >= 60 ? 'var(--risk-high)' :
  score >= 30 ? 'var(--risk-medium)' : 'var(--risk-low)';

function PageState({ msg, err }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '60vh', fontFamily: 'var(--font-mono)', fontSize: 13,
      color: err ? 'var(--risk-high)' : 'var(--text-muted)',
    }}>{msg}</div>
  );
}

export default function Overview() {
  const [summary, setSummary] = useState(null);
  const [atRisk, setAtRisk] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([fetchSummary(), fetchAtRiskUsers()])
      .then(([s, u]) => {
        setSummary(s.data);
        setAtRisk(Array.isArray(u.data) ? u.data : (u.data.users ?? []));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageState msg="Fetching org telemetry…" />;
  if (error)   return <PageState msg={`API error: ${error}`} err />;

  // Org risk score: derive from risk_distribution
  const dist = summary?.risk_distribution ?? {};
  const totalRisk = (dist.low ?? 0) + (dist.medium ?? 0) + (dist.high ?? 0);
  const orgScore = totalRisk > 0
    ? Math.round(((dist.medium ?? 0) * 50 + (dist.high ?? 0) * 100) / totalRisk)
    : 0;

  const totalEvents = summary?.total_events_24h;
  const mfaRate = summary?.mfa_adoption_rate; // 0.0–1.0
  const mfaPct = mfaRate != null ? mfaRate * 100 : null;
  const highRisk = summary?.high_risk_events_24h;

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Overview</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Org-wide Zero Trust posture — live from Okta
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        <RiskGauge score={orgScore} />
        <StatCard
          label="Total Events (24h)"
          value={totalEvents != null ? totalEvents.toLocaleString() : '—'}
          sub="system log entries"
          accent="var(--accent-amber)"
          mono
        />
        <StatCard
          label="High Risk Events"
          value={highRisk != null ? highRisk : '—'}
          sub="last 24 hours"
          accent="var(--risk-high)"
          mono
        />
        <StatCard
          label="MFA Adoption"
          value={mfaPct != null ? `${Math.round(mfaPct)}%` : '—'}
          sub="of active users"
          accent={mfaPct != null && mfaPct < 80 ? 'var(--risk-high)' : 'var(--risk-low)'}
          mono
        />
      </div>

      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={14} color="var(--accent-amber)" />
          <span style={{ fontSize: 13, fontWeight: 600 }}>At-Risk Users</span>
          <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
            {atRisk.length} users
          </span>
        </div>

        {atRisk.length === 0 ? (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No high-risk users detected
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--bg-raised)' }}>
                {['User', 'Email', 'Risk Score', 'Anomalies', 'Last Seen', ''].map((h) => (
                  <th key={h} style={{
                    padding: '10px 20px', textAlign: 'left', fontSize: 11,
                    fontWeight: 600, letterSpacing: '0.06em', color: 'var(--text-muted)',
                    textTransform: 'uppercase', borderBottom: '1px solid var(--border)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {atRisk.map((user, i) => {
                const score  = user.risk_score ?? user.riskScore ?? 0;
                const userId = user.user_id ?? user.id ?? user.login;
                return (
                  <tr key={userId ?? i} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-raised)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: '14px 20px', fontWeight: 500 }}>
                      {user.display_name ?? user.displayName ?? user.login ?? userId}
                    </td>
                    <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>
                      {user.email ?? user.login ?? '—'}
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: riskColor(score) }}>
                        {Math.round(score)}
                      </span>
                    </td>
                    <td style={{ padding: '14px 20px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>
                      {user.anomaly_count ?? '—'}
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: 12, color: 'var(--text-secondary)' }}>
                      {user.last_seen ? new Date(user.last_seen).toLocaleString() : '—'}
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <button onClick={() => navigate(`/users/${encodeURIComponent(userId)}`)}
                        style={{
                          background: 'var(--bg-raised)', border: '1px solid var(--border)',
                          borderRadius: 5, color: 'var(--text-secondary)', fontSize: 11,
                          fontWeight: 500, padding: '5px 12px', cursor: 'pointer',
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
                        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}>
                        Investigate →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
