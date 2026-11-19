import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import * as playlistsApi from '../api/playlists';
import { BookCover } from '../components/books/BookCover';
import { PlaylistNameDialog } from '../components/books/PlaylistNameDialog';
import { Button } from '../components/ui/Button';
import { Icon } from '../components/ui/Icon';
import { PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useToast } from '../context/ToastContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { plural } from '../utils/format';
import styles from './PlaylistsPage.module.css';

export function PlaylistsPage() {
  useDocumentTitle('Playlists');
  const toast = useToast();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useAsync(playlistsApi.listPlaylistDetails, []);
  const [creating, setCreating] = useState(false);

  const create = async (name) => {
    try {
      const playlist = await playlistsApi.createPlaylist(name);
      toast.success(`Playlist “${playlist.name}” created.`);
      navigate(`/playlists/${playlist.id_playlist}`);
      return null;
    } catch (err) {
      return err.status === 409 ? 'You already have a playlist with this name.' : err.message;
    }
  };

  return (
    <>
      <PageHeader
        title="Playlists"
        description="Bring books together for a reading group, a project or your next trip."
        actions={
          <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
            New playlist
          </Button>
        }
      />

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && !data && (
        <div className={styles.list} aria-busy="true" aria-label="Loading playlists">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={100} radius="var(--radius-sm)" />
          ))}
        </div>
      )}
      {!error && data?.length === 0 && (
        <EmptyState
          icon="playlists"
          title="No playlists yet"
        >
          Create a playlist above, then open a book and choose “Save to playlist.”
        </EmptyState>
      )}
      {!error && data?.length > 0 && (
        <ul className={styles.list}>
          {data.map((playlist) => (
            <li key={playlist.id_playlist}>
              <Link to={`/playlists/${playlist.id_playlist}`} className={styles.playlist}>
                <div className={styles.covers} aria-hidden="true">
                  {playlist.books.slice(0, 3).map((book) => (
                    <BookCover key={book.id_book} book={book} size="sm" decorative />
                  ))}
                  {!playlist.books.length && <Icon name="playlists" size={32} />}
                </div>
                <div className={styles.playlistText}>
                  <h2 className={styles.playlistName}>{playlist.name}</h2>
                  <span className={`${styles.playlistCount} tabular`}>{plural(playlist.books.length, 'book')}</span>
                </div>
                <Icon name="arrowRight" className={styles.arrow} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      <PlaylistNameDialog open={creating} title="New playlist" submitLabel="Create playlist" onSubmit={create} onClose={() => setCreating(false)} />
    </>
  );
}
