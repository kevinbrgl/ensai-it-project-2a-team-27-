import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Keeps a piece of UI state (filter, sort, tab…) in the URL so it survives
 * reloads and the back button.
 */
export function useSearchParamState(key, defaultValue = '') {
  const [params] = useSearchParams();
  const update = useUpdateSearchParams();
  const value = params.get(key) ?? defaultValue;
  const setValue = useCallback((next) => update({ [key]: next === defaultValue ? '' : next }), [key, defaultValue, update]);
  return [value, setValue];
}

/**
 * Updates several URL parameters at once. Two separate setters called in the
 * same event would overwrite each other, so combined changes go through here.
 * Empty values remove the parameter.
 */
export function useUpdateSearchParams() {
  const [, setParams] = useSearchParams();
  return useCallback(
    (changes) => {
      setParams(
        (prev) => {
          const copy = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(changes)) {
            if (value === '' || value == null) copy.delete(key);
            else copy.set(key, value);
          }
          return copy;
        },
        { replace: true },
      );
    },
    [setParams],
  );
}
