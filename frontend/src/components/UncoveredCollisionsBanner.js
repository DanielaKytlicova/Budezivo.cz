import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, ChevronRight, X } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

/**
 * Amber banner shown on the lecturer dashboard when there are unassigned
 * bookings that collide with already-scheduled ones and fall within the
 * lecturer's declared specialisations (``supported_program_ids`` or
 * ``learning_program_ids``). The idea: the admin doesn't need to cold-call
 * external lecturers — the dashboard proactively nudges them.
 *
 * User's choice (iter77): banner-only (no modal on login), click opens a
 * details dialog with the list so the lecturer sees exactly which slots
 * are open before contacting the organiser.
 *
 * Props:
 *   - user:         { id, role, supported_program_ids, learning_program_ids }
 *   - reservations: array<booking> — current institution bookings
 */
const parseTimeRange = (tb) => {
  if (!tb) return null;
  const m = String(tb).match(/^(\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?$/);
  if (!m) return null;
  const start = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
  const end = m[3] ? parseInt(m[3], 10) * 60 + parseInt(m[4], 10) : start + 60;
  return { start, end };
};

export default function UncoveredCollisionsBanner({ user, reservations }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const candidates = useMemo(() => {
    if (!user || !Array.isArray(reservations) || reservations.length === 0) return [];
    // Only external / lecturer-type users get the nudge. Admin/educator roles
    // already see the collision indicator on the booking card and manage it
    // directly — no need to interrupt them here.
    const role = user.role;
    if (!['lektor', 'edukator'].includes(role)) return [];

    const allowed = new Set([
      ...(Array.isArray(user.supported_program_ids) ? user.supported_program_ids : []),
      ...(Array.isArray(user.learning_program_ids) ? user.learning_program_ids : []),
    ]);
    if (allowed.size === 0) return [];

    // Detect per-day overlaps; a reservation is a "candidate" iff:
    //   * it has no assigned lecturer (assigned_lecturer_id/name missing)
    //   * its program_id is in the user's allowed set
    //   * it overlaps with at least one other active reservation the same day
    //     (i.e. there IS a real capacity pressure, not just a lone slot)
    const active = reservations.filter(r => r.status !== 'cancelled' && r.status !== 'rejected');
    const byDate = new Map();
    active.forEach(r => {
      const list = byDate.get(r.date) || [];
      list.push(r);
      byDate.set(r.date, list);
    });
    const out = [];
    byDate.forEach(list => {
      list.forEach((r, i) => {
        if (r.assigned_lecturer_id || r.assigned_lecturer_name) return;
        if (!allowed.has(r.program_id)) return;
        const rr = parseTimeRange(r.time_block);
        if (!rr) return;
        const overlaps = list.some((p, j) => {
          if (i === j) return false;
          const pr = parseTimeRange(p.time_block);
          return pr && rr.start < pr.end && pr.start < rr.end;
        });
        if (overlaps) out.push(r);
      });
    });
    // Newest first so the lecturer reacts to fresh pressure.
    return out.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
  }, [user, reservations]);

  if (candidates.length === 0 || dismissed) return null;

  return (
    <>
      <Card
        className="p-3 md:p-4 bg-amber-50 border-amber-300 border-2"
        data-testid="uncovered-collisions-banner"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-amber-900">
              {candidates.length === 1
                ? '1 rezervace hledá lektora ve vašem programu'
                : `${candidates.length} rezervací hledá lektora ve vašich programech`}
            </div>
            <p className="text-sm text-amber-800 mt-0.5">
              V rezervacích vznikla časová kolize a některé bloky zatím nemají přiděleného lektora.
              Podívejte se, zda byste některý blok nepokryli.
            </p>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <Button
              size="sm"
              onClick={() => setOpen(true)}
              className="bg-amber-600 hover:bg-amber-700 text-white"
              data-testid="uncovered-collisions-open"
            >
              Zobrazit bloky <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              aria-label="Skrýt"
              className="p-1.5 rounded hover:bg-amber-200 transition-colors"
              data-testid="uncovered-collisions-dismiss"
            >
              <X className="w-4 h-4 text-amber-700" />
            </button>
          </div>
        </div>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nepokryté bloky ve vašich programech</DialogTitle>
          </DialogHeader>

          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {candidates.map(r => (
              <div
                key={r.id}
                className="p-3 border border-amber-200 rounded-lg bg-amber-50"
                data-testid={`uncovered-item-${r.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 truncate">{r.program_name || 'Program'}</div>
                    <div className="text-xs text-slate-600 mt-0.5">
                      {r.date} · {r.time_block || '—'}
                    </div>
                    <div className="text-xs text-slate-600 truncate">
                      Škola: {r.school_name}{' · '}{r.num_students || 0} žáků
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-2 text-xs text-slate-500">
            Pokud byste některý z bloků chtěli pokrýt, ozvěte se organizátorovi / kurátorovi instituce —
            přiřadí vás do rezervace přes <span className="font-medium">Rezervace → detail → Přiřadit lektora</span>.
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Zavřít</Button>
            <Button
              onClick={() => { setOpen(false); navigate('/admin/bookings'); }}
              className="bg-slate-800 hover:bg-slate-700 text-white"
              data-testid="uncovered-go-bookings"
            >
              Otevřít Rezervace
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
