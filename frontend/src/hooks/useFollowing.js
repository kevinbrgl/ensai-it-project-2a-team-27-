import { useCallback, useMemo, useState } from 'react';
import * as usersApi from '../api/users';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useAsync } from './useAsync';

/** The users the current user follows, plus follow / unfollow actions. */
export function useFollowing() {
  const { user } = useAuth();
  const toast = useToast();
  const { data, error, loading, reload, setData } = useAsync(() => usersApi.getFollowing(user.id_user), [user.id_user]);
  const [pendingId, setPendingId] = useState(null);
  const following = useMemo(() => data || [], [data]);

  const follow = useCallback(
    async (target) => {
      setPendingId(target.id_user);
      try {
        await usersApi.followUser(target.id_user);
        setData((list = []) => [target, ...list]);
        toast.success(`You now follow ${target.username}.`);
      } catch (err) {
        toast.error(err.message);
      } finally {
        setPendingId(null);
      }
    },
    [setData, toast],
  );

  const unfollow = useCallback(
    async (target) => {
      setPendingId(target.id_user);
      try {
        await usersApi.unfollowUser(target.id_user);
        setData((list = []) => list.filter((u) => u.id_user !== target.id_user));
        toast.success(`You unfollowed ${target.username}.`);
      } catch (err) {
        toast.error(err.message);
      } finally {
        setPendingId(null);
      }
    },
    [setData, toast],
  );

  const isFollowing = useCallback((id) => following.some((u) => u.id_user === Number(id)), [following]);

  return { following, loading, error, reload, follow, unfollow, isFollowing, pendingId };
}
