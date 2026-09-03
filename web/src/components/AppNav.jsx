import { NavLink } from 'react-router-dom';
import { Home, LayoutGrid, TicketPlus, Settings } from 'lucide-react';

const LINKS = [
  { to: '/', label: 'Home', icon: Home, end: true },
  { to: '/new/jira', label: 'New Jira project', icon: TicketPlus },
  { to: '/board', label: 'Jira board', icon: LayoutGrid },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function AppNav() {
  return (
    <nav className="app-global-nav" aria-label="Main navigation">
      <span className="app-global-nav-brand">AI Web Team</span>
      <div className="app-global-nav-links">
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `app-global-nav-link${isActive ? ' active' : ''}`}
          >
            <Icon size={14} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
