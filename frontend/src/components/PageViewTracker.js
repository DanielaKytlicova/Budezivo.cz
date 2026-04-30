import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { API } from '../config/api';

/**
 * Reports a pageview to the backend on every SPA route change.
 *
 * Lightweight, fire-and-forget — failures are silent so an analytics outage
 * never breaks the user-facing flow. Skips API and static-asset paths the
 * router will never actually navigate to but defensively guards anyway.
 */
const SKIP_PREFIXES = ['/api/', '/static/', '/assets/'];

export default function PageViewTracker() {
  const location = useLocation();

  useEffect(() => {
    const path = location.pathname + (location.search || '');
    if (!path.startsWith('/') || SKIP_PREFIXES.some(p => path.startsWith(p))) return;

    // Strip ?id=, ?refId=, ?status= and similar query params from the recorded
    // path — they pollute the "Top paths" list with one-off variants. Keep
    // the path itself (incl. dynamic IDs) since route patterns matter.
    const cleanPath = location.pathname || '/';
    const referrer = document.referrer || null;

    // Defer slightly so the route-render isn't blocked by analytics network.
    const t = setTimeout(() => {
      axios.post(`${API}/analytics/pageview`, { path: cleanPath, referrer })
        .catch(() => { /* silent */ });
    }, 150);
    return () => clearTimeout(t);
  }, [location.pathname, location.search]);

  return null;
}
