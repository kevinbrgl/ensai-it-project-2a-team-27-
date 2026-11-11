import { useEffect, useMemo, useState } from 'react';
import { listBooks } from '../api/books';
import { BookGrid, BookGridSkeleton } from '../components/books/BookGrid';
import { Button } from '../components/ui/Button';
import { ChipGroup } from '../components/ui/ChipGroup';
import { Field } from '../components/ui/Field';
import { PageHeader } from '../components/ui/PageHeader';
import { Pagination } from '../components/ui/Pagination';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAsync } from '../hooks/useAsync';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { usePagination } from '../hooks/usePagination';
import { useSearchParamState, useUpdateSearchParams } from '../hooks/useSearchParamState';
import { BOOK_SORTS, sortBooks, topCategories } from '../utils/books';
import { plural } from '../utils/format';
import page from './Page.module.css';

const PAGE_SIZE = 24;

export function CatalogPage() {
  useDocumentTitle('Catalog');
  const [category, setCategory] = useSearchParamState('genre');
  const [author, setAuthor] = useSearchParamState('author');
  const [sort, setSort] = useSearchParamState('sort', 'title');
  const updateParams = useUpdateSearchParams();
  const [authorDraft, setAuthorDraft] = useState(author);
  const debouncedAuthor = useDebouncedValue(authorDraft.trim());

  useEffect(() => {
    if (debouncedAuthor !== author) setAuthor(debouncedAuthor);
  }, [debouncedAuthor, author, setAuthor]);

  // Genre chips come from the whole catalog; the list itself is filtered by the API.
  const all = useAsync(() => listBooks(), []);
  const filtered = useAsync(() => listBooks({ category, author }), [category, author], {
    skip: !category && !author,
  });
  const source = category || author ? filtered : all;

  const genres = useMemo(() => topCategories(all.data || [], 14), [all.data]);
  const sorted = useMemo(() => sortBooks(source.data || [], sort), [source.data, sort]);
  const pagination = usePagination(sorted, PAGE_SIZE, `${category}|${author}|${sort}`);
  const hasFilters = Boolean(category || author);

  const clearFilters = () => {
    updateParams({ genre: '', author: '' });
    setAuthorDraft('');
  };

  return (
    <>
      <PageHeader
        title="Catalog"
        description="Every book saved by Ex-Libris readers. Searching in Discover adds new titles here."
      />

      <div className={page.filters}>
        <ChipGroup label="Genre" options={genres} value={category} onChange={setCategory} allLabel="All genres" />
        <div className={page.toolbar}>
          <div className={page.toolbarGroup}>
            <Field
              type="search"
              placeholder="Filter by author"
              aria-label="Filter by author"
              value={authorDraft}
              onChange={(e) => setAuthorDraft(e.target.value)}
            />
            {hasFilters && (
              <Button variant="ghost" icon="x" onClick={clearFilters}>
                Clear filters
              </Button>
            )}
          </div>
          <div className={page.toolbarGroup}>
            {source.data && <span className={`${page.resultCount} tabular`}>{plural(sorted.length, 'book')}</span>}
            <Field as="select" aria-label="Sort books" value={sort} onChange={(e) => setSort(e.target.value)} className={page.sortSelect}>
              {BOOK_SORTS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Field>
          </div>
        </div>
      </div>

      {source.error && <ErrorState error={source.error} onRetry={source.reload} />}
      {!source.error && source.loading && <BookGridSkeleton count={12} />}
      {!source.loading && source.data && sorted.length === 0 && (
        <EmptyState
          icon="grid"
          title={hasFilters ? 'No books match these filters' : 'The catalog is empty'}
          action={hasFilters ? <Button onClick={clearFilters}>Clear filters</Button> : <Button variant="primary" to="/discover">Search for books</Button>}
        >
          {hasFilters ? 'Try another genre or a shorter author name.' : 'Books appear here as soon as someone searches for them.'}
        </EmptyState>
      )}
      {!source.loading && sorted.length > 0 && (
        <>
          <BookGrid books={pagination.pageItems} />
          <Pagination {...pagination} pageSize={PAGE_SIZE} onChange={pagination.setPage} />
        </>
      )}
    </>
  );
}
