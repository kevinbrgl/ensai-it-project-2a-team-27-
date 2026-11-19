import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import readingRoom from '../assets/reading-room.webp';
import { Wordmark } from '../components/layout/Wordmark';
import { Icon } from '../components/ui/Icon';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { collectErrors, validateEmail, validatePassword, validateUsername } from '../utils/validation';
import styles from './AuthPage.module.css';

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

  const [showPassword, setShowPassword] = useState(false);
  const from = location.state?.from;
  const destination = from ? { pathname: from.pathname, search: from.search, hash: from.hash } : '/';
  if (status === 'authenticated') return <Navigate to={destination} replace />;

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
      navigate(destination, { replace: true });
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
      <header className={styles.masthead}>
        <div className={styles.bar}>
          <Wordmark />
          <div className={styles.accountSwitch}>
            <span>{isLogin ? 'New here?' : 'Already a reader?'}</span>
            <Link to={isLogin ? '/register' : '/login'} state={location.state}>
              {isLogin ? 'Create account' : 'Sign in'} <Icon name="arrowRight" size={16} />
            </Link>
          </div>
        </div>
      </header>
      <main className={styles.spread}>
        <section className={styles.plate} aria-label="About Ex-Libris">
          <img className={styles.photograph} src={readingRoom} fetchPriority="high" alt="" />
          <span className={styles.ribbon} aria-hidden="true"><Icon name="book" size={20} /></span>
          <div className={styles.caption}>
            <h2>Your reading<br /><em>journal.</em></h2>
            <p>Track your books, keep your reviews, and discover what to read next.</p>
          </div>
        </section>

        <section className={styles.formSide}>
          <form className={styles.form} onSubmit={submit} noValidate>
            <div className={styles.formIntro}>
              <h1>{isLogin ? 'Welcome back.' : 'Start your journal.'}</h1>
              <p>{isLogin ? 'Sign in to your Ex-Libris account.' : 'Create a free Ex-Libris account to start your reading log.'}</p>
            </div>
          {formError && (
            <p className={styles.formError} role="alert">
              {formError}
            </p>
          )}

          <Field label="Username" autoComplete="username" value={values.username} onChange={update('username')} error={errors.username} placeholder="Your username" maxLength={30} />
          {!isLogin && (
            <Field label="Email" type="email" autoComplete="email" value={values.email} onChange={update('email')} error={errors.email} />
          )}
          <div className={styles.password}>
          <Field
            label="Password"
            type={showPassword ? 'text' : 'password'}
            placeholder="Your password"
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            value={values.password}
            onChange={update('password')}
            error={errors.password}
            hint={isLogin ? undefined : '8 to 72 characters.'}
            maxLength={72}
          />
          <button type="button" className={styles.reveal} aria-pressed={showPassword}
            aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>
            {showPassword ? 'Hide' : 'Show'}
          </button>
          </div>
          {!isLogin && (
            <Field label="Confirm password" type="password" autoComplete="new-password" value={values.confirm} onChange={update('confirm')} error={errors.confirm} maxLength={72} />
          )}

          <Button type="submit" variant="primary" loading={busy} iconRight="arrowRight" className={styles.submit}>
            {isLogin ? 'Sign in' : 'Create account'}
          </Button>
        </form>
      </section>
      </main>
    </div>
  );
}
