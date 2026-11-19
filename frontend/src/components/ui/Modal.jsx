import { useId, useLayoutEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from './Icon';
import styles from './Modal.module.css';

export function Modal({ open, title, onClose, children, footer, size = 'md' }) {
  const panelRef = useRef(null);
  const titleId = useId();

  useLayoutEffect(() => {
    if (!open) return undefined;
    const dialog = panelRef.current;
    const previous = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = 'hidden';
    const firstControl = dialog.querySelector('input:enabled, textarea:enabled, select:enabled, button:enabled:not([data-close])');
    firstControl?.focus();
    return () => {
      dialog.close();
      document.body.style.overflow = previousOverflow;
      previous?.focus?.({ preventScroll: true });
    };
  }, [open]);

  if (!open) return null;

  const dismissOutside = (event) => {
    if (event.target !== panelRef.current) return;
    const { left, right, top, bottom } = panelRef.current.getBoundingClientRect();
    if (event.clientX < left || event.clientX >= right || event.clientY < top || event.clientY >= bottom) onClose();
  };

  return createPortal(
    <dialog
      ref={panelRef}
      className={`${styles.panel} ${styles[size]}`}
      aria-labelledby={titleId}
      onClick={dismissOutside}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <header className={styles.header}>
        <h2 id={titleId} className={styles.title}>{title}</h2>
        <button type="button" data-close className={styles.close} onClick={onClose} aria-label="Close">
          <Icon name="x" size={18} />
        </button>
      </header>
      <div className={styles.body}>{children}</div>
      {footer && <footer className={styles.footer}>{footer}</footer>}
    </dialog>,
    document.body,
  );
}
