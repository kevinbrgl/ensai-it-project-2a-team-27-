import { createContext, useCallback, useContext, useMemo } from 'react';
import { useAsync } from '../hooks/useAsync';
import * as libraryApi from '../api/library';
import { STATUS_LABELS } from '../utils/format';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

const LibraryContext = createContext(null);

/**
 * Keeps the current user's library in memory so every screen knows whether a
 * book is already shelved, and exposes the library actions with feedback.
 */
export function LibraryProvider({ children }) {
  const { user } = useAuth();
  const toast = useToast();
  const { data, error, loading, reload: refresh, setData } = useAsync(libraryApi.listMyLibrary, [user?.id_user]);
  const books = useMemo(() => data || [], [data]);
  const entries = useMemo(() => new Map(books.map((item) => [item.id_book, item])), [books]);

  // Merges a LibraryBookRead (no book details) into the stored entry.
  const merge = useCallback(
    (activity, book) => {
      setData((list = []) => {
        const index = list.findIndex((item) => item.id_book === activity.id_book);
        if (index === -1) return [...list, { ...book, ...activity }];
        const copy = [...list];
        copy[index] = { ...copy[index], ...activity };
        return copy;
      });
    },
    [setData],
  );

  const add = useCallback(
    async (book, state) => {
      try {
        const activity = await libraryApi.addToLibrary(book.id_book, state);
        merge(activity, book);
        toast.success(`Added to your library as “${STATUS_LABELS[state]}”.`);
        return true;
      } catch (err) {
        toast.error(err.message);
        return false;
      }
    },
    [merge, toast],
  );

  const setStatus = useCallback(
    async (idBook, state) => {
      try {
        merge(await libraryApi.updateStatus(idBook, state));
        toast.success(state === 'COMPLETED' ? 'Marked as finished.' : `Moved to “${STATUS_LABELS[state]}”.`);
        return true;
      } catch (err) {
        toast.error(err.message);
        return false;
      }
    },
    [merge, toast],
  );

  const remove = useCallback(
    async (idBook) => {
      try {
        await libraryApi.removeFromLibrary(idBook);
        setData((list = []) => list.filter((item) => item.id_book !== idBook));
        toast.success('Removed from your library.');
        return true;
      } catch (err) {
        toast.error(err.message);
        return false;
      }
    },
    [setData, toast],
  );

  const toggleLike = useCallback(
    async (idBook) => {
      try {
        const activity = await libraryApi.toggleLike(idBook);
        merge(activity);
        toast.success(activity.is_liked ? 'Liked.' : 'Like removed.');
      } catch (err) {
        toast.error(err.message);
      }
    },
    [merge, toast],
  );

  const toggleFavorite = useCallback(
    async (idBook) => {
      try {
        const activity = await libraryApi.toggleFavorite(idBook);
        merge(activity);
        toast.success(activity.is_favorite ? 'Added to favorites.' : 'Removed from favorites.');
      } catch (err) {
        toast.error(err.message);
      }
    },
    [merge, toast],
  );

  const value = useMemo(
    () => ({
      entries,
      books,
      loading,
      error,
      refresh,
      get: (idBook) => entries.get(Number(idBook)) || null,
      add,
      setStatus,
      remove,
      toggleLike,
      toggleFavorite,
    }),
    [entries, books, loading, error, refresh, add, setStatus, remove, toggleLike, toggleFavorite],
  );

  return <LibraryContext.Provider value={value}>{children}</LibraryContext.Provider>;
}

export function useLibrary() {
  const context = useContext(LibraryContext);
  if (!context) throw new Error('useLibrary must be used inside <LibraryProvider>');
  return context;
}
