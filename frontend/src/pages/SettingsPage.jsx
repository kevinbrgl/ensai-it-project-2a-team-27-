import { useState } from 'react';
import { changePassword, updateMe } from '../api/users';
import { Avatar } from '../components/ui/Avatar';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { PageHeader } from '../components/ui/PageHeader';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { collectErrors, validateEmail, validatePassword, validateUrl, validateUsername } from '../utils/validation';
import page from './Page.module.css';
import styles from './SettingsPage.module.css';

export function SettingsPage() {
  useDocumentTitle('Settings');
  const { user } = useAuth();

  return (
    <>
      <PageHeader title="Account settings" />
      <div className={styles.layout}>
        <ProfileForm key={user.id_user} />
        <PasswordForm />
      </div>
    </>
  );
}

function ProfileForm() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const initial = {
    username: user.username,
    email: user.email,
    bio: user.bio || '',
    profile_picture: user.profile_picture || '',
  };
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  // PATCH /users/me only receives the fields that actually changed.
  const changes = Object.fromEntries(
    Object.entries(values)
      .map(([key, value]) => [key, key === 'username' || key === 'email' ? value.trim() : value])
      .filter(([key, value]) => value !== initial[key]),
  );
  const dirty = Object.keys(changes).length > 0;

  const update = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const submit = async (event) => {
    event.preventDefault();
    const found = collectErrors({
      username: validateUsername(values.username),
      email: validateEmail(values.email),
      profile_picture: validateUrl(values.profile_picture),
    });
    setErrors(found);
    if (Object.keys(found).length || !dirty) return;

    setBusy(true);
    try {
      const updated = await updateMe(changes);
      setUser(updated);
      toast.success('Profile saved.');
    } catch (err) {
      if (err.status === 409) {
        setErrors(err.message.startsWith('Email') ? { email: 'This email is already used.' } : { username: 'This username is taken.' });
      } else if (err.status === 422) {
        setErrors(err.fieldErrors);
      } else {
        toast.error(err.message);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className={`${page.card} ${styles.form}`} onSubmit={submit} noValidate>
      <div className={styles.formHeader}>
        <Avatar user={{ ...user, profile_picture: validateUrl(values.profile_picture) ? null : values.profile_picture }} size={56} />
        <div>
          <h2 className={styles.title}>Profile</h2>
          <p className={styles.text}>Other readers see your username, picture and bio.</p>
        </div>
      </div>
      <div className={styles.row}>
        <Field label="Username" value={values.username} onChange={update('username')} error={errors.username} maxLength={30} autoComplete="username" />
        <Field label="Email" type="email" value={values.email} onChange={update('email')} error={errors.email} autoComplete="email" />
      </div>
      <Field
        as="textarea"
        label="Bio"
        value={values.bio}
        onChange={update('bio')}
        placeholder="A few words about what you like to read"
        rows={3}
      />
      <Field
        label="Profile picture"
        type="url"
        value={values.profile_picture}
        onChange={update('profile_picture')}
        error={errors.profile_picture}
        placeholder="https://…"
        hint="Link to an image (max 255 characters)."
        maxLength={255}
      />
      <div className={styles.actions}>
        {dirty && (
          <Button variant="ghost" onClick={() => setValues(initial)} disabled={busy}>
            Discard changes
          </Button>
        )}
        <Button type="submit" variant="primary" loading={busy} disabled={!dirty}>
          Save profile
        </Button>
      </div>
    </form>
  );
}

function PasswordForm() {
  const toast = useToast();
  const empty = { current: '', next: '', confirm: '' };
  const [values, setValues] = useState(empty);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const update = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const submit = async (event) => {
    event.preventDefault();
    const found = collectErrors({
      current: values.current ? null : 'Enter your current password.',
      next: validatePassword(values.next) || (values.next === values.current ? 'Choose a different password.' : null),
      confirm: values.confirm === values.next ? null : 'The passwords don’t match.',
    });
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    try {
      await changePassword(values.current, values.next);
      setValues(empty);
      toast.success('Password changed.');
    } catch (err) {
      if (err.status === 403) setErrors({ current: 'This password is incorrect.' });
      else if (err.status === 400) setErrors({ next: err.message });
      else toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className={`${page.card} ${styles.form}`} onSubmit={submit} noValidate>
      <div>
        <h2 className={styles.title}>Password</h2>
        <p className={styles.text}>Use 8 to 72 characters.</p>
      </div>
      <Field label="Current password" type="password" value={values.current} onChange={update('current')} error={errors.current} autoComplete="current-password" />
      <div className={styles.row}>
        <Field label="New password" type="password" value={values.next} onChange={update('next')} error={errors.next} autoComplete="new-password" maxLength={72} />
        <Field label="Confirm new password" type="password" value={values.confirm} onChange={update('confirm')} error={errors.confirm} autoComplete="new-password" maxLength={72} />
      </div>
      <div className={styles.actions}>
        <Button type="submit" variant="primary" loading={busy}>
          Change password
        </Button>
      </div>
    </form>
  );
}
