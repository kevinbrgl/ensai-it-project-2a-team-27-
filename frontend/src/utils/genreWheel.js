// Keep each genre's hue consistent between the avatar ring and the detailed chart.
export function genreInk(color) {
  return `color-mix(in oklab, ${color} var(--wheel-mix), var(--wheel-ink))`;
}
