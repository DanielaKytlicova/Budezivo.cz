import React, { useState, useEffect, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { ChevronDown, ChevronLeft, ChevronRight, Ban, CheckCircle, Clock, Users, AlertTriangle, Lock, CalendarDays, Plus, CalendarPlus, X } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';
import { LecturerAvailabilityPage } from './LecturerAvailabilityPage';
import { FieldError, FIELD_ERROR_CLASS } from '../../components/ui/field-error';

const DAY_SHORT = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];
const DAY_NAMES = {
  monday: 'Pondělí',
  tuesday: 'Úterý',
  wednesday: 'Středa',
  thursday: 'Čtvrtek',
  friday: 'Pátek',
  saturday: 'Sobota',
  sunday: 'Neděle',
};
const HOURS = Array.from({ length: 12 }, (_, i) => i + 7); // 7:00 - 18:00

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(date.setDate(diff));
}

function fmtDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function timeToMin(t) {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + (m || 0);
}

const STATUS_COLORS = {
  available: 'bg-emerald-100 border-emerald-200',
  booked: 'bg-slate-200 border-slate-300',
  blocked_exception: 'bg-red-100 border-red-200',
  blocked_lecturer: 'bg-amber-100 border-amber-300',
  blocked_room: 'bg-purple-100 border-purple-200',
  blocked_parallel: 'bg-orange-100 border-orange-200',
  blocked_program: 'bg-rose-100 border-rose-200',
};

const STATUS_LABELS = {
  available: 'Dostupný',
  booked: 'Obsazeno',
  blocked_exception: 'Uzavřeno',
  blocked_lecturer: 'Lektor nedostupný',
  blocked_room: 'Místnost obsazena',
  blocked_parallel: 'Paralelní blokace',
  blocked_program: 'Blokace programu',
};

export const UnifiedAvailabilityPage = ({ embedded = false }) => {
  const { user } = useContext(AuthContext);
  const [viewMode, setViewMode] = useState('personal'); // 'program' | 'personal'
  // Action requested from the program view's quick buttons; consumed by the
  // personal calendar (LecturerAvailabilityPage) to auto-open the right dialog.
  const [pendingAction, setPendingAction] = useState(null);

  const requestPersonalAction = (action) => {
    setPendingAction(action);
    setViewMode('personal');
  };

  // If personal view, render the original LecturerAvailabilityPage with view toggle
  if (viewMode === 'personal') {
    return (
      <LecturerAvailabilityPage
        viewToggle={viewMode}
        onViewToggle={setViewMode}
        embedded={embedded}
        autoOpenAction={pendingAction}
        onAutoOpenConsumed={() => setPendingAction(null)}
      />
    );
  }

  return <ProgramAvailabilityView viewMode={viewMode} onViewModeChange={setViewMode} onRequestPersonalAction={requestPersonalAction} embedded={embedded} />;
};

// ============ Program Availability View ============
const ProgramAvailabilityView = ({ viewMode, onViewModeChange, onRequestPersonalAction, embedded = false }) => {
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const [programs, setPrograms] = useState([]);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [weekSlots, setWeekSlots] = useState({});
  const [loading, setLoading] = useState(false);
  const [slotDetail, setSlotDetail] = useState(null);
  const [showExceptionDialog, setShowExceptionDialog] = useState(false);
  const [exceptionReason, setExceptionReason] = useState('');
  const [exceptions, setExceptions] = useState([]);
  const [allProgramExceptions, setAllProgramExceptions] = useState([]);
  // Program block dialog (creates a program-scoped availability exception)
  const [showProgramBlock, setShowProgramBlock] = useState(false);
  const [programBlockForm, setProgramBlockForm] = useState({ date_from: '', date_to: '', start_time: '', end_time: '', reason: '' });
  const [programBlockProgramIds, setProgramBlockProgramIds] = useState([]);
  const [programBlockFieldErrors, setProgramBlockFieldErrors] = useState({});
  const [programSelectorError, setProgramSelectorError] = useState('');

  useEffect(() => { fetchPrograms(); }, []);
  useEffect(() => {
    if (selectedProgram) doFetchWeek(selectedProgram, weekStart);
  }, [weekStart, selectedProgram]);

  const fetchPrograms = async () => {
    try {
      const res = await axios.get(`${API}/programs`);
      const active = (res.data || []).filter(p => p.status !== 'archived');
      setPrograms(active);
      if (active.length > 0) setSelectedProgram(active[0].id);
    } catch { /* */ }
  };

  const blockablePrograms = programs.filter(p => p.status === 'active');
  const programNameById = (programId) => programs.find(p => p.id === programId)?.name_cs || 'Program';
  const selectedProgramData = programs.find(p => p.id === selectedProgram);
  const todayStr = fmtDate(new Date());

  const groupProgramExceptions = (items) => {
    const grouped = new Map();
    (items || [])
      .filter(e => e.scope_type === 'program')
      .filter(e => !e.date || e.date >= todayStr)
      .forEach(e => {
        const key = `${e.date}|${e.start_time || ''}|${e.end_time || ''}|${e.reason || ''}`;
        const group = grouped.get(key) || {
          key,
          date: e.date,
          start_time: e.start_time,
          end_time: e.end_time,
          reason: e.reason,
          programIds: [],
        };
        if (!group.programIds.includes(e.scope_id)) group.programIds.push(e.scope_id);
        grouped.set(key, group);
      });
    return Array.from(grouped.values()).sort((a, b) => {
      const dateCompare = String(a.date || '').localeCompare(String(b.date || ''));
      if (dateCompare !== 0) return dateCompare;
      return String(a.start_time || '').localeCompare(String(b.start_time || ''));
    });
  };

  const activeProgramExceptionGroups = groupProgramExceptions(allProgramExceptions);

  const openProgramBlockDialog = () => {
    if (!selectedProgram) {
      setProgramSelectorError('Vyberte program pro programovou blokaci.');
      toast.error('Zkontrolujte zvýrazněná pole.');
      return;
    }
    setProgramSelectorError('');
    setProgramBlockForm({ date_from: '', date_to: '', start_time: '', end_time: '', reason: '' });
    setProgramBlockProgramIds(blockablePrograms.some(p => p.id === selectedProgram) ? [selectedProgram] : []);
    setProgramBlockFieldErrors({});
    setShowProgramBlock(true);
  };

  const toggleProgramBlockProgram = (programId) => {
    setProgramBlockProgramIds(prev => (
      prev.includes(programId)
        ? prev.filter(id => id !== programId)
        : [...prev, programId]
    ));
    setProgramBlockFieldErrors(prev => ({ ...prev, program_ids: undefined }));
  };

  const doFetchWeek = async (prog, ws) => {
    setLoading(true);
    const data = {};
    const promises = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(ws);
      d.setDate(d.getDate() + i);
      const dateStr = fmtDate(d);
      promises.push(
        axios.get(`${API}/availability-unified/program/${prog}/slots?date=${dateStr}`)
          .then(res => { data[dateStr] = res.data.slots || []; })
          .catch(() => { data[dateStr] = []; })
      );
    }
    await Promise.all(promises);
    setWeekSlots(data);
    setLoading(false);
    try {
      const res = await axios.get(`${API}/availability-unified/exceptions?scope_type=program&scope_id=${prog}`);
      setExceptions(res.data || []);
      const allRes = await axios.get(`${API}/availability-unified/exceptions?scope_type=program`);
      setAllProgramExceptions(allRes.data || []);
    } catch { setExceptions([]); setAllProgramExceptions([]); }
  };

  const prevWeek = () => { const d = new Date(weekStart); d.setDate(d.getDate() - 7); setWeekStart(d); };
  const nextWeek = () => { const d = new Date(weekStart); d.setDate(d.getDate() + 7); setWeekStart(d); };
  const goToday = () => setWeekStart(getMonday(new Date()));

  const getWeekDays = () => Array.from({ length: 7 }, (_, i) => { const d = new Date(weekStart); d.setDate(d.getDate() + i); return d; });
  const weekDays = getWeekDays();
  const isToday = (d) => fmtDate(d) === fmtDate(new Date());

  // Build a lookup: dateStr -> hour -> slot
  const getSlotForCell = (dateStr, hour) => {
    const slots = weekSlots[dateStr] || [];
    return slots.find(s => {
      if (s.status === 'outside_base_availability') return false;
      const [startStr] = s.time.split('-');
      const startMin = timeToMin(startStr);
      const startHour = Math.floor(startMin / 60);
      return startHour === hour;
    });
  };

  // Check if hour falls within any slot range for this date
  const getCellStatus = (dateStr, hour) => {
    const slots = weekSlots[dateStr] || [];
    const cellStart = hour * 60;
    const cellEnd = cellStart + 60;
    for (const s of slots) {
      if (s.status === 'outside_base_availability') continue;
      const parts = s.time.split('-');
      if (parts.length !== 2) continue;
      const sStart = timeToMin(parts[0]);
      const sEnd = timeToMin(parts[1]);
      if (cellStart < sEnd && cellEnd > sStart) {
        return s;
      }
    }
    return null;
  };

  const handleCellClick = (dateStr, slot) => {
    if (!slot) return;
    setSlotDetail({ date: dateStr, slot });
    if (slot.status === 'available' || slot.status === 'blocked_exception') {
      setExceptionReason('');
      setShowExceptionDialog(true);
    }
  };

  const createException = async () => {
    if (!slotDetail || !selectedProgram) return;
    const [startTime, endTime] = slotDetail.slot.time.split('-');
    try {
      await axios.post(`${API}/availability-unified/exceptions`, {
        scope_type: 'program', scope_id: selectedProgram,
        date: slotDetail.date, start_time: startTime, end_time: endTime,
        reason: exceptionReason || null,
      });
      toast.success('Slot uzavřen');
      setShowExceptionDialog(false);
      doFetchWeek(selectedProgram, weekStart);
    } catch (err) { toast.error(err.response?.data?.detail || 'Chyba'); }
  };

  // Program-scoped block created from the program view's "Přidat blokaci" action.
  // The block always carries the selected program_id; it is never silently saved
  // as a personal block. Requires a program to be selected.
  const createProgramBlock = async () => {
    setProgramSelectorError('');
    const errors = {};
    if (!programBlockForm.date_from) errors.date_from = 'Vyberte datum od.';
    if (!programBlockForm.date_to) errors.date_to = 'Vyberte datum do.';
    if (programBlockForm.date_from && programBlockForm.date_to && programBlockForm.date_to < programBlockForm.date_from) {
      errors.date_to = 'Datum do nesmí být před datem od.';
    }
    if (Boolean(programBlockForm.start_time) !== Boolean(programBlockForm.end_time)) {
      errors.start_time = 'Zadejte začátek i konec, nebo nechte obojí prázdné.';
      errors.end_time = 'Zadejte začátek i konec, nebo nechte obojí prázdné.';
    }
    if (programBlockForm.start_time && programBlockForm.end_time && programBlockForm.end_time <= programBlockForm.start_time) {
      errors.end_time = 'Čas do musí být později než čas od.';
    }
    if (programBlockProgramIds.length === 0) {
      errors.program_ids = 'Vyberte alespoň jeden aktivní program.';
    }
    setProgramBlockFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      toast.error('Zkontrolujte zvýrazněná pole.');
      return;
    }
    try {
      await axios.post(`${API}/availability-unified/exceptions`, {
        scope_type: 'program',
        scope_id: programBlockProgramIds[0],
        program_ids: programBlockProgramIds,
        date_from: programBlockForm.date_from,
        date_to: programBlockForm.date_to,
        start_time: programBlockForm.start_time || null,
        end_time: programBlockForm.end_time || null,
        reason: programBlockForm.reason || null,
      });
      toast.success(programBlockProgramIds.length > 1 ? 'Programové blokace vytvořeny' : 'Programová blokace vytvořena');
      setShowProgramBlock(false);
      setProgramBlockFieldErrors({});
      setProgramBlockProgramIds([]);
      setProgramBlockForm({ date_from: '', date_to: '', start_time: '', end_time: '', reason: '' });
      doFetchWeek(selectedProgram, weekStart);
    } catch (err) { toast.error(err.response?.data?.detail || 'Chyba'); }
  };

  const removeException = async () => {    if (!slotDetail) return;
    const [startTime] = slotDetail.slot.time.split('-');
    const match = exceptions.find(e => e.date === slotDetail.date && e.start_time === startTime);
    if (!match) { toast.error('Výjimka nenalezena'); return; }
    try {
      await axios.delete(`${API}/availability-unified/exceptions/${match.id}`);
      toast.success('Slot obnoven');
      setShowExceptionDialog(false);
      doFetchWeek(selectedProgram, weekStart);
    } catch { toast.error('Chyba'); }
  };

  const renderCalendarCell = (dayIndex, hour) => {
    const dateStr = fmtDate(weekDays[dayIndex]);
    const slot = getCellStatus(dateStr, hour);

    if (!slot) {
      return <div className="h-8 bg-gray-50 border border-gray-100" />;
    }

    const bg = STATUS_COLORS[slot.status] || 'bg-gray-50';
    const canClick = slot.status === 'available' || slot.status === 'blocked_exception';

    return (
      <div
        className={`h-8 border ${bg} relative group ${canClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default'} transition-colors`}
        title={slot.reason || STATUS_LABELS[slot.status] || slot.status}
        onClick={() => canClick && handleCellClick(dateStr, slot)}
        data-testid={`pcal-cell-${dayIndex}-${hour}`}
      >
        <div className="absolute inset-0 flex items-center justify-center text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity">
          {STATUS_LABELS[slot.status] || slot.status}
        </div>
      </div>
    );
  };

  const content = (
      <div className="space-y-6" data-testid="program-availability-page">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dostupnost</h1>
            <p className="text-sm text-gray-500 mt-1">Programová dostupnost a jednorázové výjimky</p>
          </div>
          {/* Quick availability actions — same as personal calendar; useful for
              institutions that don't use program collisions. */}
          <div className="flex gap-2 flex-wrap" data-testid="program-availability-quick-actions">
            <Button
              onClick={() => onRequestPersonalAction && onRequestPersonalAction('recurring')}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              size="sm"
              data-testid="program-add-recurring-btn"
            >
              <Plus className="w-4 h-4 mr-1" /> Pravidelné bloky
            </Button>
            <Button
              onClick={() => onRequestPersonalAction && onRequestPersonalAction('oneoff')}
              variant="outline"
              size="sm"
              className="border-amber-300 text-amber-700 hover:bg-amber-50"
              data-testid="program-add-oneoff-btn"
            >
              <CalendarPlus className="w-4 h-4 mr-1" /> Jednorázový čas
            </Button>
            <Button
              onClick={openProgramBlockDialog}
              variant="outline"
              size="sm"
              className="border-red-300 text-red-600 hover:bg-red-50"
              data-testid="program-add-timeoff-btn"
            >
              <Ban className="w-4 h-4 mr-1" /> Přidat blokaci
            </Button>
          </div>
        </div>

        {/* Selector + View toggle in one row */}
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex items-center gap-2 border border-gray-200 rounded-lg p-1 shrink-0" data-testid="view-toggle">
              <button onClick={() => onViewModeChange('program')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${viewMode === 'program' ? 'bg-slate-800 text-white' : 'text-gray-500 hover:text-gray-700'}`} data-testid="view-mode-program">
                Programová
              </button>
              <button onClick={() => onViewModeChange('personal')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${viewMode === 'personal' ? 'bg-slate-800 text-white' : 'text-gray-500 hover:text-gray-700'}`} data-testid="view-mode-personal">
                Osobní
              </button>
            </div>
            <div className="flex items-center gap-2 flex-1">
              <Label className="text-sm font-medium whitespace-nowrap">Program:</Label>
              <Select value={selectedProgram || 'none'} onValueChange={v => { if (v !== 'none') { setSelectedProgram(v); setProgramSelectorError(''); } }}>
                <SelectTrigger className={`w-64 ${programSelectorError ? FIELD_ERROR_CLASS : ''}`} data-testid="select-program" aria-invalid={Boolean(programSelectorError)}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {programs.map(p => <SelectItem key={p.id} value={p.id}>{p.name_cs}</SelectItem>)}
                </SelectContent>
              </Select>
              <FieldError message={programSelectorError} />
            </div>
          </div>
        </Card>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs flex-wrap">
          {Object.entries(STATUS_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5">
              <div className={`w-4 h-4 rounded border ${STATUS_COLORS[key]}`} />
              <span className="text-gray-600">{label}</span>
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2" data-testid="program-availability-summary">
          <Card className="p-4 md:p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-emerald-600" />
                <h2 className="font-semibold text-slate-900">Pravidelná dostupnost programu</h2>
              </div>
            </div>
            {!selectedProgramData ? (
              <p className="text-sm text-gray-400">Vyberte program.</p>
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">Dny</p>
                  <div className="flex flex-wrap gap-2">
                    {(selectedProgramData.available_days || []).length === 0 ? (
                      <span className="text-sm text-gray-400">Žádné dny nejsou nastavené.</span>
                    ) : (
                      (selectedProgramData.available_days || []).map(day => (
                        <Badge key={day} className="bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-50">
                          {DAY_NAMES[day] || day}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">Časy</p>
                  <div className="flex flex-wrap gap-2">
                    {(selectedProgramData.time_blocks || []).length === 0 ? (
                      <span className="text-sm text-gray-400">Žádné časy nejsou nastavené.</span>
                    ) : (
                      (selectedProgramData.time_blocks || []).map(block => (
                        <Badge key={block} variant="secondary">{block}</Badge>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}
          </Card>

          <Card className="p-4 md:p-6 space-y-4" data-testid="program-exception-summary">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Ban className="w-5 h-5 text-red-500" />
                <h2 className="font-semibold text-slate-900">Programové blokace / výjimky</h2>
              </div>
            </div>
            {activeProgramExceptionGroups.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <Ban className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Žádné aktivní programové blokace.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {activeProgramExceptionGroups.map(group => (
                  <div key={group.key} className="p-3 bg-red-50 border border-red-200 rounded-lg" data-testid="program-exception-group">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                      <div>
                        <p className="font-medium text-sm text-slate-900">
                          {group.date}
                          {group.start_time && group.end_time ? ` (${group.start_time} – ${group.end_time})` : ' (celý den)'}
                        </p>
                        {group.reason && <p className="text-xs text-red-600 mt-0.5">{group.reason}</p>}
                      </div>
                      <Badge variant="outline" className="shrink-0 border-red-200 text-red-700">
                        {group.programIds.length} program{group.programIds.length === 1 ? '' : 'y/ů'}
                      </Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {group.programIds.map(programId => (
                        <Badge key={programId} variant="secondary" className="max-w-full">
                          <span className="truncate max-w-[240px]">{programNameById(programId)}</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Week Calendar */}
        <Card className="p-0 overflow-hidden" data-testid="program-week-calendar">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <Button variant="ghost" size="sm" onClick={prevWeek}><ChevronLeft className="w-4 h-4" /></Button>
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-semibold text-slate-900">
                {weekDays[0].toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long' })} – {weekDays[6].toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })}
              </h3>
              <Button variant="outline" size="sm" onClick={goToday} className="text-xs h-7">
                <CalendarDays className="w-3 h-3 mr-1" /> Dnes
              </Button>
            </div>
            <Button variant="ghost" size="sm" onClick={nextWeek}><ChevronRight className="w-4 h-4" /></Button>
          </div>

          {loading ? (
            <div className="text-center py-12"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-slate-800 mx-auto" /></div>
          ) : (
            <div className="overflow-x-auto">
              <div className="min-w-[640px]">
                {/* Day headers */}
                <div className="grid grid-cols-[60px_repeat(7,1fr)] border-b">
                  <div className="p-2 text-xs text-gray-400 text-center" />
                  {weekDays.map((d, i) => {
                    const today = isToday(d);
                    return (
                      <div key={i} className={`p-2 text-center border-l ${today ? 'bg-slate-800 text-white' : ''}`}>
                        <div className="text-xs font-medium">{DAY_SHORT[i]}</div>
                        <div className={`text-lg font-bold ${today ? 'text-white' : 'text-slate-900'}`}>{d.getDate()}</div>
                      </div>
                    );
                  })}
                </div>

                {/* Hour rows */}
                {HOURS.map(hour => (
                  <div key={hour} className="grid grid-cols-[60px_repeat(7,1fr)]">
                    <div className="p-1 text-xs text-gray-400 text-right pr-2 flex items-center justify-end">{hour}:00</div>
                    {Array.from({ length: 7 }, (_, i) => (
                      <div key={i} className="border-l">{renderCalendarCell(i, hour)}</div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Exception dialog */}
        <Dialog open={showExceptionDialog} onOpenChange={setShowExceptionDialog}>
          <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-md" aria-describedby="exc-desc">
            <DialogHeader>
              <DialogTitle>{slotDetail?.slot?.status === 'blocked_exception' ? 'Obnovit dostupnost' : 'Uzavřít slot'}</DialogTitle>
              <p id="exc-desc" className="text-sm text-gray-500 mt-1">{slotDetail?.date} {slotDetail?.slot?.time}</p>
            </DialogHeader>
            {slotDetail?.slot?.status === 'available' && (
              <div className="space-y-3 py-2">
                <p className="text-sm text-gray-600">Označit slot jako jednorázově nedostupný?</p>
                <div>
                  <Label className="text-sm text-gray-500">Důvod (volitelné)</Label>
                  <Input value={exceptionReason} onChange={e => setExceptionReason(e.target.value)} placeholder="Např. údržba, svátek..." className="mt-1" data-testid="exception-reason" />
                </div>
                <div className="flex gap-2">
                  <Button onClick={createException} className="flex-1 bg-red-600 hover:bg-red-700 text-white" data-testid="confirm-exception"><Ban className="w-4 h-4 mr-2" /> Uzavřít</Button>
                  <Button variant="outline" onClick={() => setShowExceptionDialog(false)} className="flex-1">Zrušit</Button>
                </div>
              </div>
            )}
            {slotDetail?.slot?.status === 'blocked_exception' && (
              <div className="space-y-3 py-2">
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700 font-medium">Aktuálně uzavřeno</p>
                  {slotDetail.slot.reason && <p className="text-xs text-red-600 mt-1">{slotDetail.slot.reason}</p>}
                </div>
                <div className="flex gap-2">
                  <Button onClick={removeException} className="flex-1 bg-green-600 hover:bg-green-700 text-white" data-testid="restore-slot"><CheckCircle className="w-4 h-4 mr-2" /> Obnovit</Button>
                  <Button variant="outline" onClick={() => setShowExceptionDialog(false)} className="flex-1">Zrušit</Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Program block dialog (program-scoped exception) */}
        <Dialog open={showProgramBlock} onOpenChange={setShowProgramBlock}>
          <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-md" aria-describedby="pblock-desc">
            <DialogHeader>
              <DialogTitle>Přidat programovou blokaci</DialogTitle>
              <p id="pblock-desc" className="text-sm text-gray-500 mt-1">
                Uzavře vybrané aktivní programy ve zvoleném období.
              </p>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-sm text-gray-500">Datum od</Label>
                  <Input type="date" value={programBlockForm.date_from} onChange={e => { setProgramBlockForm(f => ({ ...f, date_from: e.target.value, date_to: f.date_to || e.target.value })); setProgramBlockFieldErrors(prev => ({ ...prev, date_from: undefined, date_to: undefined })); }} className={`mt-1 ${programBlockFieldErrors.date_from ? FIELD_ERROR_CLASS : ''}`} aria-invalid={Boolean(programBlockFieldErrors.date_from)} data-testid="pblock-date-from" />
                  <FieldError message={programBlockFieldErrors.date_from} />
                </div>
                <div>
                  <Label className="text-sm text-gray-500">Datum do</Label>
                  <Input type="date" value={programBlockForm.date_to} onChange={e => { setProgramBlockForm(f => ({ ...f, date_to: e.target.value })); setProgramBlockFieldErrors(prev => ({ ...prev, date_to: undefined })); }} className={`mt-1 ${programBlockFieldErrors.date_to ? FIELD_ERROR_CLASS : ''}`} aria-invalid={Boolean(programBlockFieldErrors.date_to)} data-testid="pblock-date-to" />
                  <FieldError message={programBlockFieldErrors.date_to} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-sm text-gray-500">Od (volitelné)</Label>
                  <Input type="time" value={programBlockForm.start_time} onChange={e => { setProgramBlockForm(f => ({ ...f, start_time: e.target.value })); setProgramBlockFieldErrors(prev => ({ ...prev, start_time: undefined, end_time: undefined })); }} className={`mt-1 ${programBlockFieldErrors.start_time ? FIELD_ERROR_CLASS : ''}`} aria-invalid={Boolean(programBlockFieldErrors.start_time)} data-testid="pblock-start" />
                </div>
                <div>
                  <Label className="text-sm text-gray-500">Do (volitelné)</Label>
                  <Input type="time" value={programBlockForm.end_time} onChange={e => { setProgramBlockForm(f => ({ ...f, end_time: e.target.value })); setProgramBlockFieldErrors(prev => ({ ...prev, start_time: undefined, end_time: undefined })); }} className={`mt-1 ${programBlockFieldErrors.end_time ? FIELD_ERROR_CLASS : ''}`} aria-invalid={Boolean(programBlockFieldErrors.end_time)} data-testid="pblock-end" />
                </div>
              </div>
              <FieldError message={programBlockFieldErrors.start_time || programBlockFieldErrors.end_time} />
              <p className="text-xs text-gray-400">Nechte čas prázdný pro blokaci celého dne.</p>
              <div>
                <Label className="text-sm text-gray-500">Programy</Label>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      className={`mt-1 w-full justify-between ${programBlockFieldErrors.program_ids ? FIELD_ERROR_CLASS : ''}`}
                      aria-invalid={Boolean(programBlockFieldErrors.program_ids)}
                      data-testid="pblock-programs-trigger"
                    >
                      <span className="truncate">
                        {programBlockProgramIds.length === 0
                          ? 'Vyberte aktivní programy'
                          : `${programBlockProgramIds.length} vybráno`}
                      </span>
                      <ChevronDown className="w-4 h-4 ml-2 shrink-0" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-80 max-h-72 overflow-y-auto" align="start">
                    {blockablePrograms.length === 0 ? (
                      <div className="px-2 py-1.5 text-sm text-gray-500">Žádný aktivní program</div>
                    ) : (
                      blockablePrograms.map(program => (
                        <DropdownMenuCheckboxItem
                          key={program.id}
                          checked={programBlockProgramIds.includes(program.id)}
                          onCheckedChange={() => toggleProgramBlockProgram(program.id)}
                          onSelect={e => e.preventDefault()}
                          data-testid={`pblock-program-${program.id}`}
                        >
                          <span className="truncate">{program.name_cs}</span>
                        </DropdownMenuCheckboxItem>
                      ))
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
                {programBlockProgramIds.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {programBlockProgramIds.map(programId => (
                      <Badge key={programId} variant="secondary" className="max-w-full gap-1 pr-1">
                        <span className="truncate max-w-[220px]">{programNameById(programId)}</span>
                        <button
                          type="button"
                          onClick={() => toggleProgramBlockProgram(programId)}
                          className="rounded hover:bg-slate-200"
                          aria-label={`Odebrat ${programNameById(programId)}`}
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                <FieldError message={programBlockFieldErrors.program_ids} />
              </div>
              <div>
                <Label className="text-sm text-gray-500">Důvod (volitelné)</Label>
                <Input value={programBlockForm.reason} onChange={e => setProgramBlockForm(f => ({ ...f, reason: e.target.value }))} placeholder="Např. výjezd, údržba..." className="mt-1" data-testid="pblock-reason" />
              </div>
              <div className="flex gap-2">
                <Button onClick={createProgramBlock} className="flex-1 bg-red-600 hover:bg-red-700 text-white" data-testid="confirm-program-block"><Ban className="w-4 h-4 mr-2" /> Vytvořit blokaci</Button>
                <Button variant="outline" onClick={() => setShowProgramBlock(false)} className="flex-1">Zrušit</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
  );
  return embedded ? content : <AdminLayout>{content}</AdminLayout>;
};
