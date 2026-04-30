import React, { useEffect, useLayoutEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeft, ArrowRight, X, Sparkles } from 'lucide-react';

/**
 * Lightweight self-built guided tour for the Program editor.
 *
 * Why no external lib:
 *   - react-joyride / driver.js add ~50–80 kB and pull global CSS that fights
 *     our brand palette. The behaviour we need is small (highlight + tooltip
 *     card + tab switch) so a bespoke ~200-line implementation is cheaper.
 *
 * Spotlight technique:
 *   - One full-screen fixed overlay rendered through a portal
 *   - Above it, a transparent <div> placed at the target's bounding rect with
 *     `box-shadow: 0 0 0 9999px rgba(15,23,42,0.55)` which paints the dim
 *     surrounding without touching the target itself
 *   - Tooltip card is placed below or above depending on viewport space
 *
 * Steps schema:
 *   { tab, targetTestId, title, body, placement? }
 *   - tab: which editor tab to switch to before measuring ('detail'|'settings'|'collision'|'feedback')
 *   - targetTestId: element to spotlight (data-testid value)
 *   - placement: 'bottom' (default) or 'top'
 */

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

export default function ProgramTour({ steps, onClose, onTabChange }) {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);

  const step = steps[index];
  const totalSteps = steps.length;

  // Switch tab when step requires it
  useEffect(() => {
    if (step?.tab && onTabChange) {
      onTabChange(step.tab);
    }
  }, [step, onTabChange]);

  const measure = useCallback(() => {
    const el = findTarget(step?.targetTestId);
    if (!el) {
      setRect(null);
      return;
    }
    // Bring target into view first so its rect is meaningful
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    // Give the smooth scroll a tick to settle, then measure
    setTimeout(() => setRect(computeRect(el)), 280);
  }, [step]);

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
    else onClose(true);
  };

  const goPrev = () => {
    if (index > 0) setIndex(index - 1);
  };

  const skip = () => onClose(false);

  // Compute card position
  // pointerEvents: 'auto' is critical — Radix Dialog (react-remove-scroll)
  // sets pointer-events: none on body/html when open, which propagates to our
  // portal children. We must explicitly re-enable it on every interactive node.
  let cardStyle = {
    position: 'fixed',
    width: CARD_WIDTH,
    zIndex: 100001,
    pointerEvents: 'auto',
  };

  if (rect) {
    const placement = step.placement || 'bottom';
    const viewportH = window.innerHeight;
    const viewportW = window.innerWidth;

    if (placement === 'top' && rect.top - CARD_OFFSET - 200 > 0) {
      cardStyle.top = Math.max(16, rect.top - CARD_OFFSET - 200);
    } else if (rect.top + rect.height + CARD_OFFSET + 220 < viewportH) {
      cardStyle.top = rect.top + rect.height + CARD_OFFSET;
    } else {
      cardStyle.top = Math.max(16, rect.top - CARD_OFFSET - 220);
    }

    let left = rect.left;
    if (left + CARD_WIDTH > viewportW - 16) left = viewportW - CARD_WIDTH - 16;
    if (left < 16) left = 16;
    cardStyle.left = left;
  } else {
    // Centered fallback when target is missing
    cardStyle.top = '50%';
    cardStyle.left = '50%';
    cardStyle.transform = 'translate(-50%, -50%)';
  }

  return createPortal(
    <div
      data-testid="program-tour"
      className="select-none"
      style={{ pointerEvents: 'auto' }}
    >
      {/* Overlay — blocks clicks to underlying form except spotlight area */}
      <div
        className="fixed inset-0"
        style={{
          zIndex: 99999,
          background: 'rgba(15,23,42,0.4)',
          pointerEvents: 'auto',
        }}
        onClick={skip}
      />

      {/* Spotlight cutout — intercepts clicks so target underneath is NOT
          accidentally activated while the tour is highlighting it. The user
          should navigate through Next/Prev only. */}
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
          data-testid="program-tour-spotlight"
        />
      )}

      {/* Tooltip card */}
      <div
        className="bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden"
        style={cardStyle}
        data-testid="program-tour-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 bg-gradient-to-r from-[#2B3E50] to-[#3a516a]">
          <div className="flex items-center gap-2 text-white">
            <Sparkles className="w-4 h-4 text-[#C4AB86]" />
            <span className="text-xs font-semibold tracking-wide uppercase">
              Ukázka — krok {index + 1}/{totalSteps}
            </span>
          </div>
          <button
            type="button"
            onClick={skip}
            aria-label="Zavřít ukázku"
            className="text-white/70 hover:text-white p-1"
            data-testid="program-tour-close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4">
          <h3 className="font-semibold text-slate-900 text-base mb-1.5">
            {step.title}
          </h3>
          <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
            {step.body}
          </div>
        </div>

        <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 bg-slate-50">
          <button
            type="button"
            onClick={skip}
            className="text-xs text-slate-500 hover:text-slate-700"
            data-testid="program-tour-skip"
          >
            Přeskočit ukázku
          </button>
          <div className="flex items-center gap-2">
            {index > 0 && (
              <button
                type="button"
                onClick={goPrev}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-sm border border-slate-300 text-slate-700 hover:bg-white"
                data-testid="program-tour-prev"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Zpět
              </button>
            )}
            <button
              type="button"
              onClick={goNext}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm bg-[#2B3E50] text-white hover:bg-[#1f2d3d]"
              data-testid="program-tour-next"
            >
              {index < totalSteps - 1 ? 'Další' : 'Dokončit'}
              {index < totalSteps - 1 && <ArrowRight className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
