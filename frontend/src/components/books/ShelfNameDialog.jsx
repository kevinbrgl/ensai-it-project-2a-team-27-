import { useState } from 'react';
import { Button } from '../ui/Button';
import { Field } from '../ui/Field';
import { Modal } from '../ui/Modal';

/** Create or rename a shelf. `onSubmit(name)` returns an error message or null. */
export function ShelfNameDialog({ open, title, onClose, ...formProps }) {
  return (
    <Modal open={open} title={title} onClose={onClose} size="sm">
      {/* Mounted only while open, so the form starts fresh every time. */}
      <ShelfNameForm onClose={onClose} {...formProps} />
    </Modal>
  );
}

function ShelfNameForm({ initialName = '', submitLabel, onSubmit, onClose }) {
  const [name, setName] = useState(initialName);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    const clean = name.trim();
    if (!clean) return setError('Give the shelf a name.');
    if (clean.length > 100) return setError('At most 100 characters.');
    if (clean === initialName) return onClose();
    setBusy(true);
    const failure = await onSubmit(clean);
    setBusy(false);
    if (failure) setError(failure);
    else onClose();
  };

  return (
    <form onSubmit={submit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        <Field
          label="Shelf name"
          placeholder="e.g. Books that made me cry"
          value={name}
          maxLength={100}
          onChange={(e) => {
            setName(e.target.value);
            setError('');
          }}
          error={error}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={busy}>
            {submitLabel}
          </Button>
        </div>
    </form>
  );
}
