import React, { useState, useEffect, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { ChevronLeft, ChevronRight, Ban, CheckCircle, Clock, Users, AlertTriangle, Lock, CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';
import { LecturerAvailabilityPage } from './LecturerAvailabilityPage';

const DAY_SHORT = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];
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

  // If personal view, render the original LecturerAvailabilityPage with view toggle
  if (viewMode === 'personal') {
    return <LecturerAvailabilityPage viewToggle={viewMode} onViewToggle={setViewMode} embedded={embedded} />;
  }

  return <ProgramAvailabilityView viewMode={viewMode} onViewModeChange={setViewMode} embedded={embedded} />;
};

// ============ Program Availability View ============
const ProgramAvailabilityView = ({ viewMode, onViewModeChange, embedded = false }) => {
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const [programs, setPrograms] = useState([]);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [weekSlots, setWeekSlots] = useState({});
  const [loading, setLoading] = useState(false);
  const [slotDetail, setSlotDetail] = useState(null);
  const [showExceptionDialog, setShowExceptionDialog] = useState(false);
  const [exceptionReason, setExceptionReason] = useState('');
  const [exceptions, setExceptions] = useState([]);

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
    } catch { setExceptions([]); }
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

  const removeException = async () => {
    if (!slotDetail) return;
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
              <Select value={selectedProgram || 'none'} onValueChange={v => v !== 'none' && setSelectedProgram(v)}>
                <SelectTrigger className="w-64" data-testid="select-program"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {programs.map(p => <SelectItem key={p.id} value={p.id}>{p.name_cs}</SelectItem>)}
                </SelectContent>
              </Select>
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
      </div>
  );
  return embedded ? content : <AdminLayout>{content}</AdminLayout>;
};
