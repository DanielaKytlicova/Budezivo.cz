/**
 * Shared helpers for calendar integrations (deep-links + ICS feed tokens).
 * Kept framework-agnostic so both LecturerAvailabilityPage and BookingsPage
 * can reuse the exact same logic (single source of truth).
 */
import axios from 'axios';
import { API } from '../../config/api';
import { toast } from 'sonner';

// Provider display metadata — unified so Google & Outlook cards look identical.
export const PROVIDERS = {
  google: {
    key: 'google',
    label: 'Google kalendář',
    connectLabel: 'Připojit Google',
    accent: 'text-[#4285F4]',
    dot: 'bg-[#4285F4]',
    ring: 'bg-blue-50',
  },
  outlook: {
    key: 'outlook',
    label: 'Outlook kalendář',
    connectLabel: 'Připojit Outlook',
    accent: 'text-[#0F6CBD]',
    dot: 'bg-[#0F6CBD]',
    ring: 'bg-sky-50',
  },
};

// Parse a reservation date (YYYY-MM-DD) + time_block ("10:00-11:00" | "10:00")
// into JS Date start/end. Falls back to a 60-minute slot when no end is given.
export function reservationDateRange(booking, durationMinutes) {
  if (!booking?.date) return null;
  const tb = booking.time_block || '';
  const m = String(tb).match(/^(\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?$/);
  const [y, mo, d] = booking.date.split('-').map(Number);
  let sh = 9, sm = 0, eh = 10, em = 0;
  if (m) {
    sh = parseInt(m[1], 10); sm = parseInt(m[2], 10);
    if (m[3]) { eh = parseInt(m[3], 10); em = parseInt(m[4], 10); }
    else {
      const dur = durationMinutes || 60;
      const endMin = sh * 60 + sm + dur;
      eh = Math.floor(endMin / 60); em = endMin % 60;
    }
  }
  const start = new Date(y, (mo || 1) - 1, d, sh, sm, 0);
  const end = new Date(y, (mo || 1) - 1, d, eh, em, 0);
  return { start, end };
}

// Format a Date as local floating time YYYYMMDDTHHMMSS (Google deep-link style).
function fmtFloating(dt) {
  const p = (n) => String(n).padStart(2, '0');
  return `${dt.getFullYear()}${p(dt.getMonth() + 1)}${p(dt.getDate())}T${p(dt.getHours())}${p(dt.getMinutes())}00`;
}

// ISO local (no Z) for Outlook compose deep-links.
function fmtIsoLocal(dt) {
  const p = (n) => String(n).padStart(2, '0');
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}T${p(dt.getHours())}:${p(dt.getMinutes())}:00`;
}

// Build add-to-calendar deep-links for a reservation.
export function buildCalendarLinks(booking, { durationMinutes } = {}) {
  const range = reservationDateRange(booking, durationMinutes);
  if (!range) return null;
  const title = `${booking.program_name || 'Rezervace'}${booking.school_name ? ' – ' + booking.school_name : ''}`;
  const detailsLines = [
    booking.program_name && `Program: ${booking.program_name}`,
    booking.school_name && `Škola: ${booking.school_name}`,
    booking.num_students && `Počet žáků: ${booking.num_students}`,
    booking.contact_name && `Kontakt: ${booking.contact_name}`,
  ].filter(Boolean);
  const details = detailsLines.join('\n');
  const loc = booking.institution_name || '';

  const google = `https://calendar.google.com/calendar/render?action=TEMPLATE`
    + `&text=${encodeURIComponent(title)}`
    + `&dates=${fmtFloating(range.start)}/${fmtFloating(range.end)}`
    + `&details=${encodeURIComponent(details)}`
    + `&location=${encodeURIComponent(loc)}`;

  const outlookParams = `subject=${encodeURIComponent(title)}`
    + `&startdt=${encodeURIComponent(fmtIsoLocal(range.start))}`
    + `&enddt=${encodeURIComponent(fmtIsoLocal(range.end))}`
    + `&body=${encodeURIComponent(details)}`
    + `&location=${encodeURIComponent(loc)}`
    + `&path=/calendar/action/compose&rru=addevent`;
  const outlookLive = `https://outlook.live.com/calendar/0/deeplink/compose?${outlookParams}`;
  const outlookOffice = `https://outlook.office.com/calendar/0/deeplink/compose?${outlookParams}`;

  return { google, outlookLive, outlookOffice };
}

// ── ICS subscription feed tokens ────────────────────────────────────

const authHeaders = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

export async function listFeedTokens(token) {
  const res = await axios.get(`${API}/calendar/feed-tokens`, authHeaders(token));
  return Array.isArray(res.data) ? res.data : [];
}

// Create (regenerate) a feed token. Returns { id, url, scope, feed_type }.
export async function createFeedToken(feedType, entityId, token) {
  const res = await axios.post(
    `${API}/calendar/feed-tokens`,
    { feed_type: feedType, entity_id: entityId },
    authHeaders(token),
  );
  return res.data;
}

export async function revokeFeedToken(tokenId, token) {
  await axios.post(`${API}/calendar/feed-tokens/${tokenId}/revoke`, {}, authHeaders(token));
}

// One-time signed .ics download for a single reservation.
export async function downloadReservationIcs(reservationId, token) {
  try {
    const tokenRes = await axios.get(
      `${API}/calendar/public-feed-token/reservation/${reservationId}`,
      authHeaders(token),
    );
    const signed = tokenRes.data.token;
    window.open(`${API}/calendar/reservation/${reservationId}.ics?token=${signed}`, '_blank');
  } catch {
    toast.error('Nepodařilo se vygenerovat .ics soubor');
  }
}

export function copyToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(
      () => toast.success('Odkaz zkopírován do schránky'),
      () => toast.error('Kopírování se nezdařilo'),
    );
  } else {
    toast.error('Kopírování není v tomto prohlížeči podporováno');
  }
}
