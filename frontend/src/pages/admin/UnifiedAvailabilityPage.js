import React, { useState, useEffect, useContext, useCallback } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { ChevronLeft, ChevronRight, Ban, CheckCircle, Clock, Users, X, AlertTriangle, Lock, CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

import { API } from '../../config/api';

const DAY_NAMES = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle'];
const DAY_SHORT = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(date.setDate(diff));
}

function formatDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const STATUS_COLORS = {
  available: 'bg-green-100 border-green-300 text-green-800 hover:bg-green-200',
  booked: 'bg-slate-200 border-slate-400 text-slate-700',
  blocked_exception: 'bg-red-100 border-red-300 text-red-700 hover:bg-red-200',
  blocked_lecturer: 'bg-amber-100 border-amber-300 text-amber-800',
  blocked_room: 'bg-purple-100 border-purple-300 text-purple-800',
  blocked_parallel: 'bg-orange-100 border-orange-300 text-orange-800',
  blocked_program: 'bg-rose-100 border-rose-300 text-rose-800',
  outside_base_availability: 'bg-gray-50 border-gray-200 text-gray-400',
};

const STATUS_LABELS = {
  available: 'Dostupný',
  booked: 'Obsazeno',
  blocked_exception: 'Uzavřeno',
  blocked_lecturer: 'Lektor nedostupný',
  blocked_room: 'Místnost obsazena',
  blocked_parallel: 'Paralelní blokace',
  blocked_program: 'Blokace programu',
  outside_base_availability: 'Mimo rozvrh',
};

const STATUS_ICONS = {
  available: CheckCircle,
  booked: CalendarDays,
  blocked_exception: Ban,
  blocked_lecturer: Users,
  blocked_room: Lock,
  blocked_parallel: AlertTriangle,
  blocked_program: AlertTriangle,
  outside_base_availability: Clock,
};

export const UnifiedAvailabilityPage = () => {
  const { user } = useContext(AuthContext);
  const [viewMode, setViewMode] = useState('program'); // 'program' | 'personal'
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const [programs, setPrograms] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [selectedLecturer, setSelectedLecturer] = useState(null);
  const [weekSlots, setWeekSlots] = useState({}); // { "2026-04-14": [...slots] }
  const [loading, setLoading] = useState(false);
  const [slotDetail, setSlotDetail] = useState(null); // {date, slot}
  const [showExceptionDialog, setShowExceptionDialog] = useState(false);
  const [exceptionReason, setExceptionReason] = useState('');
  const [exceptions, setExceptions] = useState([]);

  useEffect(() => { fetchPrograms(); fetchTeam(); }, []);

  const fetchPrograms = async () => {
    try {
      const res = await axios.get(`${API}/programs`);
      const active = (res.data || []).filter(p => p.status !== 'archived');
      setPrograms(active);
      if (active.length > 0) {
        setSelectedProgram(active[0].id);
      }
    } catch { /* */ }
  };

  const fetchTeam = async () => {
    try {
      const res = await axios.get(`${API}/team`);
      setTeamMembers(res.data || []);
    } catch { /* */ }
  };

  // Fetch week data when dependencies change — use a ref to get latest values
  const selectedProgramRef = React.useRef(selectedProgram);
  const selectedLecturerRef = React.useRef(selectedLecturer);
  const viewModeRef = React.useRef(viewMode);
  const weekStartRef = React.useRef(weekStart);
  
  React.useEffect(() => { selectedProgramRef.current = selectedProgram; }, [selectedProgram]);
  React.useEffect(() => { selectedLecturerRef.current = selectedLecturer; }, [selectedLecturer]);
  React.useEffect(() => { viewModeRef.current = viewMode; }, [viewMode]);
  React.useEffect(() => { weekStartRef.current = weekStart; }, [weekStart]);

  useEffect(() => {
    if (viewMode === 'program' && selectedProgram) doFetchWeek(selectedProgram, null, viewMode, weekStart);
    else if (viewMode === 'personal' && selectedLecturer) doFetchWeek(null, selectedLecturer, viewMode, weekStart);
  }, [weekStart, selectedProgram, selectedLecturer, viewMode]);

  const doFetchWeek = async (prog, lect, mode, ws) => {
    setLoading(true);
    const data = {};
    const promises = [];

    for (let i = 0; i < 7; i++) {
      const d = new Date(ws);
      d.setDate(d.getDate() + i);
      const dateStr = formatDate(d);

      if (mode === 'program' && prog) {
        promises.push(
          axios.get(`${API}/availability-unified/program/${prog}/slots?date=${dateStr}`)
            .then(res => { data[dateStr] = res.data.slots || []; })
            .catch(() => { data[dateStr] = []; })
        );
      } else if (mode === 'personal' && lect) {
        promises.push(
          axios.get(`${API}/availability-unified/lecturer/${lect}/slots?date=${dateStr}`)
            .then(res => { data[dateStr] = res.data.slots || []; })
            .catch(() => { data[dateStr] = []; })
        );
      }
    }

    await Promise.all(promises);
    setWeekSlots(data);
    setLoading(false);

    const scopeType = mode === 'program' ? 'program' : 'lecturer';
    const scopeId = mode === 'program' ? prog : lect;
    if (scopeId) {
      try {
        const res = await axios.get(`${API}/availability-unified/exceptions?scope_type=${scopeType}&scope_id=${scopeId}`);
        setExceptions(res.data || []);
      } catch { setExceptions([]); }
    }
  };

  const prevWeek = () => { const d = new Date(weekStart); d.setDate(d.getDate() - 7); setWeekStart(d); };
  const nextWeek = () => { const d = new Date(weekStart); d.setDate(d.getDate() + 7); setWeekStart(d); };
  const goToday = () => setWeekStart(getMonday(new Date()));

  const handleSlotClick = (dateStr, slot) => {
    setSlotDetail({ date: dateStr, slot });
    if (slot.status === 'available') {
      setExceptionReason('');
      setShowExceptionDialog(true);
    } else if (slot.status === 'blocked_exception') {
      // Show option to remove exception
      setShowExceptionDialog(true);
      setExceptionReason('');
    }
  };

  const createException = async () => {
    if (!slotDetail) return;
    const scopeType = viewMode === 'program' ? 'program' : 'lecturer';
    const scopeId = viewMode === 'program' ? selectedProgram : selectedLecturer;
    const [startTime, endTime] = slotDetail.slot.time.split('-');
    try {
      await axios.post(`${API}/availability-unified/exceptions`, {
        scope_type: scopeType,
        scope_id: scopeId,
        date: slotDetail.date,
        start_time: startTime,
        end_time: endTime,
        reason: exceptionReason || null,
      });
      toast.success('Slot uzavřen');
      setShowExceptionDialog(false);
      doFetchWeek(selectedProgram, selectedLecturer, viewMode, weekStart);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba');
    }
  };

  const removeException = async () => {
    if (!slotDetail) return;
    const [startTime] = slotDetail.slot.time.split('-');
    // Find the matching exception
    const match = exceptions.find(e =>
      e.date === slotDetail.date && e.start_time === startTime
    );
    if (!match) { toast.error('Výjimka nenalezena'); return; }
    try {
      await axios.delete(`${API}/availability-unified/exceptions/${match.id}`);
      toast.success('Výjimka odstraněna — slot obnoven');
      setShowExceptionDialog(false);
      doFetchWeek(selectedProgram, selectedLecturer, viewMode, weekStart);
    } catch { toast.error('Chyba při odstraňování'); }
  };

  const getDaysOfWeek = () => {
    const days = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      days.push({ date: d, dateStr: formatDate(d), dayName: DAY_SHORT[i], dayFull: DAY_NAMES[i] });
    }
    return days;
  };

  const weekDays = getDaysOfWeek();
  const isToday = (dateStr) => formatDate(new Date()) === dateStr;

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h1 className="text-2xl font-bold text-slate-900">Dostupnost</h1>
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'program' ? 'default' : 'outline'}
              onClick={() => setViewMode('program')}
              className={viewMode === 'program' ? 'bg-slate-800 text-white' : ''}
              size="sm"
              data-testid="view-mode-program"
            >
              Programová
            </Button>
            <Button
              variant={viewMode === 'personal' ? 'default' : 'outline'}
              onClick={() => setViewMode('personal')}
              className={viewMode === 'personal' ? 'bg-slate-800 text-white' : ''}
              size="sm"
              data-testid="view-mode-personal"
            >
              Osobní
            </Button>
          </div>
        </div>

        {/* Selector */}
        <Card className="p-4">
          {viewMode === 'program' ? (
            <div>
              <Label className="text-sm text-gray-500 mb-1 block">Program</Label>
              <Select value={selectedProgram || 'none'} onValueChange={v => v !== 'none' && setSelectedProgram(v)}>
                <SelectTrigger data-testid="select-program"><SelectValue placeholder="Vyberte program..." /></SelectTrigger>
                <SelectContent>
                  {programs.map(p => <SelectItem key={p.id} value={p.id}>{p.name_cs}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div>
              <Label className="text-sm text-gray-500 mb-1 block">Lektor</Label>
              <Select value={selectedLecturer || ''} onValueChange={setSelectedLecturer}>
                <SelectTrigger data-testid="select-lecturer"><SelectValue placeholder="Vyberte lektora..." /></SelectTrigger>
                <SelectContent>
                  {teamMembers.filter(m => ['lektor', 'edukator', 'admin', 'spravce'].includes(m.role) && m.status === 'active').map(m => (
                    <SelectItem key={m.id} value={m.id}>{m.first_name} {m.last_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </Card>

        {/* Week navigation */}
        <div className="flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={prevWeek}><ChevronLeft className="w-4 h-4" /></Button>
          <div className="text-center">
            <p className="text-sm font-medium text-slate-900">
              {weekDays[0].date.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long' })} — {weekDays[6].date.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            <button onClick={goToday} className="text-xs text-[#4A6FA5] hover:underline">Dnes</button>
          </div>
          <Button variant="outline" size="sm" onClick={nextWeek}><ChevronRight className="w-4 h-4" /></Button>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-2 text-xs">
          {Object.entries(STATUS_LABELS).filter(([k]) => k !== 'outside_base_availability').map(([key, label]) => (
            <span key={key} className={`px-2 py-1 rounded border ${STATUS_COLORS[key]}`}>{label}</span>
          ))}
        </div>

        {/* Calendar grid */}
        {loading ? (
          <div className="text-center py-12"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-slate-800 mx-auto" /></div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-2">
            {weekDays.map(day => {
              const slots = weekSlots[day.dateStr] || [];
              const hasSlots = slots.length > 0 && !(slots.length === 1 && slots[0].status === 'outside_base_availability');
              return (
                <Card key={day.dateStr} className={`p-2 min-h-[120px] ${isToday(day.dateStr) ? 'ring-2 ring-[#4A6FA5]' : ''}`} data-testid={`day-${day.dateStr}`}>
                  <div className="text-center mb-2">
                    <p className="text-xs font-medium text-gray-500">{day.dayName}</p>
                    <p className={`text-sm font-bold ${isToday(day.dateStr) ? 'text-[#4A6FA5]' : 'text-slate-900'}`}>
                      {day.date.getDate()}.{day.date.getMonth() + 1}.
                    </p>
                  </div>
                  {!hasSlots ? (
                    <p className="text-xs text-gray-400 text-center py-2">Žádné bloky</p>
                  ) : (
                    <div className="space-y-1">
                      {slots.filter(s => s.status !== 'outside_base_availability').map((slot, idx) => {
                        const Icon = STATUS_ICONS[slot.status] || Clock;
                        const canClick = slot.status === 'available' || slot.status === 'blocked_exception';
                        return (
                          <button
                            key={idx}
                            onClick={() => canClick && handleSlotClick(day.dateStr, slot)}
                            className={`w-full text-left px-1.5 py-1 rounded border text-xs transition-colors ${STATUS_COLORS[slot.status]} ${canClick ? 'cursor-pointer' : 'cursor-default'}`}
                            title={slot.reason || STATUS_LABELS[slot.status]}
                            data-testid={`slot-${day.dateStr}-${idx}`}
                          >
                            <div className="flex items-center gap-1">
                              <Icon className="w-3 h-3 shrink-0" />
                              <span className="truncate">{slot.time.split('-')[0]}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Exception dialog */}
        <Dialog open={showExceptionDialog} onOpenChange={setShowExceptionDialog}>
          <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-md" aria-describedby="exc-desc">
            <DialogHeader>
              <DialogTitle>
                {slotDetail?.slot?.status === 'blocked_exception' ? 'Obnovit dostupnost' : 'Uzavřít slot'}
              </DialogTitle>
              <p id="exc-desc" className="text-sm text-gray-500 mt-1">
                {slotDetail?.date} {slotDetail?.slot?.time}
              </p>
            </DialogHeader>

            {slotDetail?.slot?.status === 'available' && (
              <div className="space-y-3 py-2">
                <p className="text-sm text-gray-600">Označit tento slot jako jednorázově nedostupný?</p>
                <div>
                  <Label className="text-sm text-gray-500">Důvod (volitelné)</Label>
                  <Input
                    value={exceptionReason}
                    onChange={e => setExceptionReason(e.target.value)}
                    placeholder="Např. údržba, svátek..."
                    className="mt-1"
                    data-testid="exception-reason"
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={createException} className="flex-1 bg-red-600 hover:bg-red-700 text-white" data-testid="confirm-exception">
                    <Ban className="w-4 h-4 mr-2" /> Uzavřít
                  </Button>
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
                  <Button onClick={removeException} className="flex-1 bg-green-600 hover:bg-green-700 text-white" data-testid="restore-slot">
                    <CheckCircle className="w-4 h-4 mr-2" /> Obnovit dostupnost
                  </Button>
                  <Button variant="outline" onClick={() => setShowExceptionDialog(false)} className="flex-1">Zrušit</Button>
                </div>
              </div>
            )}

            {slotDetail?.slot?.status && !['available', 'blocked_exception'].includes(slotDetail.slot.status) && (
              <div className="space-y-3 py-2">
                <div className="p-3 bg-gray-50 border rounded-lg">
                  <p className="text-sm font-medium">{STATUS_LABELS[slotDetail.slot.status]}</p>
                  {slotDetail.slot.reason && <p className="text-xs text-gray-600 mt-1">{slotDetail.slot.reason}</p>}
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
};
