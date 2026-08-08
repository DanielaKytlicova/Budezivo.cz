import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeft, ArrowRight, ExternalLink, X, HelpCircle } from 'lucide-react';

const PADDING = 8;
const CARD_WIDTH = 360;
const CARD_OFFSET = 14;

function findTarget(testId) {
  if (!testId) return null;
  return document.querySelector(`[data-testid="${testId}"]`);
}

function computeRect(el) {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    top: r.top - PADDING,
    left: r.left - PADDING,
    width: r.width + PADDING * 2,
    height: r.height + PADDING * 2,
  };
}

export const GuidedHelpTour = ({ steps, title, pdfUrl, onClose }) => {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);
  const step = steps[index];
  const totalSteps = steps.length;

  const measure = useCallback(() => {
    let attempts = 0;
    const tryMeasure = () => {
      const el = findTarget(step?.targetTestId);
      if (!el) {
        attempts += 1;
        if (attempts < 6) {
          setTimeout(tryMeasure, 100);
        } else {
          setRect(null);
        }
        return;
      }
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      setTimeout(() => setRect(computeRect(el)), 280);
    };
    tryMeasure();
  }, [step]);

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useLayoutEffect(() => {
    measure();
    const onResize = () => {
      const el = findTarget(step?.targetTestId);
      setRect(computeRect(el));
    };
    window.addEventListener('resize', onResize);
    window.addEventListener('scroll', onResize, true);
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('scroll', onResize, true);
    };
  }, [measure, step]);

  const goNext = () => {
    if (index < totalSteps - 1) setIndex(index + 1);
    else onClose();
  };

  const goPrev = () => {
    if (index > 0) setIndex(index - 1);
  };

  let cardStyle = {
    position: 'fixed',
    width: CARD_WIDTH,
    zIndex: 100001,
    pointerEvents: 'auto',
  };

  if (rect) {
    const viewportH = window.innerHeight;
    const viewportW = window.innerWidth;
    const estimatedCardH = 270;
    const margin = 16;
    const spaceRight = viewportW - (rect.left + rect.width) - margin;
    const spaceLeft = rect.left - margin;
    const spaceBelow = viewportH - (rect.top + rect.height) - margin;
    const spaceAbove = rect.top - margin;
    const needsSide = CARD_WIDTH + CARD_OFFSET;
    const needsTopBottom = estimatedCardH + CARD_OFFSET;
    let placed = false;

    const placeRight = () => {
      cardStyle.left = rect.left + rect.width + CARD_OFFSET;
      cardStyle.top = Math.min(
        Math.max(margin, rect.top + rect.height / 2 - estimatedCardH / 2),
        viewportH - estimatedCardH - margin,
      );
      placed = true;
    };
    const placeLeft = () => {
      cardStyle.left = rect.left - CARD_OFFSET - CARD_WIDTH;
      cardStyle.top = Math.min(
        Math.max(margin, rect.top + rect.height / 2 - estimatedCardH / 2),
        viewportH - estimatedCardH - margin,
      );
      placed = true;
    };
    const placeBelow = () => {
      cardStyle.top = rect.top + rect.height + CARD_OFFSET;
      cardStyle.left = Math.min(Math.max(margin, rect.left), viewportW - CARD_WIDTH - margin);
      placed = true;
    };
    const placeAbove = () => {
      cardStyle.top = Math.max(margin, rect.top - CARD_OFFSET - estimatedCardH);
      cardStyle.left = Math.min(Math.max(margin, rect.left), viewportW - CARD_WIDTH - margin);
      placed = true;
    };

    if (step?.placement === 'right' && spaceRight >= needsSide) placeRight();
    else if (step?.placement === 'left' && spaceLeft >= needsSide) placeLeft();
    else if (spaceRight >= needsSide) placeRight();
    else if (spaceLeft >= needsSide) placeLeft();
    else if (spaceBelow >= needsTopBottom) placeBelow();
    else if (spaceAbove >= needsTopBottom) placeAbove();

    if (!placed) {
      cardStyle.top = '50%';
      cardStyle.left = '50%';
      cardStyle.transform = 'translate(-50%, -50%)';
    }
  } else {
    cardStyle.top = '50%';
    cardStyle.left = '50%';
    cardStyle.transform = 'translate(-50%, -50%)';
  }

  return createPortal(
    <div data-testid="guided-help-tour" className="select-none" style={{ pointerEvents: 'auto' }}>
      <div
        className="fixed inset-0"
        style={{ zIndex: 99999, background: 'rgba(15,23,42,0.4)', pointerEvents: 'auto' }}
        onClick={onClose}
      />

      {rect && (
        <div
          className="fixed rounded-lg transition-all duration-200"
          style={{
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            zIndex: 100000,
            boxShadow: '0 0 0 9999px rgba(15,23,42,0.55)',
            outline: '2px solid #C4AB86',
            pointerEvents: 'auto',
            cursor: 'default',
          }}
          onClick={(e) => e.stopPropagation()}
          data-testid="guided-help-spotlight"
        />
      )}

      <div
        className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
        style={cardStyle}
        data-testid="guided-help-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-[#2B3E50] to-[#3a516a] px-5 py-3">
          <div className="flex min-w-0 items-center gap-2 text-white">
            <HelpCircle className="h-4 w-4 shrink-0 text-[#C4AB86]" />
            <span className="truncate text-xs font-semibold uppercase tracking-wide">
              {title} - krok {index + 1}/{totalSteps}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Zavřít nápovědu"
            className="p-1 text-white/70 hover:text-white"
            data-testid="guided-help-close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-4">
          <h3 className="mb-1.5 text-base font-semibold text-slate-900">{step.title}</h3>
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{step.body}</p>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-slate-100 bg-slate-50 px-5 py-3">
          {pdfUrl ? (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-slate-500 underline hover:text-slate-800"
              data-testid="guided-help-pdf"
            >
              PDF návod <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            {index > 0 && (
              <button
                type="button"
                onClick={goPrev}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-white"
                data-testid="guided-help-prev"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Zpět
              </button>
            )}
            <button
              type="button"
              onClick={goNext}
              className="inline-flex items-center gap-1.5 rounded-md bg-[#2B3E50] px-4 py-1.5 text-sm text-white hover:bg-[#1f2d3d]"
              data-testid="guided-help-next"
            >
              {index < totalSteps - 1 ? 'Další' : 'Dokončit'}
              {index < totalSteps - 1 && <ArrowRight className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
};
