import { useCallback, useMemo, useState } from 'react';

/**
 * Client-side pagination. The backend returns full lists, so pages are cut here.
 * The page goes back to 1 whenever `resetKey` changes (new filter, new sort…).
 */
export function usePagination(items, pageSize, resetKey) {
  const [state, setState] = useState({ key: resetKey, page: 1 });
  const total = items ? items.length : 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const page = state.key === resetKey ? Math.min(state.page, pageCount) : 1;

  const setPage = useCallback((next) => setState({ key: resetKey, page: next }), [resetKey]);

  const pageItems = useMemo(
    () => (items ? items.slice((page - 1) * pageSize, page * pageSize) : []),
    [items, page, pageSize],
  );

  return { page, pageCount, pageItems, setPage, total };
}
