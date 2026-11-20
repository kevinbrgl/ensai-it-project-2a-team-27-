import { genreInk } from '../../utils/genreWheel';
import { Avatar } from '../ui/Avatar';
import styles from './GenreWheelAvatar.module.css';

export function GenreWheelAvatar({ user, wheel, size, descriptionId }) {
  let ring;
  let description;
  if (wheel?.is_empty) {
    ring = genreInk(wheel.empty_color);
    description = 'No finished books with a genre yet';
  } else if (wheel?.segments.length) {
    if (wheel.segments.length === 1) {
      ring = genreInk(wheel.segments[0].color);
    } else {
      const stops = [];
      let start = 0;
      for (const { color, percentage } of wheel.segments) {
        const end = start + percentage;
        const divider = `calc(${end}% - 2.5deg)`;
        stops.push(`${genreInk(color)} ${start}% ${divider}`, `transparent ${divider} ${end}%`);
        start = end;
      }
      ring = `conic-gradient(${stops.join(', ')})`;
    }
    const shares = wheel.segments.map(({ genre, percentage }) => `${genre} ${percentage}%`);
    description = `Reading genres: ${shares.join(', ')}`;
  }

  return (
    <span className={styles.frame} style={{ width: size, height: size, '--genre-ring': ring }}
      id={descriptionId} role={description ? 'img' : undefined} aria-label={description} title={description}>
      <Avatar key={user.profile_picture || user.id_user} user={user} size={Math.round(size * 0.72)} />
    </span>
  );
}
