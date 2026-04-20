import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { CreditCard, CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { API } from '../../config/api';

/**
 * MOCK payment page — only reachable when the institution's gateway is in MOCK mode
 * (i.e., no real Comgate credentials configured yet).
 *
 * This lets the admin simulate a successful or cancelled payment end-to-end
 * before production keys are available. In production with real keys, users
 * never see this page — they go straight to Comgate's hosted page.
 */
export default function PaymentMockPage() {
  const [params] = useSearchParams();
  const vs = params.get('vs');
  const returnUrl = params.get('return');
  const trans = params.get('trans');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  // Extract institution id from return URL if present, else from localStorage
  let institutionId = null;
  if (returnUrl) {
    try {
      const u = new URL(returnUrl);
      institutionId = u.searchParams.get('institution');
    } catch {}
  }
  if (!institutionId) institutionId = localStorage.getItem('bz_last_payment_institution');

  const finish = async (outcome) => {
    setBusy(true);
    try {
      await axios.post(`${API}/event-payments/mock/complete`, {
        institution_id: institutionId,
        variable_symbol: vs,
        outcome,
      });
      setDone(outcome);
      const back = returnUrl || '/';
      const url = new URL(back, window.location.origin);
      url.searchParams.set('vs', vs || '');
      url.searchParams.set('institution', institutionId || '');
      url.searchParams.set('status', outcome === 'paid' ? 'paid' : 'cancelled');
      setTimeout(() => { window.location.href = url.toString(); }, 1200);
    } catch (e) {
      alert(e.response?.data?.detail || 'Mock simulace selhala');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-700 flex items-center justify-center px-4" data-testid="payment-mock-page">
      <Card className="max-w-lg w-full p-6 md:p-10">
        <div className="flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mb-6 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>Simulační režim platební brány — instituce zatím nenastavila produkční klíče Comgate.</span>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <CreditCard className="w-8 h-8 text-slate-700" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">Testovací platba Comgate</h1>
            <p className="text-xs text-slate-500 font-mono">VS: {vs} | Trans: {trans}</p>
          </div>
        </div>

        {!done && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">Toto je interní simulace platby. V produkci zde bude hostovaná stránka Comgate.</p>
            <Button
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => finish('paid')}
              disabled={busy}
              data-testid="mock-pay-success"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
              Simulovat úspěšnou platbu
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => finish('cancelled')}
              disabled={busy}
              data-testid="mock-pay-cancel"
            >
              <XCircle className="w-4 h-4 mr-2" />
              Simulovat zrušení platby
            </Button>
          </div>
        )}

        {done === 'paid' && (
          <div className="text-center py-6">
            <CheckCircle className="w-14 h-14 text-emerald-500 mx-auto mb-3" />
            <p className="text-slate-800 font-medium">Platba simulována. Přesměrování...</p>
          </div>
        )}
        {done === 'cancelled' && (
          <div className="text-center py-6">
            <XCircle className="w-14 h-14 text-red-500 mx-auto mb-3" />
            <p className="text-slate-800 font-medium">Platba zrušena. Přesměrování...</p>
          </div>
        )}
      </Card>
    </div>
  );
}
