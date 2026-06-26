import { useState } from 'react';
import api from '../api/client';
import { fetchAtRiskUsers } from '../api/client';
import { useEffect } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, Play, RotateCcw } from 'lucide-react';

const ACTIONS = ['login', 'access_resource', 'admin_action', 'mfa_challenge', 'password_reset', 'api_access'];

const decisionStyle = (decision) => {
  if (!decision) return {};
  switch (decision.toUpperCase()) {
    case 'ALLOW':     return { color: 'var(--risk-low)',    icon: ShieldCheck, label: 'ALLOW' };
    case 'CHALLENGE': return { color: 'var(--risk-medium)', icon: ShieldAlert, label: 'CHALLENGE' };
    case 'DENY':      return { color: 'var(--risk-high)',   icon: ShieldX,     label: 'DENY' };
    default:          return { color: 'var(--text-muted)',  icon: ShieldCheck, label: decision };
  }
};

const riskBarColor = (score) =>
  score >= 80 ? 'var(--risk-critical)' :
  score >= 60 ? 'var(--risk-high)' :
  score >= 30 ? 'var(--risk-medium)' : 'var(--risk-low)';

export default function RiskSimulator() {
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState('');
  const [action, setAction] = useState('login');
  const [ipAddress, setIpAddress] = useState('');
  const [country, setCountry] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchAtRiskUsers().then(u => {
      const list = Array.isArray(u.data) ? u.data : (u.data.value ?? u.data.users ?? []);
      setUsers(list);
      if (list.length > 0) setUserId(list[0].user_id);
    });
  }, []);

  const handleSimulate = async () => {
    if (!userId) return;
    setLoading(true);
    setResult(null);
    try {
      // Match the exact PolicySimulationRequest schema
      const payload = { user_id: userId };
      if (ipAddress) payload.ip_address = ipAddress;
      if (country)   payload.location_country = country;
      payload.resource = action;

      const res = await api.post('/risk/simulate', payload);
      const data = res.data;
      setResult(data);

      const user = users.find(u => u.user_id === userId);
      setHistory(prev => [{
        user: user ? `${user.first_name} ${user.last_name}` : userId,
        action,
        decision: data.decision,
        risk_score: data.risk_score,
        ts: new Date(),
      }, ...prev].slice(0, 10));
    } catch (e) {
      setResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => { setResult(null); setIpAddress(''); setCountry(''); };

  const ds = decisionStyle(result?.decision);
  const DecisionIcon = ds.icon ?? ShieldCheck;

  const selectStyle = {
    background: 'var(--bg-raised)', border: '1px solid var(--border)',
    borderRadius: 6, color: 'var(--text-primary)', fontSize: 13,
    padding: '9px 12px', width: '100%', outline: 'none',
    fontFamily: 'var(--font-ui)',
  };
  const inputStyle = { ...selectStyle, fontFamily: 'var(--font-mono)', fontSize: 12 };

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Risk Simulator</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Simulate Zero Trust policy decisions for any user and action
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 16 }}>
              Simulation Parameters
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>User</label>
              <select value={userId} onChange={e => setUserId(e.target.value)} style={selectStyle}>
                {users.map(u => (
                  <option key={u.user_id} value={u.user_id}>{u.first_name} {u.last_name} — {u.email}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>Action / Resource</label>
              <select value={action} onChange={e => setAction(e.target.value)} style={selectStyle}>
                {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>

            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10, marginTop: 4 }}>
              Context (optional)
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>IP Address</label>
              <input type="text" placeholder="e.g. 192.168.1.1" value={ipAddress} onChange={e => setIpAddress(e.target.value)} style={inputStyle} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Country</label>
              <input type="text" placeholder="e.g. US, CN, RU" value={country} onChange={e => setCountry(e.target.value)} style={inputStyle} />
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={handleSimulate} disabled={loading || !userId} style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                background: loading ? 'var(--bg-raised)' : 'var(--accent-amber)',
                color: loading ? 'var(--text-muted)' : '#000',
                border: 'none', borderRadius: 6, padding: '10px 0',
                fontSize: 13, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
              }}>
                <Play size={13} />
                {loading ? 'Simulating…' : 'Run Simulation'}
              </button>
              <button onClick={handleReset} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                borderRadius: 6, padding: '10px 14px', cursor: 'pointer', color: 'var(--text-secondary)',
              }}>
                <RotateCcw size={13} />
              </button>
            </div>
          </div>

          {history.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Recent Simulations
              </div>
              {history.map((h, i) => {
                const hds = decisionStyle(h.decision);
                return (
                  <div key={i} style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: hds.color, background: hds.color + '22', border: `1px solid ${hds.color}44`, borderRadius: 4, padding: '2px 6px' }}>
                      {hds.label}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{h.user}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{h.action}</div>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{h.ts.toLocaleTimeString()}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '28px 32px' }}>
          {!result ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: 300, gap: 12 }}>
              <ShieldCheck size={40} color="var(--text-muted)" />
              <div style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 500 }}>Configure parameters and run a simulation</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>The Zero Trust engine will evaluate the request and return a policy decision</div>
            </div>
          ) : result.error ? (
            <div style={{ color: 'var(--risk-high)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>{result.error}</div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32, paddingBottom: 28, borderBottom: '1px solid var(--border)' }}>
                <div style={{ width: 64, height: 64, borderRadius: 16, background: ds.color + '18', border: `2px solid ${ds.color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <DecisionIcon size={28} color={ds.color} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>Policy Decision</div>
                  <div style={{ fontSize: 36, fontFamily: 'var(--font-mono)', fontWeight: 800, color: ds.color, letterSpacing: '0.04em' }}>{result.decision}</div>
                </div>
              </div>

              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Risk Score</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: riskBarColor(result.risk_score) }}>
                    {result.risk_score} / 100 — {result.risk_level?.toUpperCase()}
                  </span>
                </div>
                <div style={{ height: 8, background: 'var(--bg-raised)', borderRadius: 4, overflow: 'hidden', border: '1px solid var(--border)' }}>
                  <div style={{ height: '100%', width: `${result.risk_score}%`, background: riskBarColor(result.risk_score), borderRadius: 4, transition: 'width 0.6s ease' }} />
                </div>
              </div>

              {result.reasoning && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Reasoning</div>
                  <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, padding: '12px 16px', background: 'var(--bg-raised)', borderRadius: 6, border: '1px solid var(--border)' }}>
                    {result.reasoning}
                  </div>
                </div>
              )}

              {result.recommended_action && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Recommended Action</div>
                  <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, padding: '12px 16px', background: 'var(--bg-raised)', borderRadius: 6, border: `1px solid ${ds.color}33` }}>
                    {result.recommended_action}
                  </div>
                </div>
              )}

              {result.factors_evaluated?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Factors Evaluated</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {result.factors_evaluated.map((f, i) => (
                      <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', padding: '8px 12px', background: 'var(--bg-raised)', borderRadius: 5, border: '1px solid var(--border)', borderLeft: `3px solid ${ds.color}` }}>
                        {f}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
