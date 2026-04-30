import React, { useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '../context/AuthContext';
import { AlertCircle, X } from 'lucide-react';
import { API } from '../config/api';

/**
 * Superadmin-only top alert banner.
 *
 * Renders an orange attention band when at least one institution is waiting
 * for a paid-plan upgrade confirmation (``pending_billing_orders > 0``).
 * Hidden for everyone except the platform owner (identified by e-mail to
 * match the existing Superadmin nav-visibility rule).
 *
 * We poll the overview endpoint once per minute so the badge count refreshes
 * without the superadmin needing to reload the SPA. The endpoint is
 * lightweight (a handful of COUNT queries) so polling is cheap.
 *
 * Click on the banner → navigates to the Superadmin hub where the orders
 * table lives. The "×" dismisses the banner for the current tab session.
 */
const POLL_INTERVAL_MS = 60_000;
const SUPERADMIN_EMAILS = ['demo@budezivo.cz', 'admin@budezivo.cz'];

export default function SuperadminAlertBanner() {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();
  const [dismissed, setDismissed] = useState(false);
  const [pending, setPending] = useState(0);

  const isSuperadmin = !!user && (
    SUPERADMIN_EMAILS.includes(user.email) || user.role === 'superadmin'
  );

  // Per user request: banner is only visible on the Superadmin page itself.
  const onSuperadminPage = location.pathname.startsWith('/admin/superadmin');

  const fetchCount = useCallback(async () => {
    if (!isSuperadmin) return;
    try {
      const res = await axios.get(`${API}/superadmin/overview`);
      setPending(res.data?.pending_billing_orders || 0);
    } catch {
      // Silent fail — an outage of this endpoint shouldn't break the shell.
    }
  }, [isSuperadmin]);

  useEffect(() => {
    if (!isSuperadmin || !onSuperadminPage) return undefined;
    fetchCount();
    const id = setInterval(fetchCount, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isSuperadmin, onSuperadminPage, fetchCount]);

  if (!isSuperadmin || !onSuperadminPage || pending === 0 || dismissed) return null;

  const label = pending === 1
    ? '1 čekající žádost o vyšší tarif'
    : `${pending} čekajících žádostí o vyšší tarif`;

  return (
    <div
      className="mb-4 rounded-lg bg-amber-100 border border-amber-300 text-amber-900 shadow-sm"
      data-testid="superadmin-pending-banner"
    >
      <div className="flex items-center gap-3 px-4 py-2">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <button
          type="button"
          onClick={() => navigate('/admin/superadmin?tab=orders')}
          className="text-sm font-semibold hover:underline flex-1 text-left"
          data-testid="superadmin-pending-open"
        >
          {label} — klikněte pro zobrazení a potvrzení
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="p-1 rounded hover:bg-amber-200 transition-colors flex-shrink-0"
          aria-label="Zavřít oznámení"
          data-testid="superadmin-pending-dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
