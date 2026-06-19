export default function StatCard({ label, value, sub, accent, mono }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '20px 24px',
      borderTop: accent ? `2px solid ${accent}` : '1px solid var(--border)',
    }}>
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.08em',
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        marginBottom: 10,
      }}>{label}</div>
      <div style={{
        fontSize: 30,
        fontFamily: mono ? 'var(--font-mono)' : 'var(--font-ui)',
        fontWeight: 700,
        color: accent || 'var(--text-primary)',
        lineHeight: 1,
      }}>{value ?? '—'}</div>
      {sub && (
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>{sub}</div>
      )}
    </div>
  );
}
