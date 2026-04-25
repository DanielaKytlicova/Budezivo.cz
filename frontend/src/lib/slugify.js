// Lightweight slugify for SEO URLs (Czech-aware).
// "Praha" → "praha", "Výtvarná výchova" → "vytvarna-vychova"
export function slugify(input) {
  if (!input) return '';
  return String(input)
    .normalize('NFD')                 // decompose diacritics
    .replace(/[\u0300-\u036f]/g, '')  // strip combining marks
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')      // non-alnum → dash
    .replace(/^-+|-+$/g, '');         // trim dashes
}

// Hard-coded age slugs (must match backend AGE_SLUG_MAP keys)
export const AGE_SLUGS = ['ms', 'zs1', 'zs2', 'ss'];

export const AGE_SLUG_LABELS = {
  ms:  'mateřské školy',
  zs1: '1. stupeň ZŠ',
  zs2: '2. stupeň ZŠ',
  ss:  'střední školy',
};

// UUID v4 format detection (used to differentiate program-id from slug)
export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
