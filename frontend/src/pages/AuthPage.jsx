import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { BookCover } from '../components/books/BookCover';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { collectErrors, validateEmail, validatePassword, validateUsername } from '../utils/validation';
import styles from './AuthPage.module.css';

// Real Open Library covers, fetched by ISBN, for the welcome panel.
const SHOWCASE = [
  { isbn: '9780141439518', title: 'Pride and Prejudice', author: 'Jane Austen' },
  { isbn: '9780451524935', title: 'Nineteen Eighty-Four', author: 'George Orwell' },
  { isbn: '9780061120084', title: 'To Kill a Mockingbird', author: 'Harper Lee' },
  { isbn: '9780743273565', title: 'The Great Gatsby', author: 'F. Scott Fitzgerald' },
  { isbn: '9780140449136', title: 'Crime and Punishment', author: 'Fyodor Dostoevsky' },
];

const EMPTY = { username: '', email: '', password: '', confirm: '' };

export function AuthPage({ mode }) {
  const isLogin = mode === 'login';
  useDocumentTitle(isLogin ? 'Sign in' : 'Create an account');
  const { status, login, register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  if (status === 'authenticated') return <Navigate to={location.state?.from?.pathname || '/'} replace />;

  const update = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
    setFormError('');
  };

  const validate = () =>
    isLogin
      ? collectErrors({
          username: values.username.trim() ? null : 'Enter your username.',
          password: values.password ? null : 'Enter your password.',
        })
      : collectErrors({
          username: validateUsername(values.username),
          email: validateEmail(values.email),
          password: validatePassword(values.password),
          confirm: values.confirm === values.password ? null : 'The passwords don’t match.',
        });

  const submit = async (event) => {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) return;

    setBusy(true);
    try {
      if (isLogin) {
        const me = await login(values.username.trim(), values.password);
        toast.success(`Welcome back, ${me.username}.`);
      } else {
        const me = await register({
          username: values.username.trim(),
          email: values.email.trim(),
          password: values.password,
        });
        toast.success(`Welcome to Ex-Libris, ${me.username}.`);
      }
      navigate(location.state?.from?.pathname || '/', { replace: true });
    } catch (error) {
      if (error.status === 409) {
        setErrors(error.message.startsWith('Email') ? { email: 'This email is already registered.' } : { username: 'This username is taken.' });
      } else if (error.status === 422) {
        setErrors(error.fieldErrors);
      } else {
        setFormError(error.message);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <section className={styles.showcase} aria-hidden="true">
        <span className={styles.brand}>Ex-Libris</span>
        <div className={styles.stack}>
          {SHOWCASE.map((book, i) => (
            <div key={book.isbn} className={styles.stackItem} style={{ '--i': i - 2 }}>
              <BookCover book={book} src={`https://covers.openlibrary.org/b/isbn/${book.isbn}-L.jpg?default=false`} />
            </div>
          ))}
        </div>
        <div className={styles.pitch}>
          <h2>Every book you read, in one place.</h2>
          <p>Track what you’re reading, rate what you finished, and find your next book through readers you trust.</p>
        </div>
      </section>

      <section className={styles.formSide}>
        <form className={styles.form} onSubmit={submit} noValidate>
          <span className={styles.mobileBrand}>Ex-Libris</span>
          <h1>{isLogin ? 'Sign in to your library' : 'Start your reading log'}</h1>
          <p className={styles.lead}>
            {isLogin ? 'New here? ' : 'Already have an account? '}
            <Link to={isLogin ? '/register' : '/login'} state={location.state} className={styles.switch}>
              {isLogin ? 'Create an account' : 'Sign in'}
            </Link>
          </p>

          {formError && (
            <p className={styles.formError} role="alert">
              {formError}
            </p>
          )}

          <Field label="Username" autoComplete="username" value={values.username} onChange={update('username')} error={errors.username} maxLength={30} autoFocus />
          {!isLogin && (
            <Field label="Email" type="email" autoComplete="email" value={values.email} onChange={update('email')} error={errors.email} />
          )}
          <Field
            label="Password"
            type="password"
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            value={values.password}
            onChange={update('password')}
            error={errors.password}
            hint={isLogin ? undefined : '8 to 72 characters.'}
            maxLength={72}
          />
          {!isLogin && (
            <Field label="Confirm password" type="password" autoComplete="new-password" value={values.confirm} onChange={update('confirm')} error={errors.confirm} maxLength={72} />
          )}

          <Button type="submit" variant="primary" loading={busy} className={styles.submit}>
            {isLogin ? 'Sign in' : 'Create account'}
          </Button>
        </form>
      </section>
    </div>
  );
}
