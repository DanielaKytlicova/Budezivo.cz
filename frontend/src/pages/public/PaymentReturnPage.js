import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle, XCircle, Loader2, Home, Calendar, MapPin, User, Mail, CreditCard, Hash } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { API } from '../../config/api';

/**
 * Payment return page.
 *
 * After a successful payment we render a full **order summary** so the
 * customer has a clear receipt-like confirmation: program / date / time,
 * institution, amount, applicant info, and variable symbol. The "Zpět"
 * button takes them home (history-back was confusing — it returned to the
 * payment-init page that no longer applied to a paid order).
 *
 * Query params (any subset):
 *   - refId=<application_id>          (Comgate-portal URLs substitute ${refId})
 *   - id=<comgate_trans_id>           (Comgate-portal URLs substitute ${id})
 *   - vs=<variable_symbol>
 *   - institution=<id>                (only needed for vs fallback)
 *   - status=paid|cancelled|pending   (optimistic hint from gateway)
 *
 * Lookup priority:
 *   1. /api/event-payments/by-ref/{refId}   (preferred — works with portal URLs)
 *   2. /api/event-payments/by-vs/{institution}/{vs}   (fallback)
 */

const fmtDateTime = (iso) => {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString('cs-CZ', {
      day: 'numeric', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
};

const SummaryRow = ({ icon: Icon, label, value, mono = false, testid }) => {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-100 last:border-b-0" data-testid={testid}>
      {Icon && <Icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />}
      <div className="flex-1 min-w-0">
        <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">{label}</div>
        <div className={`text-sm text-slate-900 mt-0.5 break-words ${mono ? 'font-mono' : ''}`}>{value}</div>
      </div>
    </div>
  );
};

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

  const goHome = () => navigate('/');

  // Pretty-print currency consistently across CZ locale.
  const fmtAmount = (amt, cur) => {
    if (amt == null) return null;
    try {
      return new Intl.NumberFormat('cs-CZ', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(amt) + ' ' + (cur || 'CZK');
    } catch {
      return `${amt} ${cur || 'CZK'}`;
    }
  };

  const ev = detail?.event;
  const dateRange = ev?.starts_at
    ? (ev?.ends_at && ev.ends_at !== ev.starts_at
        ? `${fmtDateTime(ev.starts_at)} → ${fmtDateTime(ev.ends_at)}`
        : fmtDateTime(ev.starts_at))
    : null;

  return (
    <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center px-4 py-8" data-testid="payment-return-page">
      <Card className="max-w-xl w-full p-6 md:p-8">
        {status === 'polling' && (
          <div className="text-center py-8">
            <Loader2 className="w-14 h-14 text-slate-400 animate-spin mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-slate-900 mb-1">Ověřujeme platbu…</h1>
            <p className="text-gray-600 mb-1">Čekáme na potvrzení od banky.</p>
            <p className="text-xs text-gray-400">Pokus {attempts} z 15</p>
          </div>
        )}

        {status === 'paid' && (
          <div data-testid="payment-return-paid">
            <div className="text-center pb-4 border-b border-slate-100">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-3" />
              <h1 className="text-2xl font-bold text-slate-900 mb-1">Platba úspěšná</h1>
              <p className="text-gray-600">
                Částka <strong>{fmtAmount(detail?.amount, detail?.currency)}</strong> byla zaplacena.
                {detail?.application_status === 'approved'
                  ? ' Vaše přihláška je potvrzena.'
                  : ' Vaše přihláška čeká na potvrzení organizátora.'}
              </p>
            </div>

            <div className="mt-4 space-y-0.5">
              <h2 className="text-sm font-semibold text-slate-700 mb-2 uppercase tracking-wide">Souhrn objednávky</h2>
              <SummaryRow icon={Calendar} label="Program" value={ev?.title} testid="summary-program" />
              <SummaryRow icon={Calendar} label="Termín" value={dateRange} testid="summary-date" />
              <SummaryRow icon={MapPin} label="Pořadatel" value={detail?.institution_name} testid="summary-institution" />
              <SummaryRow icon={User} label="Účastník" value={detail?.applicant_name} testid="summary-applicant" />
              <SummaryRow icon={Mail} label="E-mail" value={detail?.applicant_email} testid="summary-email" />
              <SummaryRow icon={CreditCard} label="Zaplaceno" value={fmtAmount(detail?.amount, detail?.currency)} testid="summary-amount" />
              <SummaryRow icon={Hash} label="Variabilní symbol" value={detail?.variable_symbol} mono testid="summary-vs" />
              <SummaryRow icon={CheckCircle} label="Datum platby" value={fmtDateTime(detail?.paid_at)} testid="summary-paid-at" />
            </div>

            <div className="mt-6 rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-xs text-slate-600">
              Potvrzení a daňový doklad obdržíte e-mailem{detail?.applicant_email ? <> na adresu <span className="font-medium">{detail.applicant_email}</span></> : ''}.
              Pokud ji neuvidíte do několika minut, zkontrolujte složku Spam.
            </div>

            <div className="mt-6 flex gap-2 justify-center flex-wrap">
              <Button variant="outline" onClick={() => window.print()} data-testid="payment-return-print">
                Vytisknout potvrzení
              </Button>
              <Button onClick={goHome} className="bg-slate-800 hover:bg-slate-700 text-white" data-testid="payment-return-home">
                <Home className="w-4 h-4 mr-1" /> Zpět na hlavní stránku
              </Button>
            </div>
          </div>
        )}

        {status === 'failed' && (
          <div className="text-center py-6">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-3" />
            <h1 className="text-2xl font-bold text-slate-900 mb-1">Platba se nezdařila</h1>
            <p className="text-gray-600 mb-4">
              Zkuste platbu prosím opakovat, nebo kontaktujte organizátora.
              {detail?.variable_symbol && <> Při komunikaci uveďte VS <span className="font-mono font-medium">{detail.variable_symbol}</span>.</>}
            </p>
            <div className="flex gap-2 justify-center flex-wrap">
              <Button variant="outline" onClick={() => navigate(-1)} data-testid="payment-return-retry">
                Zkusit znovu
              </Button>
              <Button onClick={goHome} className="bg-slate-800 hover:bg-slate-700 text-white" data-testid="payment-return-home">
                <Home className="w-4 h-4 mr-1" /> Hlavní stránka
              </Button>
            </div>
          </div>
        )}

        {status === 'unknown' && (
          <div className="text-center py-6">
            <Loader2 className="w-16 h-16 text-slate-400 mx-auto mb-3" />
            <h1 className="text-2xl font-bold text-slate-900 mb-1">Stav platby neznámý</h1>
            <p className="text-gray-600 mb-4">
              Banka zatím neposlala definitivní potvrzení. Pokud jste platbu dokončili,
              stav se aktualizuje do několika minut. Organizátor přihlášku potvrdí po přijetí.
              {detail?.variable_symbol && <> VS: <span className="font-mono font-medium">{detail.variable_symbol}</span></>}
            </p>
            <Button onClick={goHome} className="bg-slate-800 hover:bg-slate-700 text-white" data-testid="payment-return-home">
              <Home className="w-4 h-4 mr-1" /> Hlavní stránka
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
