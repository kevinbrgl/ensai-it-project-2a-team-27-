import { useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate, useNavigationType } from 'react-router-dom';
import { getUserGenreWheel } from '../../api/users';
import { useAuth } from '../../context/AuthContext';
import { useLibrary } from '../../context/LibraryContext';
import { useToast } from '../../context/ToastContext';
import { useAsync } from '../../hooks/useAsync';
import { GenreWheelAvatar } from '../stats/GenreWheelAvatar';
import { Icon } from '../ui/Icon';
import { Menu } from '../ui/Menu';
import { Wordmark } from './Wordmark';
import styles from './AppLayout.module.css';

const NAV = [
  { to: '/', label: 'Home' },
  { to: '/discover', label: 'Discover' },
  { to: '/library', label: 'My library' },
  { to: '/playlists', label: 'Playlists' },
  { to: '/readers', label: 'Readers' },
  { to: '/progress', label: 'Progress' },
];

function Masthead({ wheel }) {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState('');

  const search = (event) => {
    event.preventDefault();
    if (query.trim()) {
      navigate(`/discover?q=${encodeURIComponent(query.trim())}`);
      setMenuOpen(false);
      setQuery('');
    }
  };

  const signOut = async () => {
    try {
      await logout();
      toast.success('You are signed out.');
    } catch (error) {
      toast.error(error.message);
    }
  };

  return (
    <header className={styles.masthead}>
      <div className={styles.bar}>
        <NavLink to="/" className={styles.brand} aria-label="Ex-Libris home"><Wordmark /></NavLink>
        <button
          type="button" className={styles.menuToggle} onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} aria-controls="main-navigation"
        >
          <Icon name={menuOpen ? 'x' : 'menu'} />
        </button>
        <div className={`${styles.navigation} ${menuOpen ? styles.open : ''}`} id="main-navigation">
          <nav className={styles.nav} aria-label="Main">
            {NAV.map(({ to, label }) => (
              <NavLink key={to} to={to} end={to === '/'} onClick={() => setMenuOpen(false)}
                className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <form className={styles.search} onSubmit={search} role="search">
            <Icon name="search" size={16} />
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)}
              placeholder="Search books" aria-label="Quick search" />
          </form>
        </div>
        <Menu align="end"
          trigger={({ open, toggle }) => (
            <button type="button" className={styles.account} onClick={toggle}
              aria-label={`Account menu for ${user.username}`} aria-describedby={wheel ? 'account-genres' : undefined}
              aria-haspopup="menu" aria-expanded={open}>
              <GenreWheelAvatar user={user} wheel={wheel} size={44} descriptionId="account-genres" />
              <Icon name="chevronDown" size={14} />
            </button>
          )}
          items={[
            { label: 'My profile', icon: 'book', onSelect: () => navigate(`/users/${user.id_user}`) },
            { label: 'Account settings', icon: 'settings', onSelect: () => navigate('/settings') },
            { separator: true },
            { label: 'Sign out', icon: 'logout', onSelect: signOut },
          ]}
        />
      </div>
    </header>
  );
}

export function AppLayout() {
  const { user } = useAuth();
  const { books, loading } = useLibrary();
  const finishedBooks = useMemo(() => books.filter((book) => book.state === 'COMPLETED')
    .map((book) => `${book.id_book}:${book.is_favorite}`).join(','), [books]);
  const accountWheel = useAsync(() => getUserGenreWheel(user.id_user), [user.id_user, finishedBooks], { skip: loading });
  const { pathname } = useLocation();
  const navigationType = useNavigationType();
  useEffect(() => {
    if (navigationType !== 'POP') window.scrollTo(0, 0);
  }, [pathname, navigationType]);

  return (
    <>
      <a className={styles.skip} href="#main-content">Skip to content</a>
      {/* Keyed by route so the mobile menu and quick search reset on navigation. */}
      <Masthead key={`masthead:${pathname}`} wheel={accountWheel.error ? null : accountWheel.data} />
      <main id="main-content" className={styles.content} key={pathname} tabIndex={-1}>
        <Outlet context={accountWheel} />
      </main>
    </>
  );
}
