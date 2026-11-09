import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import styles from './Menu.module.css';

/**
 * Dropdown menu. `trigger` receives ({ open, toggle }) and returns a button.
 * items: { label, onSelect, icon?, checked?, tone?: 'danger', separator? }
 */
export function Menu({ trigger, items, align = 'start' }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    const onKey = (event) => event.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className={styles.root} ref={rootRef}>
      {trigger({ open, toggle: () => setOpen((value) => !value) })}
      {open && (
        <ul className={`${styles.menu} ${styles[align]}`} role="menu">
          {items.map((item) =>
            item.separator ? (
              <li key={item.key || 'sep'} className={styles.separator} role="separator" />
            ) : (
              <li key={item.label} role="none">
                <button
                  type="button"
                  role="menuitem"
                  className={`${styles.item} ${item.tone === 'danger' ? styles.danger : ''}`}
                  onClick={() => {
                    setOpen(false);
                    item.onSelect();
                  }}
                >
                  <span className={styles.check}>{item.checked && <Icon name="check" size={16} />}</span>
                  {item.label}
                  {item.icon && <Icon name={item.icon} size={16} className={styles.trailing} />}
                </button>
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}
