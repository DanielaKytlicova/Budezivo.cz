/**
 * Phase C — "Kalendář byl propojen" dialog shown after a successful OAuth
 * connect. Gives short, provider-specific guidance so the user understands
 * what the connection actually does (import blocks availability; export of
 * reservations is configured separately in Rezervace).
 */
import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { CheckCircle2, CalendarClock, ArrowRight, ShieldCheck } from 'lucide-react';

const PROVIDER_NAME = { google: 'Google kalendář', outlook: 'Outlook kalendář' };

export const ConnectedGuideDialog = ({ open, provider, onClose }) => {
  const name = PROVIDER_NAME[provider] || 'Kalendář';
  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose?.(); }}>
      <DialogContent className="sm:max-w-lg" aria-describedby={undefined} data-testid="calendar-connected-guide">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            {name} byl propojen
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-1 text-sm text-slate-600">
          <div className="flex gap-3">
            <CalendarClock className="w-5 h-5 text-[#4A6FA5] shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-slate-800">Obsazené termíny se přenesou jako blokace</p>
              <p className="text-xs mt-0.5">Události z vašeho osobního kalendáře, které mají čas označený jako „obsazeno", automaticky zablokují vaši dostupnost. Systém vás v ten čas nepřiřadí na kolidující rezervaci.</p>
            </div>
          </div>
          <div className="flex gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-slate-800">Soukromí je zachováno</p>
              <p className="text-xs mt-0.5">Blokuje se pouze <strong>vaše</strong> dostupnost — nikoliv celá instituce, ostatní lektoři ani místnosti. Ostatní role uvidí pouze „Externí kalendář / Nedostupný", nikdy název vaší soukromé události.</p>
            </div>
          </div>
          <div className="flex gap-3">
            <ArrowRight className="w-5 h-5 text-[#C4AB86] shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-slate-800">Chcete do kalendáře vidět i rezervace?</p>
              <p className="text-xs mt-0.5">Export rezervací do vašeho kalendáře zapnete v sekci <strong>Rezervace → Synchronizace kalendáře</strong>. Zde v profilu řídíte pouze blokaci vlastní dostupnosti.</p>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={onClose} className="bg-slate-800 hover:bg-slate-900 text-white" data-testid="calendar-guide-close">
            Rozumím
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConnectedGuideDialog;
