export function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-');
}

export function unslugify(slug, workTypes) {
  return workTypes.find(wt => slugify(wt.name) === slug);
}

export function formatDate(d) {
  if (!d) return null;
  return new Date(d).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

export function formatDateRange(start, end) {
  const s = formatDate(start);
  const e = end ? formatDate(end) : 'Present';
  if (!s) return null;
  return `${s} — ${e}`;
}
