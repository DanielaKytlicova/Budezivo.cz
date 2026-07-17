/**
 * Read-only "Připomínka před návštěvou" status shown in the reservation detail.
 * The checkbox is NOT interactive — it reflects the email-log truth.
 */
import React from 'react';
import { CheckSquare, Square, AlertTriangle } from 'lucide-react';

const TZ = 'Europe/Prague';
const CANCELLED = ['cancelled', 'rejected', 'completed', 'no_show', 'deleted'];

function fmt(dt) {
  if (!dt) return '';
  try {
    return new Date(dt).toLocaleString('cs-CZ', {
      timeZone: TZ, day: 'numeric', month: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return String(dt); }
}

function subtractWorkingDays(dateStr, n) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const cur = new Date(y, m - 1, d);
  let left = n;
  while (left > 0) {
    cur.setDate(cur.getDate() - 1);
    const wd = cur.getDay(); // 0=Sun..6=Sat
    if (wd >= 1 && wd <= 5) left -= 1;
  }
  return cur.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', year: 'numeric' });
}

export const VisitReminderStatus = ({ booking, reminderEnabled }) => {
  if (!booking) return null;

  const sentAt = booking.visit_reminder_sent_at;
  const err = booking.visit_reminder_error;
  const lastAttempt = booking.visit_reminder_last_attempt_at;
  const notEligible = CANCELLED.includes(booking.status) || !booking.contact_email;

  let checked = false;
  let title = '';
  let sub = '';
  let danger = false;

  if (sentAt) {
    checked = true;
    title = 'Připomínka byla odeslána';
    sub = `Odesláno: ${fmt(sentAt)}`;
  } else if (err && lastAttempt) {
    danger = true;
    title = 'Odeslání připomínky se nezdařilo';
    sub = `Poslední pokus: ${fmt(lastAttempt)} · ${err}`;
  } else if (notEligible) {
    const reason = !booking.contact_email
      ? 'chybí e-mail'
      : (booking.status === 'completed' ? 'návštěva proběhla'
        : (['cancelled', 'deleted'].includes(booking.status) ? 'rezervace byla zrušena' : 'rezervace není potvrzená'));
    title = 'Připomínka se neodesílá';
    sub = `Důvod: ${reason}`;
  } else if (!reminderEnabled) {
    title = 'Připomínka je v nastavení vypnutá';
  } else {
    title = 'Připomínka zatím nebyla odeslána';
    try { sub = `Plánované odeslání: ${subtractWorkingDays(booking.date, 2)}`; } catch { /* noop */ }
  }

  const Icon = danger ? AlertTriangle : (checked ? CheckSquare : Square);
  const color = danger ? 'text-red-500' : (checked ? 'text-emerald-600' : 'text-slate-400');

  return (
    <div className="pt-3 border-t" data-testid="visit-reminder-status">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Připomínka před návštěvou</p>
      <div className="flex items-start gap-2.5">
        <Icon className={`w-4.5 h-4.5 mt-0.5 shrink-0 ${color}`} />
        <div>
          <p className="text-sm text-slate-800" data-testid="visit-reminder-title">{title}</p>
          {sub && <p className="text-xs text-slate-500 mt-0.5" data-testid="visit-reminder-sub">{sub}</p>}
        </div>
      </div>
    </div>
  );
};

export default VisitReminderStatus;
