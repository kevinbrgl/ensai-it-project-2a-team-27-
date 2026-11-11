import { useState } from 'react';
import { Button } from './Button';
import { Modal } from './Modal';

/**
 * Asks for confirmation before a destructive action.
 * `onConfirm` may return a promise; the dialog stays open while it runs.
 */
export function ConfirmDialog({ open, title, message, confirmLabel = 'Delete', onConfirm, onClose }) {
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
      onClose();
    }
  };

  return (
    <Modal
      open={open}
      title={title}
      onClose={busy ? () => {} : onClose}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={confirm} loading={busy}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p style={{ color: 'var(--ink-700)' }}>{message}</p>
    </Modal>
  );
}
