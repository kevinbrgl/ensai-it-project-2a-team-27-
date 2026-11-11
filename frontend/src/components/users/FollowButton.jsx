import { Button } from '../ui/Button';

export function FollowButton({ user, social, size = 'sm' }) {
  const following = social.isFollowing(user.id_user);
  const busy = social.pendingId === user.id_user;
  return following ? (
    <Button size={size} icon="userCheck" loading={busy} onClick={() => social.unfollow(user)} aria-label={`Unfollow ${user.username}`}>
      Following
    </Button>
  ) : (
    <Button size={size} variant="primary" icon="userPlus" loading={busy} onClick={() => social.follow(user)}>
      Follow
    </Button>
  );
}
