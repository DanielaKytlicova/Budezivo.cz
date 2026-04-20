import React, { useContext, useState } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, UserCog, LogOut, Loader2 } from 'lucide-react';
import { AuthContext } from '../../context/AuthContext';

/**
 * Sticky top banner shown on every page when the session is acting as another
 * user (superadmin impersonation). Clearly visible, persistent, and offers a
 * one-click "stop" action that returns to the original superadmin identity.
 */
export const ImpersonationBanner = () => {
  const { user, stopImpersonation } = useContext(AuthContext);
  const [busy, setBusy] = useState(false);

  const active = user?.impersonation?.active;
  if (!active) return null;

  const handleStop = async () => {
    setBusy(true);
    try {
      await stopImpersonation();
      toast.success('Impersonace ukončena');
      // Hard reload to ensure every cached component re-reads auth/me
      setTimeout(() => window.location.assign('/admin/superadmin'), 400);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Nepodařilo se ukončit impersonaci');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="sticky top-0 z-50 w-full bg-amber-500 text-amber-950 border-b-2 border-amber-700 shadow-md"
      role="alert"
      aria-live="polite"
      data-testid="impersonation-banner"
    >
      <div className="max-w-7xl mx-auto px-4 py-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3 text-sm font-medium">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            <strong>IMPERSONACE</strong> — vystupujete jako{' '}
            <span className="font-mono bg-amber-600/30 px-1.5 py-0.5 rounded">
              <UserCog className="w-3 h-3 inline -mt-0.5" /> {user.email}
            </span>{' '}
            ({user.role}). Skutečný účet:{' '}
            <span className="font-semibold">{user.impersonation.original_email}</span>
          </span>
        </div>
        <button
          type="button"
          onClick={handleStop}
          disabled={busy}
          className="inline-flex items-center gap-1 bg-amber-900 hover:bg-amber-950 text-white text-xs font-semibold px-3 py-1.5 rounded disabled:opacity-60"
          data-testid="stop-impersonation-btn"
        >
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <LogOut className="w-3 h-3" />}
          Ukončit impersonaci
        </button>
      </div>
    </div>
  );
};

export default ImpersonationBanner;
