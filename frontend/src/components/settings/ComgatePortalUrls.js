import React, { useState } from 'react';
import { Card } from '../ui/card';
import { Copy, Check, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Comgate Portal URLs — read-only block listing the URLs that the merchant
 * must paste into the Comgate Klientský portál → Nastavení obchodu →
 * Integrace.
 *
 * The URLs use Comgate's ${id} / ${refId} placeholders so the customer-return
 * page receives the transaction id and our application id (refId) regardless
 * of how the payment was initiated.
 *
 * Props:
 *   - frontendBase: e.g. "https://budezivo.cz"
 *   - apiBase:      e.g. "https://api.budezivo.cz"
 */
export default function ComgatePortalUrls({ frontendBase, apiBase }) {
  const [copied, setCopied] = useState(null);

  const fb = (frontendBase || '').replace(/\/$/, '');
  const ab = (apiBase || '').replace(/\/$/, '');

  // eslint-disable-next-line no-template-curly-in-string
  const idQs = '?id=${id}&refId=${refId}';

  const rows = [
    {
      key: 'paid',
      label: 'Url zaplacený',
      value: `${fb}/payment/return?status=paid&id=\${id}&refId=\${refId}`,
      hint: 'Zákazník po úspěšné platbě',
    },
    {
      key: 'cancelled',
      label: 'Url zrušený',
      value: `${fb}/payment/return?status=cancelled&id=\${id}&refId=\${refId}`,
      hint: 'Zákazník po zrušení platby',
    },
    {
      key: 'pending',
      label: 'Url nevyřízený',
      value: `${fb}/payment/return?status=pending&id=\${id}&refId=\${refId}`,
      hint: 'Bankovní převod – platba ještě nebyla potvrzena',
    },
    {
      key: 'notify',
      label: 'Url pro předání výsledku platby (notify)',
      value: `${ab}/api/event-payments/webhook/comgate`,
      hint: 'Server-to-server webhook (Comgate posílá výsledek automaticky)',
    },
  ];

  const copy = async (key, value) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(key);
      toast.success('URL zkopírováno');
      setTimeout(() => setCopied((c) => (c === key ? null : c)), 1800);
    } catch {
      toast.error('Nepodařilo se zkopírovat — zkopíruj ručně');
    }
  };

  return (
    <Card className="p-4 md:p-5 space-y-3 bg-slate-50 border-slate-200" data-testid="comgate-portal-urls">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h4 className="font-semibold text-slate-900 text-sm">URL pro Comgate Klientský portál</h4>
          <p className="text-xs text-slate-600">
            Tyto URL vlož do <span className="font-medium">Klientský portál Comgate → Nastavení obchodu → Integrace</span>.
            Placeholdery <code className="font-mono bg-white px-1 py-0.5 rounded border border-slate-200">${'{id}'}</code> a <code className="font-mono bg-white px-1 py-0.5 rounded border border-slate-200">${'{refId}'}</code> Comgate doplní automaticky.
          </p>
        </div>
        <a
          href="https://portal.comgate.cz/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 underline"
          data-testid="comgate-portal-link"
        >
          Otevřít portál <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <div className="space-y-2 mt-2">
        <div className="grid grid-cols-[1fr_auto] gap-2 text-[11px] uppercase tracking-wide text-slate-500 font-semibold px-1">
          <span>Pole / hodnota</span>
          <span className="text-right pr-2">Akce</span>
        </div>
        {rows.map((r) => (
          <div
            key={r.key}
            className="flex items-stretch gap-2"
            data-testid={`comgate-url-${r.key}`}
          >
            <div className="flex-1 min-w-0 bg-white border border-slate-200 rounded-md px-3 py-2">
              <div className="text-[11px] font-medium text-slate-700">{r.label}</div>
              <div className="text-xs font-mono text-slate-900 break-all leading-relaxed mt-0.5">
                {r.value}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">{r.hint}</div>
            </div>
            <button
              type="button"
              onClick={() => copy(r.key, r.value)}
              className="px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-100 text-xs font-medium text-slate-700 transition-colors flex items-center gap-1"
              data-testid={`comgate-url-copy-${r.key}`}
            >
              {copied === r.key ? (
                <>
                  <Check className="w-3.5 h-3.5 text-green-600" />
                  <span className="hidden sm:inline">Zkopírováno</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Kopírovat</span>
                </>
              )}
            </button>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-600 leading-relaxed">
        <p>
          <span className="font-semibold">Doporučené nastavení v portálu:</span> Povolený způsob založení platby{' '}
          <span className="font-mono">HTTP POST protokol – backend</span> (doporučujeme).
        </p>
        <p className="mt-1">
          Po zadání URL v portálu klikni v <span className="font-medium">Comgate → Test integrace</span> na &bdquo;Otestovat&ldquo;,
          dokud nebudou všechny zelené ✓. Teprve pak je obchod plně funkční pro reálné platby.
        </p>
      </div>
    </Card>
  );
}
