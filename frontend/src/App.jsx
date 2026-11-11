import { Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { RequireAuth } from './components/layout/RequireAuth';
import { AuthPage } from './pages/AuthPage';
import { BookPage } from './pages/BookPage';
import { CatalogPage } from './pages/CatalogPage';
import { DiscoverPage } from './pages/DiscoverPage';
import { HomePage } from './pages/HomePage';
import { LibraryPage } from './pages/LibraryPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProgressPage } from './pages/ProgressPage';
import { ReadersPage } from './pages/ReadersPage';
import { SettingsPage } from './pages/SettingsPage';
import { ShelfPage } from './pages/ShelfPage';
import { ShelvesPage } from './pages/ShelvesPage';
import { UserPage } from './pages/UserPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="discover" element={<DiscoverPage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="books/:bookId" element={<BookPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="shelves" element={<ShelvesPage />} />
        <Route path="shelves/:shelfId" element={<ShelfPage />} />
        <Route path="readers" element={<ReadersPage />} />
        <Route path="users/:userId" element={<UserPage />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
