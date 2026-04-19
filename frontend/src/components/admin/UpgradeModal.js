import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Lock, Crown, ArrowRight, Mail } from 'lucide-react';

/**
 * Modal shown when user tries to access a locked feature.
 * Redirects to pricing page or contact form.
 */
export const UpgradeModal = ({ open, onClose, featureLabel, minPlan, minPlanLabel }) => {
  const navigate = useNavigate();

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-amber-500" />
            Funkce vyžaduje vyšší plán
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <p className="text-sm text-slate-600">
            Funkce <strong>{featureLabel || 'tato funkce'}</strong> je dostupná od plánu{' '}
            <Badge className="bg-amber-100 text-amber-800 ml-1">{minPlanLabel || 'PRO'}</Badge>
          </p>
          <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600">
            Upgradujte svůj plán pro přístup k této a dalším pokročilým funkcím.
          </div>
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" size="sm" onClick={() => window.open('mailto:info@budezivo.cz?subject=Zájem o plán ' + (minPlanLabel || 'PRO'))}>
            <Mail className="w-4 h-4 mr-1" /> Kontaktovat nás
          </Button>
          <Button size="sm" onClick={() => { onClose(); navigate('/admin/plan'); }} data-testid="upgrade-modal-plans-btn">
            <Crown className="w-4 h-4 mr-1" /> Zobrazit plány
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UpgradeModal;
