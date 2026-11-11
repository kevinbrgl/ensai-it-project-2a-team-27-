import { useState } from 'react';
import { useLibrary } from '../../context/LibraryContext';
import { READING_STATES } from '../../api/library';
import { STATUS_LABELS } from '../../utils/format';
import { Button } from '../ui/Button';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { Menu } from '../ui/Menu';

/**
 * The main action on a book: add it to the library (as "Want to read" by
 * default) or, once shelved, change its reading status or remove it.
 */
export function LibraryControl({ book, size = 'md' }) {
  const library = useLibrary();
  const entry = library.get(book.id_book);
  const [busy, setBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const run = async (action) => {
    setBusy(true);
    await action();
    setBusy(false);
  };

  if (!entry) {
    return (
      <div style={{ display: 'inline-flex', gap: 'var(--space-2)' }}>
        <Button variant="primary" size={size} icon="plus" loading={busy} onClick={() => run(() => library.add(book, 'WANT_TO_READ'))}>
          Want to read
        </Button>
        <Menu
          trigger={({ toggle }) => (
            <Button size={size} iconRight="chevronDown" onClick={toggle} disabled={busy}>
              Add as
            </Button>
          )}
          items={[
            { label: 'Currently reading', onSelect: () => run(() => library.add(book, 'READING')) },
            { label: 'Already finished', onSelect: () => run(() => library.add(book, 'COMPLETED')) },
          ]}
        />
      </div>
    );
  }

  return (
    <>
      <Menu
        trigger={({ toggle }) => (
          <Button size={size} icon="check" iconRight="chevronDown" loading={busy} onClick={toggle}>
            {STATUS_LABELS[entry.state]}
          </Button>
        )}
        items={[
          ...READING_STATES.map((state) => ({
            label: STATUS_LABELS[state],
            checked: entry.state === state,
            onSelect: () => state !== entry.state && run(() => library.setStatus(book.id_book, state)),
          })),
          { separator: true },
          { label: 'Remove from library', icon: 'trash', tone: 'danger', onSelect: () => setConfirmOpen(true) },
        ]}
      />
      <ConfirmDialog
        open={confirmOpen}
        title="Remove from your library?"
        message={`“${book.title}” will leave your library, along with its like and favorite. Your review, if any, is kept.`}
        confirmLabel="Remove"
        onConfirm={() => library.remove(book.id_book)}
        onClose={() => setConfirmOpen(false)}
      />
    </>
  );
}
