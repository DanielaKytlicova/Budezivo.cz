import React from 'react';
import { Link } from 'react-router-dom';
import { UserPlus, Users } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';

export default function LeadTeamAccessCard() {
  return (
    <Card className="flex flex-col gap-4 border-purple-200 bg-purple-50 p-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <Users className="mt-1 h-5 w-5 shrink-0 text-purple-600" aria-hidden="true" />
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Uživatelé leadů</h2>
          <p className="mt-1 text-sm text-slate-600">
            Přidávejte spolupracovníky, nastavujte jim přihlašovací údaje a přiřazujte leady.
          </p>
        </div>
      </div>
      <Button asChild className="shrink-0" data-testid="superadmin-lead-team">
        <Link to="/admin/leady/tym">
          <UserPlus className="mr-2 h-4 w-4" aria-hidden="true" />
          Spravovat uživatele leadů
        </Link>
      </Button>
    </Card>
  );
}
