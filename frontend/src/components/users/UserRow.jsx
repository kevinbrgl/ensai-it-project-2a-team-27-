import { Link } from 'react-router-dom';
import { Avatar } from '../ui/Avatar';
import styles from './UserRow.module.css';

/** A reader in a list: avatar, name and bio, with an optional action. */
export function UserRow({ user, action }) {
  return (
    <li className={styles.row}>
      <Link to={`/users/${user.id_user}`} className={styles.identity}>
        <Avatar user={user} size={40} />
        <span className={styles.text}>
          <span className={styles.name}>{user.username}</span>
          {user.bio && <span className={styles.bio}>{user.bio}</span>}
        </span>
      </Link>
      {action}
    </li>
  );
}
