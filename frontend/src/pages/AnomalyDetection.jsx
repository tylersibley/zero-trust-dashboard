import { useEffect, useState } from 'react';
import { fetchAtRiskUsers, fetchBaseline } from '../api/client';
import api from '../api/client';
import { Brain, Zap, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const riskColor = (level) =>
  level === 'critical' ? 'var(--risk-critical)' :
  level === 'high'     ? 'var(--risk-high)' :
  level === 'medium'   ? 'var(--risk-medium)' : 'var(--risk-low)';

function ScoreBar({ label, value, max = 1, color }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: color || 'var(--text-primary)', fontWeight: 600 }}>
          {typeof value === 'number' ? value.toFixed(3) : value}
        </span>
      </div>
      <div style={{ height: 6, background: 'var(--bg-raised)', borderRadius: 3, overflow: 'hidden', border: '1px solid var(--border)' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color || 'var(--accent-amber)', borderRadius: 3, transition: 'width 0.5s ease' }} />
      </div>
    </div>
  );
}

export default function AnomalyDetection() {
  const [users, setUsers] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [baseline, setBaseline] = useState(null);
  const [scoreResult, setScoreResult] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState(null);

  // Editable event inputs
  const [hour, setHour] = useState('23');
  const [ip, setIp] = useState('');
  const [country, setCountry] = useState('US');
  const [outcome, setOutcome] = useState('SUCCESS');

  useEffect(() => {
    fetchAtRiskUsers().then(u => {
      const list = Array.isArray(u.data) ? u.data : (u.data.value ?? u.data.users ?? []);
      setUsers(list);
      if (list.length > 0) setSelectedId(list[0].user_id);
    });
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setBaseline(null);
    setScoreResult(null);
    fetchBaseline(selectedId).then(r => setBaseline(r.data)).catch(() => {});
  }, [selectedId]);

  const handleTrain = async () => {
    setTraining(true);
    setTrainResult(null);
    try {
      const res = await api.post(`/ml/train/${selectedId}`);
      setTrainResult(res.data);
      // Refresh baseline after training
      fetchBaseline(selectedId).then(r => setBaseline(r.data)).catch(() => {});
    } catch (e) {
      setTrainResult({ error: e.message });
    } finally {
      setTraining(false);
    }
  };

  const handleScore = async () => {
    setScoring(true);
    setScoreResult(null);
    try {
      const payload = {
        user_id: selectedId,
        hour: parseInt(hour),
        outcome,
      };
      if (ip) payload.ip_address = ip;
      if (country) payload.country = country;

      const res = await api.post('/ml/score', payload);
      setScoreResult(res.data);
    } catch (e) {
      setScoreResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setScoring(false);
    }
  };

  const user = users.find(u => u.user_id === selectedId);
  const profile = baseline?.behavioral_profile ?? {};

  const inputStyle = {
    background: 'var(--bg-raised)', border: '1px solid var(--border)',
    borderRadius: 6, color: 'var(--text-primary)', fontSize: 12,
    padding: '8px 10px', width: '100%', outline: 'none',
    fontFamily: 'var(--font-mono)',
  };
  const selectStyle = { ...inputStyle, fontFamily: 'var(--font-ui)', fontSize: 13 };

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Anomaly Detection</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Isolation Forest ML model — score events against user behavioral baselines
        </p>
      </div>

      {/* User selector */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {users.map(u => (
          <button key={u.user_id} onClick={() => setSelectedId(u.user_id)} style={{
            padding: '7px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border)',
            background: selectedId === u.user_id ? 'var(--accent-amber-dim)' : 'var(--bg-surface)',
            color: selectedId === u.user_id ? 'var(--accent-amber)' : 'var(--text-secondary)',
          }}>
            {u.first_name} {u.last_name}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Left col */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Baseline card */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Brain size={15} color="var(--accent-amber)" />
                <span style={{ fontSize: 13, fontWeight: 600 }}>Behavioral Baseline</span>
              </div>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                padding: '2px 8px', borderRadius: 4,
                color: baseline?.model_trained ? 'var(--risk-low)' : 'var(--risk-medium)',
                background: baseline?.model_trained ? 'rgba(63,185,80,0.12)' : 'rgba(210,153,34,0.12)',
                border: `1px solid ${baseline?.model_trained ? 'rgba(63,185,80,0.3)' : 'rgba(210,153,34,0.3)'}`,
              }}>
                {baseline?.model_trained ? 'TRAINED' : 'NOT TRAINED'}
              </span>
            </div>

            {baseline ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                  {[
                    { label: 'Typical Login', value: profile.typical_login_hour ?? '—' },
                    { label: 'Events Analyzed', value: baseline.total_events_analyzed ?? '—' },
                    { label: 'Known IPs', value: profile.known_ip_count ?? '—' },
                    { label: 'Failure Rate', value: profile.historical_failure_rate ?? '—' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ background: 'var(--bg-raised)', borderRadius: 6, padding: '10px 12px', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: 4 }}>{label}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', padding: '8px 10px', background: 'var(--bg-raised)', borderRadius: 5 }}>
                  {baseline.note}
                </div>
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>Loading baseline…</div>
            )}

            {/* Train button */}
            <button onClick={handleTrain} disabled={training} style={{
              width: '100%', marginTop: 14, padding: '9px 0',
              background: training ? 'var(--bg-raised)' : 'transparent',
              border: '1px solid var(--border)', borderRadius: 6,
              color: training ? 'var(--text-muted)' : 'var(--text-secondary)',
              fontSize: 12, fontWeight: 500, cursor: training ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              <Brain size={12} />
              {training ? 'Training model…' : 'Re-train Model'}
            </button>

            {trainResult && !trainResult.error && (
              <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(63,185,80,0.08)', border: '1px solid rgba(63,185,80,0.25)', borderRadius: 5, fontSize: 12, color: 'var(--risk-low)', fontFamily: 'var(--font-mono)' }}>
                ✓ {trainResult.message} ({trainResult.events_used} events)
              </div>
            )}
            {trainResult?.error && (
              <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.25)', borderRadius: 5, fontSize: 12, color: 'var(--risk-high)', fontFamily: 'var(--font-mono)' }}>
                {trainResult.error}
              </div>
            )}
          </div>

          {/* Score event form */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Zap size={15} color="var(--accent-amber)" />
              <span style={{ fontSize: 13, fontWeight: 600 }}>Score an Event</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Login Hour (0–23)</label>
                <input type="number" min="0" max="23" value={hour} onChange={e => setHour(e.target.value)} style={inputStyle} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Outcome</label>
                <select value={outcome} onChange={e => setOutcome(e.target.value)} style={selectStyle}>
                  <option value="SUCCESS">SUCCESS</option>
                  <option value="FAILURE">FAILURE</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>IP Address</label>
                <input type="text" placeholder="e.g. 10.0.0.1" value={ip} onChange={e => setIp(e.target.value)} style={inputStyle} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Country</label>
                <input type="text" placeholder="e.g. US, CN" value={country} onChange={e => setCountry(e.target.value)} style={inputStyle} />
              </div>
            </div>

            <button onClick={handleScore} disabled={scoring} style={{
              width: '100%', marginTop: 4, padding: '10px 0',
              background: scoring ? 'var(--bg-raised)' : 'var(--accent-amber)',
              border: 'none', borderRadius: 6,
              color: scoring ? 'var(--text-muted)' : '#000',
              fontSize: 13, fontWeight: 700, cursor: scoring ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              <Zap size={13} />
              {scoring ? 'Scoring…' : 'Score Event'}
            </button>
          </div>
        </div>

        {/* Right: Score result */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '28px 32px' }}>
          {!scoreResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: 320, gap: 12 }}>
              <Brain size={40} color="var(--text-muted)" />
              <div style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 500 }}>Score an event to see ML output</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', maxWidth: 280, lineHeight: 1.6 }}>
                The Isolation Forest model will compare the event against this user's behavioral baseline and return an anomaly score.
              </div>
            </div>
          ) : scoreResult.error ? (
            <div style={{ color: 'var(--risk-high)', fontFamily: 'var(--font-mono)', fontSize: 13, padding: 16, background: 'rgba(248,81,73,0.08)', borderRadius: 6, border: '1px solid rgba(248,81,73,0.25)' }}>
              {scoreResult.error}
            </div>
          ) : (
            <div>
              {/* Anomaly verdict */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28, paddingBottom: 24, borderBottom: '1px solid var(--border)' }}>
                <div style={{
                  width: 64, height: 64, borderRadius: 16, flexShrink: 0,
                  background: scoreResult.is_anomaly ? 'rgba(248,81,73,0.12)' : 'rgba(63,185,80,0.12)',
                  border: `2px solid ${scoreResult.is_anomaly ? 'rgba(248,81,73,0.4)' : 'rgba(63,185,80,0.4)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {scoreResult.is_anomaly
                    ? <XCircle size={28} color="var(--risk-high)" />
                    : <CheckCircle size={28} color="var(--risk-low)" />
                  }
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
                    Anomaly Detection Result
                  </div>
                  <div style={{ fontSize: 32, fontFamily: 'var(--font-mono)', fontWeight: 800, color: scoreResult.is_anomaly ? 'var(--risk-high)' : 'var(--risk-low)' }}>
                    {scoreResult.is_anomaly ? 'ANOMALY' : 'NORMAL'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    Risk level: <span style={{ color: riskColor(scoreResult.risk_level), fontWeight: 600 }}>{scoreResult.risk_level?.toUpperCase()}</span>
                  </div>
                </div>
              </div>

              {/* Scores */}
              <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 12 }}>ML Scores</div>
                <ScoreBar
                  label="Anomaly Score (higher = more anomalous)"
                  value={Math.abs(scoreResult.anomaly_score ?? 0)}
                  max={1}
                  color={scoreResult.is_anomaly ? 'var(--risk-high)' : 'var(--risk-low)'}
                />
                <ScoreBar
                  label="Confidence"
                  value={scoreResult.confidence ?? 0}
                  max={1}
                  color="var(--accent-amber)"
                />
              </div>

              {/* Anomalous features */}
              {scoreResult.anomalous_features?.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>Anomalous Features</div>
                  {scoreResult.anomalous_features.map((f, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '8px 12px', marginBottom: 6,
                      background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.2)',
                      borderRadius: 5, borderLeft: '3px solid var(--risk-high)',
                    }}>
                      <AlertTriangle size={12} color="var(--risk-high)" />
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{f}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Baseline comparison */}
              {scoreResult.baseline_comparison && Object.keys(scoreResult.baseline_comparison).length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>Baseline Comparison</div>
                  <div style={{ background: 'var(--bg-raised)', borderRadius: 6, border: '1px solid var(--border)', overflow: 'hidden' }}>
                    {Object.entries(scoreResult.baseline_comparison).map(([key, val], i, arr) => (
                      <div key={key} style={{
                        display: 'flex', justifyContent: 'space-between', padding: '10px 14px',
                        borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
                      }}>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                        <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Scored at {scoreResult.scored_at ? new Date(scoreResult.scored_at).toLocaleString() : '—'}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
