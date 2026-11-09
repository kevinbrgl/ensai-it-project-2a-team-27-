import { useEffect } from 'react';

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · Ex-Libris` : 'Ex-Libris';
  }, [title]);
}
