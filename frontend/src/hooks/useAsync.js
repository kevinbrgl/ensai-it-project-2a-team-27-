import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

/**
 * Runs an async function whenever its dependencies change and tracks the result.
 *
 * - `loading` is true until the call for the *current* dependencies resolves.
 * - Results of outdated calls are ignored, so fast changes never show stale data.
 * - The previous data stays available while a new call runs (useful for
 *   "show more" buttons); pages show skeletons by checking `loading`.
 *
 * Dependencies must be primitives (ids, strings, numbers).
 *
 * @param {() => Promise<any>} fn
 * @param {Array<string|number|boolean|null|undefined>} deps
 * @param {{ skip?: boolean }} [options] skip: do not run (e.g. empty search)
 */
export function useAsync(fn, deps, { skip = false } = {}) {
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState({ key: undefined, data: undefined, error: null });
  const fnRef = useRef(fn);
  const key = skip ? null : JSON.stringify([...deps, nonce]);

  useLayoutEffect(() => {
    fnRef.current = fn;
  });

  useEffect(() => {
    if (key === null) return undefined;
    let active = true;
    fnRef.current().then(
      (data) => active && setState({ key, data, error: null }),
      (error) => active && setState((prev) => ({ key, data: prev.data, error })),
    );
    return () => {
      active = false;
    };
  }, [key]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const setData = useCallback((updater) => {
    setState((prev) => ({
      ...prev,
      data: typeof updater === 'function' ? updater(prev.data) : updater,
    }));
  }, []);

  return {
    data: key === null ? undefined : state.data,
    error: key !== null && state.key === key ? state.error : null,
    loading: key !== null && state.key !== key,
    reload,
    setData,
  };
}
