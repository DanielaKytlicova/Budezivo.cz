import React from 'react';
import { ArrowLeft, CreditCard, Download, ExternalLink, Link as LinkIcon } from 'lucide-react';
import { Card } from '../ui/card';
import { HELP_GUIDES, HELP_MANUAL_URL, getHelpGuidePdfUrl } from './helpGuides';

const GUIDE_ICONS = {
  'web-links': LinkIcon,
  comgate: CreditCard,
};

export const HelpCenter = ({ onBack }) => (
  <div className="space-y-6" data-testid="settings-help-section">
    <div className="flex items-center gap-4">
      <button
        type="button"
        onClick={onBack}
        className="rounded-lg p-2 hover:bg-gray-100"
        aria-label="Zpět do nastavení"
      >
        <ArrowLeft className="h-5 w-5" aria-hidden="true" />
      </button>
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Nápověda a návody</h1>
        <p className="text-sm text-slate-500">
          Postupy můžete otevřít přímo zde nebo předat kolegům jako PDF.
        </p>
      </div>
    </div>

    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {Object.values(HELP_GUIDES).map((guide) => {
        const Icon = GUIDE_ICONS[guide.id];
        return (
          <Card
            key={guide.id}
            className="flex flex-col overflow-hidden"
            data-testid={`help-guide-${guide.id}`}
          >
            <div className="bg-[#192938] p-5 text-white">
              <div className="mb-4 flex items-start justify-between gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                {guide.optional && (
                  <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-medium">
                    Volitelné
                  </span>
                )}
              </div>
              <h2 className="text-lg font-semibold">{guide.title}</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-200">{guide.description}</p>
            </div>

            <div className="flex flex-1 flex-col p-5">
              <dl className="mb-4 space-y-1 text-xs text-slate-500">
                <div>
                  <dt className="inline font-semibold text-slate-700">Pro koho: </dt>
                  <dd className="inline">{guide.audience}</dd>
                </div>
                <div>
                  <dt className="inline font-semibold text-slate-700">Čas: </dt>
                  <dd className="inline">{guide.duration}</dd>
                </div>
              </dl>

              {guide.optional && (
                <p className="mb-4 rounded-lg bg-[#f5f0e8] px-3 py-2 text-xs text-[#66563e]">
                  Tento návod se vás týká pouze tehdy, pokud chcete přijímat online platby přes
                  Comgate.
                </p>
              )}

              <ol className="mb-5 space-y-2 text-sm text-slate-700">
                {guide.steps.map((step, index) => (
                  <li key={step} className="flex gap-2">
                    <span className="font-semibold text-[#192938]">{index + 1}.</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>

              <div className="mt-auto flex flex-wrap gap-2 border-t pt-4">
                <a
                  href={getHelpGuidePdfUrl(guide)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg bg-[#192938] px-3 py-2 text-sm font-semibold text-white hover:bg-[#243a52]"
                >
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  Otevřít návod
                </a>
                <a
                  href={HELP_MANUAL_URL}
                  download
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-[#192938] hover:bg-slate-50"
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  Stáhnout PDF
                </a>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  </div>
);
