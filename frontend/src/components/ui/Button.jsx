import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from './Icon';
import { Spinner } from './Spinner';
import styles from './Button.module.css';

/**
 * variant: primary (accent, one per view) | secondary | ghost | danger
 * size: md | sm
 * Pass `to` to render a router link styled as a button.
 */
export const Button = forwardRef(function Button(
  { variant = 'secondary', size = 'md', icon, iconRight, loading = false, to, className = '', children, ...props },
  ref,
) {
  const classes = [styles.button, styles[variant], styles[size], !children && styles.iconOnly, className]
    .filter(Boolean)
    .join(' ');
  const iconSize = size === 'sm' ? 16 : 18;
  const content = (
    <>
      {loading ? <Spinner size={iconSize} /> : icon && <Icon name={icon} size={iconSize} />}
      {children}
      {iconRight && <Icon name={iconRight} size={iconSize} />}
    </>
  );

  if (to) {
    return (
      <Link ref={ref} to={to} className={classes} {...props}>
        {content}
      </Link>
    );
  }
  return (
    <button ref={ref} type="button" className={classes} disabled={loading || props.disabled} {...props}>
      {content}
    </button>
  );
});
