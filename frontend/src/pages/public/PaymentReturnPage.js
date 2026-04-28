import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle, XCircle, Loader2, ArrowLeft } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { API } from '../../config/api';

/**
 * Payment return page.
 * Called by the gateway (or our mock) after user finishes payment attempt.
 *
 * Query params used (any subset):
 *   - refId=<application_id>   (Comgate-portal URLs substitute ${refId})
 *   - id=<comgate_trans_id>    (Comgate-portal URLs substitute ${id})
 *   - vs=<variable_symbol>
 *   - institution=<id>         (only needed for vs fallback)
 *   - application=<id>
 *   - status=paid|cancelled|pending  (optimistic hint from gateway)
 *
 * Lookup priority:
 *   1. /api/event-payments/by-ref/{refId}  (preferred — works with portal URLs)
 *   2. /api/event-payments/by-vs/{institution}/{vs}  (fallback)
 */
export default function PaymentReturnPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const refId = params.get('refId') || params.get('application');
  const vs = params.get('vs');
  const institutionId = params.get('institution') || localStorage.getItem('bz_last_payment_institution');
  const hint = params.get('status');

  const [status, setStatus] = useState('polling'); // polling | paid | failed | unknown
  const [detail, setDetail] = useState(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!refId && (!vs || !institutionId)) {
      setStatus('unknown');
      return;
    }
    let cancelled = false;
    let tries = 0;
    const poll = async () => {
      tries += 1;
      setAttempts(tries);
      try {
        const url = refId
          ? `${API}/event-payments/by-ref/${refId}`
          : `${API}/event-payments/by-vs/${institutionId}/${vs}`;
        const res = await axios.get(url);
        if (cancelled) return;
        setDetail(res.data);
        if (res.data.payment_status === 'paid') setStatus('paid');
        else if (res.data.payment_status === 'failed') setStatus('failed');
        else if (tries >= 15) setStatus(hint === 'cancelled' ? 'failed' : 'unknown');
        else setTimeout(poll, 2000);
      } catch {
        if (tries >= 8) setStatus('unknown');
        else setTimeout(poll, 2000);
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [refId, vs, institutionId, hint]);

  return (
    <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center px-4" data-testid="payment-return-page">
      <Card className="max-w-lg w-full p-6 md:p-10 text-center">
        {status === 'polling' && (
          <>
            <Loader2 className="w-16 h-16 text-slate-400 animate-spin mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Ověřujeme platbu...</h1>
            <p className="text-gray-600 mb-1">Čekáme na potvrzení od banky.</p>
            <p className="text-xs text-gray-400">Pokus {attempts} z 15</p>
          </>
        )}
        {status === 'paid' && (
          <>
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Platba úspěšná</h1>
            <p className="text-gray-600 mb-4">
              Částka <strong>{detail?.amount} {detail?.currency}</strong> byla zaplacena.
              Vaše přihláška je {detail?.application_status === 'approved' ? 'potvrzena' : 'čeká na potvrzení organizátora'}.
            </p>
            <p className="text-xs text-gray-400">VS: {detail?.variable_symbol}</p>
          </>
        )}
        {status === 'failed' && (
          <>
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Platba se nezdařila</h1>
            <p className="text-gray-600 mb-4">Zkuste platbu prosím opakovat, nebo kontaktujte organizátora.</p>
          </>
        )}
        {status === 'unknown' && (
          <>
            <Loader2 className="w-16 h-16 text-slate-400 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Stav platby neznámý</h1>
            <p className="text-gray-600 mb-4">
              Banka zatím neposlala definitivní potvrzení. Pokud jste platbu dokončili,
              stav se aktualizuje do několika minut. Organizátor přihlášku potvrdí po přijetí.
            </p>
          </>
        )}

        <div className="mt-6">
          <Button variant="outline" onClick={() => navigate(-1)} data-testid="payment-return-back">
            <ArrowLeft className="w-4 h-4 mr-1" /> Zpět
          </Button>
        </div>
      </Card>
    </div>
  );
}
