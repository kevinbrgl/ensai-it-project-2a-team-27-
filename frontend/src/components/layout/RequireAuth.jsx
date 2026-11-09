import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { LibraryProvider } from '../../context/LibraryContext';
import { Spinner } from '../ui/Spinner';

/** Renders children only for signed-in users; others go to the sign-in page. */
export function RequireAuth({ children }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'checking') {
    return (
      <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', color: 'var(--text-muted)' }}>
        <Spinner size={24} />
      </div>
    );
  }
  if (status !== 'authenticated') {
    // After an expired session, come back to the same page once signed in.
    const state = status === 'signedOut' ? undefined : { from: location };
    return <Navigate to="/login" replace state={state} />;
  }
  return <LibraryProvider>{children}</LibraryProvider>;
}
