export default function RiskGauge({ score }) {
  const pct = Math.min(100, Math.max(0, score ?? 0));
  const color =
    pct < 30 ? 'var(--risk-low)' :
    pct < 60 ? 'var(--risk-medium)' :
    pct < 80 ? 'var(--risk-high)' :
    'var(--risk-critical)';
  const label = pct < 30 ? 'LOW' : pct < 60 ? 'MEDIUM' : pct < 80 ? 'HIGH' : 'CRITICAL';

  const r = 54, cx = 80, cy = 80;
  const startAngle = Math.PI;
  const endAngle = startAngle + (pct / 100) * Math.PI;
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = pct > 50 ? 1 : 0;

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '20px 24px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    }}>
      <div style={{
        fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
        color: 'var(--text-muted)', textTransform: 'uppercase',
        marginBottom: 8, alignSelf: 'flex-start',
      }}>Org Risk Score</div>
      <svg width={160} height={100} viewBox="0 0 160 100">
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke="var(--border)" strokeWidth={8} strokeLinecap="round" />
        {pct > 0 && (
          <path d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none" stroke={color} strokeWidth={8} strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 6} textAnchor="middle" fill="var(--text-primary)"
          fontSize={22} fontWeight={700} fontFamily="JetBrains Mono, monospace">
          {Math.round(pct)}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill={color}
          fontSize={9} fontWeight={600} letterSpacing={1.5} fontFamily="Inter, sans-serif">
          {label}
        </text>
      </svg>
    </div>
  );
}
