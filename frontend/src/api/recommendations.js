import { request } from './client';

/**
 * GET /recommendations?genre=&sort=&limit= → { book, score, reason }[]
 * sort: 'rating' | 'new' | 'title'
 */
export function getRecommendations({ genre, sort = 'rating', limit = 12 } = {}) {
  return request('/recommendations', { query: { genre, sort, limit } });
}
