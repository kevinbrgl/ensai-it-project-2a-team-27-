import { yearOf } from './format';

export const BOOK_SORTS = [
  { value: 'title', label: 'Title A–Z' },
  { value: 'author', label: 'Author A–Z' },
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
];

const collator = new Intl.Collator('en', { sensitivity: 'base' });

/** Returns a sorted copy of a book list (Book or LibraryBookDetails). */
export function sortBooks(books, sort) {
  const list = [...books];
  switch (sort) {
    case 'author':
      return list.sort((a, b) => collator.compare(a.author || '~', b.author || '~'));
    case 'newest':
      return list.sort((a, b) => (yearOf(b.publish_date) || 0) - (yearOf(a.publish_date) || 0));
    case 'oldest':
      return list.sort((a, b) => (yearOf(a.publish_date) || 9999) - (yearOf(b.publish_date) || 9999));
    default:
      return list.sort((a, b) => collator.compare(a.title, b.title));
  }
}

/** Most frequent categories of a list of books, most common first. */
export function topCategories(books, max = 12) {
  const counts = new Map();
  for (const book of books) {
    const category = book.category && book.category.trim();
    if (category) counts.set(category, (counts.get(category) || 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || collator.compare(a[0], b[0]))
    .slice(0, max)
    .map(([name, count]) => ({ name, count }));
}
