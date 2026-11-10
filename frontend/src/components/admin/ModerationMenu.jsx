import { useState } from 'react';
import { banUser, suspendUser } from '../../api/admin';
import { useToast } from '../../context/ToastContext';
import { formatDate } from '../../utils/format';
import { Button } from '../ui/Button';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { Field } from '../ui/Field';
import { Menu } from '../ui/Menu';
import { Modal } from '../ui/Modal';

/** Admin-only menu on a profile: suspend for N days or ban for good. */
export function ModerationMenu({ user }) {
  const toast = useToast();
  const [dialog, setDialog] = useState(null); // 'suspend' | 'ban' | null

  const ban = async () => {
    try {
      await banUser(user.id_user);
      toast.success(`${user.username} has been banned.`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <Menu
        align="end"
        trigger={({ toggle }) => (
          <Button icon="alert" onClick={toggle}>
            Moderate
          </Button>
        )}
        items={[
          { label: 'Suspend…', onSelect: () => setDialog('suspend') },
          { label: 'Ban permanently', icon: 'trash', tone: 'danger', onSelect: () => setDialog('ban') },
        ]}
      />
      <SuspendDialog open={dialog === 'suspend'} user={user} onClose={() => setDialog(null)} />
      <ConfirmDialog
        open={dialog === 'ban'}
        title={`Ban ${user.username}?`}
        message="They will be signed out and will never be able to sign in again."
        confirmLabel="Ban account"
        onConfirm={ban}
        onClose={() => setDialog(null)}
      />
    </>
  );
}

function SuspendDialog({ open, user, onClose }) {
  const toast = useToast();
  const [days, setDays] = useState('7');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    const value = Number(days);
    if (!Number.isInteger(value) || value < 1 || value > 365) {
      setError('Enter a number of days between 1 and 365.');
      return;
    }
    setBusy(true);
    try {
      const status = await suspendUser(user.id_user, value);
      toast.success(`${user.username} is suspended until ${formatDate(status.suspended_until)}.`);
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      title={`Suspend ${user.username}`}
      onClose={busy ? () => {} : onClose}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" type="submit" form="suspend-form" loading={busy}>
            Suspend
          </Button>
        </>
      }
    >
      <form id="suspend-form" onSubmit={submit} noValidate>
        <Field
          label="Duration (days)"
          type="number"
          min={1}
          max={365}
          value={days}
          onChange={(event) => {
            setDays(event.target.value);
            setError(null);
          }}
          error={error}
          hint="The reader can’t sign in until the suspension ends."
        />
      </form>
    </Modal>
  );
}