/**
 * PlanUsageBanner — SOFT plan-limit usage meters + upgrade prompts.
 *
 * Reads GET /api/plan/usage (never blocks anything — `enforced: false`).
 * - Hidden entirely when the plan has unlimited quotas (PRO / PRO+).
 * - Shows green/amber/red meters for programs + this-month bookings.
 * - Surfaces an upgrade CTA when a quota is near (>=80%) or over the limit.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { TrendingUp, AlertTriangle, ArrowUpRight } from 'lucide-react';
import { API } from '../../config/api';

const Meter = ({ label, quota }) => {
  if (!quota || quota.unlimited) return null;
  const pct = Math.min(quota.percent, 100);
  const tone = quota.over_limit
    ? { bar: 'bg-red-500', text: 'text-red-600' }
    : quota.near_limit
    ? { bar: 'bg-amber-500', text: 'text-amber-600' }
    : { bar: 'bg-emerald-500', text: 'text-slate-500' };
  return (
    <div data-testid={`usage-meter-${label.toLowerCase()}`}>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className={`text-sm font-semibold ${tone.text}`}>
          {quota.used}<span className="text-slate-400 font-normal"> / {quota.limit}</span>
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${tone.bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export const PlanUsageBanner = () => {
  const [usage, setUsage] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    axios
      .get(`${API}/plan/usage`)
      .then((res) => { if (active) setUsage(res.data); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  if (!usage) return null;

  const { programs, bookings_month } = usage;
  const blocks = [programs, bookings_month].filter(Boolean);

  // Unlimited plan → nothing to show.
  if (blocks.every((b) => b.unlimited)) return null;

  const anyOver = blocks.some((b) => !b.unlimited && b.over_limit);
  const anyNear = blocks.some((b) => !b.unlimited && b.near_limit);

  return (
    <Card
      className={`p-5 mb-6 border ${anyOver ? 'border-red-200 bg-red-50/40' : anyNear ? 'border-amber-200 bg-amber-50/40' : 'border-slate-200'}`}
      data-testid="plan-usage-banner"
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-800">Využití tarifu</h3>
        </div>
        <Button
          size="sm"
          variant={anyOver ? 'default' : 'outline'}
          className={anyOver ? 'bg-slate-900 hover:bg-slate-800 text-white' : ''}
          onClick={() => navigate('/admin/plan')}
          data-testid="usage-upgrade-btn"
        >
          Vylepšit tarif <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Meter label="Programy" quota={programs} />
        <Meter label="Rezervace tento měsíc" quota={bookings_month} />
      </div>

      {(anyOver || anyNear) && (
        <div
          className={`mt-4 flex items-start gap-2 rounded-lg p-3 text-xs ${anyOver ? 'bg-red-100/60 text-red-700' : 'bg-amber-100/60 text-amber-700'}`}
          data-testid="usage-limit-alert"
        >
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {anyOver
              ? 'Dosáhli jste limitu svého tarifu. Funkce zůstávají dostupné, ale doporučujeme přejít na vyšší tarif pro vyšší limity.'
              : 'Blížíte se limitu svého tarifu. Zvažte přechod na vyšší tarif, ať vás nic nezdrží.'}
          </span>
        </div>
      )}
    </Card>
  );
};

export default PlanUsageBanner;
