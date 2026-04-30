import React from 'react';
import { Info } from 'lucide-react';
import { Popover, PopoverTrigger, PopoverContent } from '../ui/popover';

/**
 * Small inline `(i)` icon that opens a popover with a helper text.
 * Used next to form labels in the program editor for self-service onboarding.
 *
 * Why click-to-open instead of hover only:
 *   - Friendly to mobile (no hover events)
 *   - User has time to read longer copy without losing focus on the input
 */
export default function FieldTooltip({ text, testId, side = 'top' }) {
  if (!text) return null;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Více informací"
          className="inline-flex items-center justify-center w-4 h-4 rounded-full text-slate-400 hover:text-[#4A6FA5] hover:bg-slate-100 transition-colors ml-1.5 align-middle"
          data-testid={testId || 'field-tooltip'}
        >
          <Info className="w-3.5 h-3.5" strokeWidth={2.25} />
        </button>
      </PopoverTrigger>
      <PopoverContent
        side={side}
        align="start"
        className="w-72 text-xs leading-relaxed text-slate-700 border-slate-200"
      >
        {text}
      </PopoverContent>
    </Popover>
  );
}
