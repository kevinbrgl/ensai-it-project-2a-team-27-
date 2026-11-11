import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { Avatar } from '../ui/Avatar';
import { Icon } from '../ui/Icon';
import styles from './AppLayout.module.css';

const NAV = [
  { to: '/', label: 'Home', icon: 'home', end: true },
  { to: '/discover', label: 'Discover', icon: 'compass' },
  { to: '/catalog', label: 'Catalog', icon: 'grid' },
  { to: '/library', label: 'My library', icon: 'library' },
  { to: '/shelves', label: 'Shelves', icon: 'shelves' },
  { to: '/readers', label: 'Readers', icon: 'users' },
  { to: '/progress', label: 'Progress', icon: 'chart' },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  // The mobile menu closes by itself on navigation: it stays open only for
  // the page on which it was opened.
  const [menuPath, setMenuPath] = useState(null);
  const menuOpen = menuPath === location.pathname;
  const [query, setQuery] = useState('');

  const search = (event) => {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    navigate(`/discover?q=${encodeURIComponent(q)}`);
    setQuery('');
  };

  const signOut = async () => {
    await logout();
    toast.success('You are signed out.');
  };

  return (
    <div className={styles.shell}>
      <aside className={`${styles.sidebar} ${menuOpen ? styles.open : ''}`}>
        <div className={styles.brandRow}>
          <NavLink to="/" className={styles.brand}>
            Ex-Libris
          </NavLink>
          <button
            type="button"
            className={styles.menuToggle}
            onClick={() => setMenuPath(menuOpen ? null : location.pathname)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
          >
            <Icon name={menuOpen ? 'x' : 'menu'} />
          </button>
        </div>

        <div className={styles.collapsible}>
          <form className={styles.search} onSubmit={search} role="search">
            <Icon name="search" size={16} className={styles.searchIcon} />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search books"
              aria-label="Quick search"
            />
          </form>

          <nav className={styles.nav} aria-label="Main">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}
              >
                <Icon name={item.icon} size={18} />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className={styles.account}>
            <NavLink
              to="/settings"
              className={({ isActive }) => `${styles.profile} ${isActive ? styles.active : ''}`}
              title="Account settings"
            >
              <Avatar user={user} size={30} />
              <span className={styles.username}>{user.username}</span>
              <Icon name="settings" size={16} className={styles.settingsIcon} />
            </NavLink>
            <button type="button" className={styles.logout} onClick={signOut}>
              <Icon name="logout" size={18} />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.content} key={location.pathname}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
