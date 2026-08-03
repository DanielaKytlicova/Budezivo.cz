import React, { useState } from 'react';
import { ChevronDown, Download, ExternalLink, HelpCircle } from 'lucide-react';
import { HELP_GUIDES, HELP_MANUAL_URL, getHelpGuidePdfUrl } from './helpGuides';

export const ContextHelp = ({ guideId, className = '' }) => {
  const [expanded, setExpanded] = useState(false);
  const guide = HELP_GUIDES[guideId];

  if (!guide) return null;

  return (
    <aside
      className={`rounded-xl border border-[#d8dee8] bg-[#f5f7fa] ${className}`}
      data-testid={`context-help-${guide.id}`}
    >
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-center gap-3 p-3 text-left text-[#192938]"
        aria-expanded={expanded}
        aria-controls={`context-help-content-${guide.id}`}
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white">
          <HelpCircle className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-xs font-medium text-slate-500">Potřebujete poradit?</span>
          <span className="block text-sm font-semibold">{guide.title}</span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {expanded && (
        <div
          id={`context-help-content-${guide.id}`}
          className="border-t border-[#d8dee8] px-4 pb-4 pt-3"
        >
          {guide.optional && (
            <p className="mb-3 rounded-lg bg-white px-3 py-2 text-xs text-slate-600">
              Comgate je volitelná. Pokud online platby nevyužíváte, nemusíte tento postup
              dokončovat.
            </p>
          )}
          <ol className="space-y-2 text-sm text-slate-700">
            {guide.steps.map((step, index) => (
              <li key={step} className="flex gap-2">
                <span className="font-semibold text-[#192938]">{index + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <div className="mt-4 flex flex-wrap gap-2">
            <a
              href={getHelpGuidePdfUrl(guide)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-[#192938] px-3 py-2 text-xs font-semibold text-white hover:bg-[#243a52]"
              data-testid={`help-open-pdf-${guide.id}`}
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              Otevřít celý návod
            </a>
            <a
              href={HELP_MANUAL_URL}
              download
              className="inline-flex items-center gap-2 rounded-lg border border-[#b8c2d0] bg-white px-3 py-2 text-xs font-semibold text-[#192938] hover:bg-slate-50"
              data-testid={`help-download-pdf-${guide.id}`}
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Stáhnout PDF
            </a>
          </div>
        </div>
      )}
    </aside>
  );
};
