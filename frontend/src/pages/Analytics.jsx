import { useEffect, useState } from 'react';
import { fetchSummary } from '../api/client';
import api from '../api/client';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, Legend,
} from 'recharts';

const RISK_COLORS = {
  low:      '#3FB950',
  medium:   '#D29922',
  high:     '#F85149',
  critical: '#FF6E40',
};

const CHART_TOOLTIP = {
  contentStyle: {
    background: '#1C2128',
    border: '1px solid #30363D',
    borderRadius: 6,
    fontSize: 12,
    fontFamily: 'JetBrains Mono, monospace',
    color: '#E6EDF3',
  },
  cursor: { fill: 'rgba(255,255,255,0.04)' },
};

function SectionHeader({ title, sub }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function Card({ children, style }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '20px 24px',
      ...style,
    }}>
      {children}
    </div>
  );
}

export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [scores, setScores] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchSummary(),
      api.get('/risk/scores'),
      api.get('/users'),
    ]).then(([s, sc, u]) => {
      setSummary(s.data);
      const scoreList = Array.isArray(sc.data) ? sc.data : (sc.data.value ?? []);
      setScores(scoreList);
      const userList = Array.isArray(u.data) ? u.data : (u.data.value ?? u.data.users ?? []);
      setUsers(userList);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-muted)' }}>
      Loading analytics…
    </div>
  );

  // --- Chart 1: Risk score per user (bar chart) ---
  const userMap = {};
  users.forEach(u => { userMap[u.user_id] = u.first_name ? `${u.first_name} ${u.last_name}` : u.login; });

  const scoreChartData = scores.map(s => ({
    name: userMap[s.user_id] ? userMap[s.user_id].split(' ')[0] : s.user_id.slice(-6),
    score: s.score,
    level: s.level,
    fill: RISK_COLORS[s.level] ?? '#8B949E',
  }));

  // --- Chart 2: Risk distribution (pie chart) ---
  const dist = summary?.risk_distribution ?? {};
  const pieData = [
    { name: 'Low',    value: dist.low    ?? 0, color: RISK_COLORS.low    },
    { name: 'Medium', value: dist.medium ?? 0, color: RISK_COLORS.medium },
    { name: 'High',   value: dist.high   ?? 0, color: RISK_COLORS.high   },
  ].filter(d => d.value > 0);

  // If no dist data, derive from scores
  const derivedPie = pieData.length > 0 ? pieData : (() => {
    const counts = { low: 0, medium: 0, high: 0, critical: 0 };
    scores.forEach(s => { if (counts[s.level] !== undefined) counts[s.level]++; });
    return Object.entries(counts).filter(([, v]) => v > 0).map(([k, v]) => ({
      name: k.charAt(0).toUpperCase() + k.slice(1),
      value: v,
      color: RISK_COLORS[k],
    }));
  })();

  // --- Chart 3: Per-user security radar ---
  const radarData = users.slice(0, 3).map(u => {
    const score = scores.find(s => s.user_id === u.user_id);
    return {
      user: u.first_name ?? u.login.split('@')[0],
      'Risk Score':   Math.round(score?.score ?? 0),
      'Failed Logins': Math.min(100, (u.failed_login_count ?? 0) * 20),
      'MFA Gap':      u.mfa_enrolled ? 0 : 100,
      'Event Count':  Math.min(100, (u.recent_event_count ?? 0) * 10),
    };
  });

  // --- Summary stats row ---
  const avgScore = scores.length > 0
    ? (scores.reduce((a, b) => a + b.score, 0) / scores.length).toFixed(1)
    : '—';
  const highCount = scores.filter(s => s.level === 'high' || s.level === 'critical').length;
  const mfaGap = users.filter(u => !u.mfa_enrolled).length;

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Analytics</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Risk distribution, user scores, and security posture overview
        </p>
      </div>

      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Users Scored',    value: scores.length,    color: 'var(--accent-amber)' },
          { label: 'Avg Risk Score',  value: avgScore,         color: 'var(--risk-medium)'  },
          { label: 'High/Critical',   value: highCount,        color: 'var(--risk-high)'    },
          { label: 'No MFA',          value: mfaGap,           color: 'var(--risk-high)'    },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 28, fontFamily: 'var(--font-mono)', fontWeight: 700, color }}>{value}</div>
          </Card>
        ))}
      </div>

      {/* Charts row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>

        {/* Bar chart: risk scores per user */}
        <Card>
          <SectionHeader title="Risk Score by User" sub="Current scores from /api/v1/risk/scores" />
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={scoreChartData} barSize={32}>
              <XAxis dataKey="name" tick={{ fill: '#8B949E', fontSize: 12, fontFamily: 'Inter' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#484F58', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...CHART_TOOLTIP} formatter={(v) => [`${v} / 100`, 'Risk Score']} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {scoreChartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Pie chart: risk distribution */}
        <Card>
          <SectionHeader title="Risk Level Distribution" sub="Breakdown of users by risk tier" />
          {derivedPie.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 220, color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
              No risk data available
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
              <ResponsiveContainer width="60%" height={220}>
                <PieChart>
                  <Pie data={derivedPie} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                    {derivedPie.map((entry, i) => (
                      <Cell key={i} fill={entry.color} stroke="var(--bg-surface)" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip {...CHART_TOOLTIP} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ flex: 1 }}>
                {derivedPie.map(({ name, value, color }) => (
                  <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: color, flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{name}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Radar chart: per-user security posture */}
      {radarData.length > 0 && (
        <Card>
          <SectionHeader title="User Security Posture" sub="Multi-factor comparison across top 3 users (higher = worse)" />
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData} cx="50%" cy="50%">
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="user" tick={{ fill: '#8B949E', fontSize: 12 }} />
              {['Risk Score', 'Failed Logins', 'MFA Gap', 'Event Count'].map((key, i) => (
                <Radar
                  key={key}
                  name={key}
                  dataKey={key}
                  stroke={['#F59E0B', '#3FB950', '#F85149', '#8B949E'][i]}
                  fill={['#F59E0B', '#3FB950', '#F85149', '#8B949E'][i]}
                  fillOpacity={0.08}
                  strokeWidth={2}
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 12, color: '#8B949E' }} />
              <Tooltip {...CHART_TOOLTIP} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
