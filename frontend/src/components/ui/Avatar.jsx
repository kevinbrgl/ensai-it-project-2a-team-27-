import { useState } from 'react';
import styles from './Avatar.module.css';

// Deterministic, muted background per user so avatars are recognisable.
const TONES = ['#e7d8c9', '#d9e2d3', '#dcd9ea', '#ecd5d1', '#d3e0e6', '#eadfc2'];

export function Avatar({ user, size = 36 }) {
  const [broken, setBroken] = useState(false);
  const name = user?.username || '?';
  const tone = TONES[(user?.id_user || 0) % TONES.length];
  const style = { width: size, height: size, fontSize: size * 0.42, background: tone };

  if (user?.profile_picture && !broken) {
    return (
      <img
        src={user.profile_picture}
        alt=""
        className={styles.avatar}
        style={style}
        onError={() => setBroken(true)}
      />
    );
  }
  return (
    <span className={styles.avatar} style={style} aria-hidden="true">
      {name.charAt(0).toUpperCase()}
    </span>
  );
}
