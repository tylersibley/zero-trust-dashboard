import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchAtRiskUsers, fetchBaseline } from '../api/client';
import { ArrowLeft, Shield, ShieldOff, Clock, Globe, Wifi, AlertTriangle } from 'lucide-react';

const riskColor = (level) =>
  level === 'critical' ? 'var(--risk-critical)' :
  level === 'high'     ? 'var(--risk-high)' :
  level === 'medium'   ? 'var(--risk-medium)' : 'var(--risk-low)';

function InfoRow({ label, value, mono }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)', fontFamily: mono ? 'var(--font-mono)' : 'var(--font-ui)' }}>{value ?? '—'}</span>
    </div>
  );
}

function Badge({ children, color }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.06em',
      textTransform: 'uppercase',
      color,
      background: color + '22',
      border: `1px solid ${color}44`,
    }}>{children}</span>
  );
}

function SectionHeader({ title }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 12, marginTop: 24 }}>
      {title}
    </div>
  );
}

export default function UserDrilldown() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [baseline, setBaseline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // If no userId in URL, show user list picker
  const [selectedId, setSelectedId] = useState(userId ?? null);

  useEffect(() => {
    fetchAtRiskUsers()
      .then(u => {
        const list = Array.isArray(u.data) ? u.data : (u.data.value ?? u.data.users ?? []);
        setUsers(list);
        if (!selectedId && list.length > 0) setSelectedId(list[0].user_id);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setBaseline(null);
    fetchBaseline(selectedId)
      .then(r => setBaseline(r.data))
      .catch(() => setBaseline(null));
  }, [selectedId]);

  if (loading) return <PageState msg="Loading users…" />;
  if (error)   return <PageState msg={`API error: ${error}`} err />;

  const user = users.find(u => u.user_id === selectedId) ?? users[0];
  if (!user) return <PageState msg="No users found." />;

  const riskLevel = user.risk_level ?? 'low';
  const profile   = baseline?.behavioral_profile ?? {};

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <button onClick={() => navigate('/')} style={{
          background: 'none', border: '1px solid var(--border)', borderRadius: 6,
          color: 'var(--text-secondary)', padding: '6px 10px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6, fontSize: 12,
        }}>
          <ArrowLeft size={13} /> Back
        </button>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>User Drilldown</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>Behavioral baseline & risk profile</p>
        </div>
      </div>

      {/* User selector tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        {users.map(u => (
          <button key={u.user_id} onClick={() => setSelectedId(u.user_id)} style={{
            padding: '7px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border)',
            background: selectedId === u.user_id ? 'var(--accent-amber-dim)' : 'var(--bg-surface)',
            color: selectedId === u.user_id ? 'var(--accent-amber)' : 'var(--text-secondary)',
            transition: 'all 0.15s',
          }}>
            {u.first_name} {u.last_name}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Left: Identity */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{user.first_name} {user.last_name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{user.email}</div>
            </div>
            <Badge color={riskColor(riskLevel)}>{riskLevel}</Badge>
          </div>

          <SectionHeader title="Identity" />
          <InfoRow label="User ID"     value={user.user_id} mono />
          <InfoRow label="Status"      value={user.status} />
          <InfoRow label="Created"     value={user.created ? new Date(user.created).toLocaleDateString() : null} />
          <InfoRow label="Last Login"  value={user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'} />

          <SectionHeader title="Risk Signals" />
          <InfoRow label="Risk Score"       value={user.current_risk_score?.toFixed(1)} mono />
          <InfoRow label="Recent Events"    value={user.recent_event_count} mono />
          <InfoRow label="Failed Logins"    value={user.failed_login_count} mono />

          <SectionHeader title="MFA Status" />
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingTop: 8 }}>
            {user.mfa_enrolled
              ? <><Shield size={16} color="var(--risk-low)" /><span style={{ fontSize: 13, color: 'var(--risk-low)', fontWeight: 600 }}>Enrolled</span></>
              : <><ShieldOff size={16} color="var(--risk-high)" /><span style={{ fontSize: 13, color: 'var(--risk-high)', fontWeight: 600 }}>Not Enrolled</span></>
            }
          </div>
          {user.mfa_factors?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {user.mfa_factors.map((f, i) => (
                <Badge key={i} color="var(--risk-low)">{f}</Badge>
              ))}
            </div>
          )}
        </div>

        {/* Right: Behavioral baseline */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>Behavioral Baseline</span>
            {baseline && (
              <Badge color={baseline.model_trained ? 'var(--risk-low)' : 'var(--risk-medium)'}>
                {baseline.model_trained ? 'Model Trained' : 'Training'}
              </Badge>
            )}
          </div>

          {!baseline ? (
            <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12, paddingTop: 8 }}>
              Loading baseline…
            </div>
          ) : (
            <>
              <SectionHeader title="Login Patterns" />
              <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                <div style={{
                  flex: 1, background: 'var(--bg-raised)', borderRadius: 6, padding: '14px 16px',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <Clock size={12} color="var(--accent-amber)" />
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Typical Hour</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {profile.typical_login_hour ?? '—'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {profile.login_hour_window ?? ''}
                  </div>
                </div>
                <div style={{
                  flex: 1, background: 'var(--bg-raised)', borderRadius: 6, padding: '14px 16px',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <AlertTriangle size={12} color="var(--risk-high)" />
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Failure Rate</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: profile.historical_failure_rate && parseFloat(profile.historical_failure_rate) > 30 ? 'var(--risk-high)' : 'var(--text-primary)' }}>
                    {profile.historical_failure_rate ?? '—'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {profile.total_failures ?? 0} total failures
                  </div>
                </div>
              </div>

              <SectionHeader title="Network Fingerprint" />
              <div style={{ background: 'var(--bg-raised)', borderRadius: 6, padding: '14px 16px', border: '1px solid var(--border)', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                  <Wifi size={12} color="var(--accent-amber)" />
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Known IPs ({profile.known_ip_count ?? 0})
                  </span>
                </div>
                {(profile.known_ips ?? []).length === 0 ? (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>No IPs recorded</div>
                ) : (
                  profile.known_ips.map((ip, i) => (
                    <div key={i} style={{
                      fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)',
                      padding: '4px 0', borderBottom: i < profile.known_ips.length - 1 ? '1px solid var(--border)' : 'none',
                    }}>{ip}</div>
                  ))
                )}
              </div>

              {(profile.known_countries ?? []).length > 0 && (
                <div style={{ background: 'var(--bg-raised)', borderRadius: 6, padding: '14px 16px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <Globe size={12} color="var(--accent-amber)" />
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Known Countries</span>
                  </div>
                  {profile.known_countries.map((c, i) => (
                    <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', padding: '4px 0' }}>{c}</div>
                  ))}
                </div>
              )}

              <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--bg-raised)', borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {baseline.total_events_analyzed} events analyzed · {baseline.note}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function PageState({ msg, err }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '60vh', fontFamily: 'var(--font-mono)', fontSize: 13,
      color: err ? 'var(--risk-high)' : 'var(--text-muted)',
    }}>{msg}</div>
  );
}
