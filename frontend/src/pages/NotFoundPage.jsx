import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/States';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

export function NotFoundPage() {
  useDocumentTitle('Page not found');
  return (
    <EmptyState icon="compass" title="This page doesn’t exist" action={<Button variant="primary" to="/">Back to home</Button>}>
      The link may be broken or the page may have moved.
    </EmptyState>
  );
}
