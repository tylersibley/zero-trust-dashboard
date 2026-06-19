import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Activity, Shield, FlaskConical, Brain } from 'lucide-react';

const nav = [
  { to: '/',           icon: LayoutDashboard, label: 'Overview'   },
  { to: '/users',      icon: Users,           label: 'Users'      },
  { to: '/live-feed',  icon: Activity,        label: 'Live Feed'  },
  { to: '/simulate',   icon: FlaskConical,    label: 'Simulator'  },
  { to: '/anomalies',  icon: Brain,           label: 'Anomalies'  },
];

export default function Layout({ children }) {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <aside style={{
        width: 220, flexShrink: 0,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', padding: '24px 0',
      }}>
        <div style={{ padding: '0 20px 28px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Shield size={18} color="var(--accent-amber)" />
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>ZERO TRUST</span>
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 2, letterSpacing: '0.08em' }}>SECURITY DASHBOARD</div>
        </div>

        <nav style={{ padding: '16px 12px', flex: 1 }}>
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 12px', borderRadius: 6, marginBottom: 2,
                color: isActive ? 'var(--accent-amber)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-amber-dim)' : 'transparent',
                textDecoration: 'none', fontSize: 13, fontWeight: 500, transition: 'all 0.15s',
              })}>
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>OKTA DEV ORG</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>integrator-1985580</div>
        </div>
      </aside>

      <main style={{ flex: 1, overflow: 'auto', padding: '32px 36px' }}>
        {children}
      </main>
    </div>
  );
}
