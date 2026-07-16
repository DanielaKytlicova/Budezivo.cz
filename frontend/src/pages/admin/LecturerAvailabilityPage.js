import React, { useState, useEffect, useContext, useCallback } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Checkbox } from '../../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Trash2, ChevronLeft, ChevronRight, Clock, Ban, Edit2, Info, CalendarDays, CalendarPlus, RefreshCw, Unlink, ExternalLink } from 'lucide-react';
import axios from 'axios';
import { ConnectedGuideDialog } from '../../components/calendar/ConnectedGuideDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ucetni/pokladni have no personal availability → no personal calendar.
const PERSONAL_CALENDAR_ROLES = ['admin', 'spravce', 'edukator', 'lektor', 'produkcni'];

const DAY_NAMES = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle'];
const DAY_SHORT = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];
const HOURS = Array.from({ length: 12 }, (_, i) => i + 7); // 7:00 - 18:00

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(date.setDate(diff));
}

function formatDate(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function timeToMinutes(t) {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + (m || 0);
}

export const LecturerAvailabilityPage = ({ viewToggle, onViewToggle, embedded = false, autoOpenAction = null, onAutoOpenConsumed }) => {
  const { user, token } = useContext(AuthContext);
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const [recurring, setRecurring] = useState([]);
  const [oneOffs, setOneOffs] = useState([]);
  const [timeOffs, setTimeOffs] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedLecturer, setSelectedLecturer] = useState(null);
  const [loading, setLoading] = useState(true);

  // Dialogs
  const [showAddRecurring, setShowAddRecurring] = useState(false);
  const [showAddOneOff, setShowAddOneOff] = useState(false);
  const [showAddTimeOff, setShowAddTimeOff] = useState(false);
  const [editingRecurring, setEditingRecurring] = useState(null);
  const [editingTimeOff, setEditingTimeOff] = useState(null);
  
  // Outlook integration state
  const [outlookStatus, setOutlookStatus] = useState({ connected: false });
  const [outlookBlocks, setOutlookBlocks] = useState([]);
  const [outlookSyncing, setOutlookSyncing] = useState(false);

  // Google Calendar integration state
  const [googleStatus, setGoogleStatus] = useState({ connected: false, configured: false });
  const [googleBlocks, setGoogleBlocks] = useState([]);
  const [googleSyncing, setGoogleSyncing] = useState(false);
  const [googleSyncResult, setGoogleSyncResult] = useState(null);
  const [showGoogleDisconnect, setShowGoogleDisconnect] = useState(false);

  // Phase C — "connected" guide dialog
  const [connectedGuide, setConnectedGuide] = useState(null); // 'google' | 'outlook' | null

  // Forms
  const [recurringForm, setRecurringForm] = useState({
    days_of_week: [],
    start_time: '08:00',
    end_time: '12:00',
  });
  const [oneOffForm, setOneOffForm] = useState({
    specific_date: '',
    start_time: '09:00',
    end_time: '12:00',
  });
  const [timeOffForm, setTimeOffForm] = useState({
    start_date: '',
    end_date: '',
    start_time: '',
    end_time: '',
    reason: '',
  });

  const isAdmin = ['admin', 'spravce'].includes(user?.role);
  const canPersonalCalendar = PERSONAL_CALENDAR_ROLES.includes(user?.role);
  const lecturerId = selectedLecturer || user?.id;

  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const weekStr = formatDate(weekStart);
      const params = selectedLecturer ? `?lecturer_id=${selectedLecturer}&week_start=${weekStr}` : `?week_start=${weekStr}`;
      const res = await axios.get(`${API}/lecturer-availability/week-view${params}`, { headers });
      setRecurring(res.data.recurring || []);
      setOneOffs(res.data.one_offs || []);
      setTimeOffs(res.data.time_offs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [weekStart, selectedLecturer, token]);

  const fetchTeam = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const res = await axios.get(`${API}/team`, { headers });
      setTeamMembers(res.data.filter(m => ['edukator', 'lektor', 'admin', 'spravce'].includes(m.role)));
    } catch (err) {
      console.error(err);
    }
  }, [isAdmin, token]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchTeam(); }, [fetchTeam]);

  // Auto-open a dialog when navigated here from the program-availability view's
  // quick-action buttons (task: surface block/one-off/recurring actions there too).
  useEffect(() => {
    if (!autoOpenAction) return;
    if (autoOpenAction === 'recurring') {
      setShowAddRecurring(true);
      setRecurringForm({ days_of_week: [], start_time: '08:00', end_time: '12:00' });
    } else if (autoOpenAction === 'oneoff') {
      setShowAddOneOff(true);
      setOneOffForm({ specific_date: '', start_time: '09:00', end_time: '12:00' });
    } else if (autoOpenAction === 'timeoff') {
      setShowAddTimeOff(true);
      setTimeOffForm({ start_date: '', end_date: '', start_time: '', end_time: '', reason: '' });
    }
    if (onAutoOpenConsumed) onAutoOpenConsumed();
  }, [autoOpenAction]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { fetchOutlookStatus(); }, [token]);
  useEffect(() => { if (outlookStatus.connected) fetchOutlookBlocks(); }, [weekStart, lecturerId, outlookStatus.connected]);
  useEffect(() => { fetchGoogleStatus(); }, [token]);
  useEffect(() => { if (googleStatus.connected) fetchGoogleBlocks(); }, [weekStart, lecturerId, googleStatus.connected]);

  // Listen for OAuth popup messages
  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data?.type === 'outlook_connected') {
        toast.success('Outlook kalendář připojen!');
        fetchOutlookStatus();
        fetchOutlookBlocks();
        setConnectedGuide('outlook');
      } else if (event.data?.type === 'outlook_error') {
        const raw = event.data.error || '';
        const aadsts = event.data.aadsts;
        let msg = raw || 'Připojení Outlooku se nezdařilo.';
        const low = raw.toLowerCase();
        if (low.includes('nakonfigurován') || low.includes('not configured')) {
          msg = 'Připojení Outlooku není nakonfigurováno (chybí přihlašovací údaje Microsoft).';
        } else if (aadsts === 'AADSTS50011' || low.includes('redirect')) {
          msg = 'Nesouhlasí přesměrovací adresa (redirect URI) v Microsoft Entra.';
        } else if (aadsts === 'AADSTS7000215' || aadsts === 'AADSTS7000222' || low.includes('invalid client secret') || low.includes('secret')) {
          msg = 'Neplatný nebo prošlý client secret aplikace Microsoft.';
        }
        toast.error(aadsts ? `${msg} (${aadsts})` : msg, { duration: 8000 });
      } else if (event.data?.type === 'google_connected') {
        toast.success('Google kalendář připojen!');
        fetchGoogleStatus();
        fetchGoogleBlocks();
        setConnectedGuide('google');
      } else if (event.data?.type === 'google_error') {
        toast.error(event.data.error || 'Chyba při připojení Google kalendáře');
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const fetchOutlookStatus = async () => {
    try {
      const res = await axios.get(`${API}/microsoft-calendar/status`, { headers });
      setOutlookStatus(res.data);
      if (res.data.connected) fetchOutlookBlocks();
    } catch (err) {
      console.error('Outlook status fetch failed');
    }
  };

  const fetchOutlookBlocks = async () => {
    try {
      const weekStr = formatDate(weekStart);
      const endStr = formatDate(new Date(weekStart.getTime() + 6 * 86400000));
      const params = lecturerId ? `?user_id=${lecturerId}&start=${weekStr}&end=${endStr}` : `?start=${weekStr}&end=${endStr}`;
      const res = await axios.get(`${API}/microsoft-calendar/blocks${params}`, { headers });
      setOutlookBlocks(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error('Outlook blocks fetch failed');
    }
  };

  const connectOutlook = async () => {
    try {
      const res = await axios.get(`${API}/microsoft-calendar/connect`, { headers });
      if (res.data.auth_url) {
        window.open(res.data.auth_url, 'outlook_auth', 'width=500,height=700');
      }
    } catch (err) {
      toast.error(formatApiError(err, 'Nepodařilo se zahájit připojení Outlooku'));
    }
  };

  const disconnectOutlook = async () => {
    try {
      await axios.post(`${API}/microsoft-calendar/disconnect`, {}, { headers });
      setOutlookStatus({ connected: false });
      setOutlookBlocks([]);
      toast.success('Outlook odpojen');
    } catch (err) {
      toast.error('Chyba při odpojování');
    }
  };

  const syncOutlook = async () => {
    setOutlookSyncing(true);
    try {
      const res = await axios.post(`${API}/microsoft-calendar/sync`, {}, { headers });
      toast.success(res.data.message || 'Synchronizováno');
      await fetchOutlookBlocks();
    } catch (err) {
      toast.error('Synchronizace selhala');
    } finally {
      setOutlookSyncing(false);
    }
  };

  const toggleBlockOverride = async (blockId) => {
    try {
      const res = await axios.post(`${API}/microsoft-calendar/blocks/${blockId}/override`, {}, { headers });
      toast.success(res.data.message);
      await fetchOutlookBlocks();
    } catch (err) {
      toast.error('Chyba při změně přepsání');
    }
  };

  // Single personal-page toggle: import busy events as blocks (+ auto-sync).
  const setOutlookImport = async (value) => {
    const prev = outlookStatus;
    setOutlookStatus(s => ({ ...s, import_enabled: value }));
    try {
      await axios.put(`${API}/microsoft-calendar/settings`, { import_enabled: value }, { headers });
      toast.success('Nastavení uloženo');
      if (value) syncOutlook();
    } catch (err) {
      setOutlookStatus(prev);
      toast.error(formatApiError(err, 'Nepodařilo se uložit nastavení'));
    }
  };

  const setGoogleImport = async (value) => {
    const prev = googleStatus;
    setGoogleStatus(s => ({ ...s, import_enabled: value, auto_sync_enabled: value }));
    try {
      await axios.put(`${API}/google-calendar/settings`, { import_enabled: value, auto_sync_enabled: value }, { headers });
      toast.success('Nastavení uloženo');
      if (value) syncGoogle();
    } catch (err) {
      setGoogleStatus(prev);
      toast.error(formatApiError(err, 'Nepodařilo se uložit nastavení'));
    }
  };

  // ── Google Calendar integration ─────────────────────────────────────
  // Surface the backend-provided detail (and status) for Google/Outlook OAuth
  // errors. 403 is intentionally treated as a plan gate elsewhere.
  const formatApiError = (err, fallback) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    if (detail) return status ? `${detail} (${status})` : detail;
    if (status === 503) return 'Služba Google kalendáře je dočasně nedostupná (503)';
    if (status === 404) return 'Zdroj nebyl nalezen (404)';
    return fallback;
  };

  const fetchGoogleStatus = async () => {
    try {
      const res = await axios.get(`${API}/google-calendar/status`, { headers });
      setGoogleStatus(res.data);
      if (res.data.connected) fetchGoogleBlocks();
    } catch (err) {
      // 403 = plan gate: stay silent so non-PRO+ users see nothing. Surface
      // other errors (e.g. 404/503) so the user knows what went wrong.
      if (err?.response?.status !== 403) {
        toast.error(formatApiError(err, 'Nepodařilo se načíst stav Google kalendáře'));
      }
      console.error('Google status fetch failed');
    }
  };

  const fetchGoogleBlocks = async () => {
    try {
      const weekStr = formatDate(weekStart);
      const endStr = formatDate(new Date(weekStart.getTime() + 6 * 86400000));
      const params = lecturerId ? `?user_id=${lecturerId}&start=${weekStr}&end=${endStr}` : `?start=${weekStr}&end=${endStr}`;
      const res = await axios.get(`${API}/google-calendar/blocks${params}`, { headers });
      setGoogleBlocks(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error('Google blocks fetch failed');
    }
  };

  const connectGoogle = async () => {
    try {
      const res = await axios.get(`${API}/google-calendar/connect`, { headers });
      if (res.data.auth_url) {
        window.open(res.data.auth_url, 'google_auth', 'width=500,height=700');
      }
    } catch (err) {
      toast.error(formatApiError(err, 'Nepodařilo se zahájit připojení Google kalendáře'));
    }
  };

  const disconnectGoogle = async (deleteExported) => {
    try {
      const res = await axios.post(`${API}/google-calendar/disconnect`, { delete_exported: !!deleteExported }, { headers });
      setGoogleStatus({ connected: false, configured: googleStatus.configured });
      setGoogleBlocks([]);
      setGoogleSyncResult(null);
      setShowGoogleDisconnect(false);
      toast.success(res.data?.message || 'Google kalendář odpojen');
    } catch (err) {
      toast.error(formatApiError(err, 'Chyba při odpojování'));
    }
  };

  const updateGoogleSetting = async (key, value) => {
    const prev = googleStatus;
    setGoogleStatus(s => ({ ...s, [key]: value }));
    try {
      await axios.put(`${API}/google-calendar/settings`, { [key]: value }, { headers });
      toast.success('Nastavení uloženo');
    } catch (err) {
      setGoogleStatus(prev);
      toast.error(formatApiError(err, 'Nepodařilo se uložit nastavení'));
      // If export needs the calendar.events scope, reflect reconnect requirement.
      if (err?.response?.status === 409) {
        setGoogleStatus(s => ({ ...s, needs_reconnect: true }));
      }
    }
  };

  const syncGoogle = async () => {
    setGoogleSyncing(true);
    try {
      const res = await axios.post(`${API}/google-calendar/sync`, {}, { headers });
      toast.success(res.data.message || 'Synchronizováno');
      setGoogleSyncResult(res.data);
      await fetchGoogleStatus();
      await fetchGoogleBlocks();
    } catch (err) {
      toast.error(formatApiError(err, 'Synchronizace selhala'));
    } finally {
      setGoogleSyncing(false);
    }
  };

  const toggleGoogleBlockOverride = async (blockId) => {
    try {
      const res = await axios.post(`${API}/google-calendar/blocks/${blockId}/override`, {}, { headers });
      toast.success(res.data.message);
      await fetchGoogleBlocks();
    } catch (err) {
      toast.error('Chyba při změně přepsání');
    }
  };

  const navigateWeek = (dir) => {
    const newDate = new Date(weekStart);
    newDate.setDate(newDate.getDate() + dir * 7);
    setWeekStart(newDate);
  };

  const goToCurrentWeek = () => {
    setWeekStart(getMonday(new Date()));
  };

  // CRUD handlers
  const handleAddRecurring = async () => {
    if (recurringForm.days_of_week.length === 0) {
      toast.error('Vyberte alespoň jeden den.');
      return;
    }
    try {
      const params = selectedLecturer ? `?lecturer_id=${selectedLecturer}` : '';
      await axios.post(`${API}/lecturer-availability/recurring${params}`, recurringForm, { headers });
      toast.success('Pravidelná dostupnost přidána.');
      setShowAddRecurring(false);
      setRecurringForm({ days_of_week: [], start_time: '08:00', end_time: '12:00' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při ukládání.');
    }
  };

  const handleUpdateRecurring = async () => {
    try {
      await axios.put(`${API}/lecturer-availability/recurring/${editingRecurring.id}`, {
        day_of_week: editingRecurring.day_of_week,
        start_time: editingRecurring.start_time,
        end_time: editingRecurring.end_time,
      }, { headers });
      toast.success('Dostupnost aktualizována.');
      setEditingRecurring(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při aktualizaci.');
    }
  };

  const handleAddOneOff = async () => {
    if (!oneOffForm.specific_date) {
      toast.error('Vyberte datum.');
      return;
    }
    try {
      const params = selectedLecturer ? `?lecturer_id=${selectedLecturer}` : '';
      await axios.post(`${API}/lecturer-availability/recurring${params}`, {
        days_of_week: [],
        start_time: oneOffForm.start_time,
        end_time: oneOffForm.end_time,
        specific_date: oneOffForm.specific_date,
      }, { headers });
      toast.success('Příležitostná dostupnost přidána.');
      setShowAddOneOff(false);
      setOneOffForm({ specific_date: '', start_time: '09:00', end_time: '12:00' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při ukládání.');
    }
  };

  const handleDeleteRecurring = async (id) => {
    try {
      await axios.delete(`${API}/lecturer-availability/recurring/${id}`, { headers });
      toast.success('Blok smazán.');
      fetchData();
    } catch (err) {
      toast.error('Chyba při mazání.');
    }
  };

  const handleAddTimeOff = async () => {
    if (!timeOffForm.start_date) {
      toast.error('Zadejte datum.');
      return;
    }
    try {
      const params = selectedLecturer ? `?lecturer_id=${selectedLecturer}` : '';
      const payload = {
        ...timeOffForm,
        end_date: timeOffForm.end_date || timeOffForm.start_date,
        start_time: timeOffForm.start_time || null,
        end_time: timeOffForm.end_time || null,
        reason: timeOffForm.reason || null,
      };
      await axios.post(`${API}/lecturer-availability/time-off${params}`, payload, { headers });
      toast.success('Blokace přidána.');
      setShowAddTimeOff(false);
      setTimeOffForm({ start_date: '', end_date: '', start_time: '', end_time: '', reason: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při ukládání.');
    }
  };

  const handleUpdateTimeOff = async () => {
    try {
      await axios.put(`${API}/lecturer-availability/time-off/${editingTimeOff.id}`, {
        start_date: editingTimeOff.start_date,
        end_date: editingTimeOff.end_date,
        start_time: editingTimeOff.start_time || null,
        end_time: editingTimeOff.end_time || null,
        reason: editingTimeOff.reason || null,
      }, { headers });
      toast.success('Blokace aktualizována.');
      setEditingTimeOff(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při aktualizaci.');
    }
  };

  const handleDeleteTimeOff = async (id) => {
    try {
      await axios.delete(`${API}/lecturer-availability/time-off/${id}`, { headers });
      toast.success('Blokace smazána.');
      fetchData();
    } catch (err) {
      toast.error('Chyba při mazání.');
    }
  };

  const toggleDay = (day) => {
    setRecurringForm(prev => ({
      ...prev,
      days_of_week: prev.days_of_week.includes(day)
        ? prev.days_of_week.filter(d => d !== day)
        : [...prev.days_of_week, day].sort()
    }));
  };

  // Calendar rendering
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });

  const getBlocksForDay = (dayIndex) => {
    const avail = recurring.filter(r => r.day_of_week === dayIndex);
    const dateStr = formatDate(weekDays[dayIndex]);
    // Include one-off blocks for this specific date
    const dayOneOffs = oneOffs.filter(o => o.specific_date === dateStr);
    const allAvail = [...avail, ...dayOneOffs];
    const offs = timeOffs.filter(t => t.start_date <= dateStr && t.end_date >= dateStr);
    
    // Outlook blocks for this day
    const dayOutlook = outlookBlocks.filter(b => {
      const bDate = new Date(b.start_time).toISOString().slice(0, 10);
      return bDate === dateStr;
    });
    // Google blocks for this day
    const dayGoogle = googleBlocks.filter(b => {
      const bDate = new Date(b.start_time).toISOString().slice(0, 10);
      return bDate === dateStr;
    });

    return { avail: allAvail, offs, outlook: dayOutlook, google: dayGoogle };
  };

  const renderCalendarCell = (dayIndex, hour) => {
    const { avail, offs, outlook, google } = getBlocksForDay(dayIndex);
    const cellStart = hour * 60;
    const cellEnd = (hour + 1) * 60;

    let isAvailable = false;
    let isBlocked = false;
    let blockReason = '';
    let isOutlookBlock = false;
    let isOutlookOverride = false;
    let outlookTitle = '';

    for (const a of avail) {
      const aStart = timeToMinutes(a.start_time);
      const aEnd = timeToMinutes(a.end_time);
      if (cellStart < aEnd && cellEnd > aStart) {
        isAvailable = true;
        break;
      }
    }

    for (const o of offs) {
      if (!o.start_time || !o.end_time) {
        isBlocked = true;
        blockReason = o.reason || 'Celodenní blokace';
        break;
      }
      const oStart = timeToMinutes(o.start_time);
      const oEnd = timeToMinutes(o.end_time);
      if (cellStart < oEnd && cellEnd > oStart) {
        isBlocked = true;
        blockReason = o.reason || 'Blokace';
        break;
      }
    }

    // Check Outlook + Google external blocks (treated identically — first match wins)
    const externalBlocks = [
      ...(outlook || []).map(b => ({ ...b, _provider: 'Outlook' })),
      ...(google || []).map(b => ({ ...b, _provider: 'Google' })),
    ];
    for (const ob of externalBlocks) {
      const obStart = new Date(ob.start_time);
      const obEnd = new Date(ob.end_time);
      const obStartMin = obStart.getHours() * 60 + obStart.getMinutes();
      const obEndMin = obEnd.getHours() * 60 + obEnd.getMinutes();
      if (cellStart < obEndMin && cellEnd > obStartMin) {
        isOutlookBlock = true;
        isOutlookOverride = ob.override || false;
        outlookTitle = `${ob._provider}: ${ob.title || ob._provider}`;
        break;
      }
    }

    let bg = 'bg-gray-50';
    let textColor = 'text-gray-300';
    let title = 'Nedostupný';

    if (isOutlookBlock && !isOutlookOverride) {
      bg = 'bg-slate-200 border-slate-300';
      textColor = 'text-slate-600';
      title = outlookTitle;
    } else if (isOutlookBlock && isOutlookOverride) {
      bg = 'bg-amber-100 border-amber-300';
      textColor = 'text-amber-700';
      title = `Povoleno: ${outlookTitle}`;
    } else if (isBlocked && isAvailable) {
      bg = 'bg-red-100 border-red-200';
      textColor = 'text-red-600';
      title = blockReason;
    } else if (isAvailable) {
      bg = 'bg-emerald-100 border-emerald-200';
      textColor = 'text-emerald-700';
      title = 'Dostupný';
    } else if (isBlocked) {
      bg = 'bg-red-50 border-red-100';
      textColor = 'text-red-400';
      title = blockReason;
    }

    return (
      <div
        key={`${dayIndex}-${hour}`}
        className={`h-8 border border-gray-100 ${bg} relative group cursor-default transition-colors`}
        title={title}
        data-testid={`cal-cell-${dayIndex}-${hour}`}
      >
        {(isAvailable || isBlocked || isOutlookBlock) && (
          <div className={`absolute inset-0 flex items-center justify-center ${textColor} text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity`}>
            {isOutlookBlock ? outlookTitle : (isBlocked ? 'Blokace' : 'Volný')}
          </div>
        )}
      </div>
    );
  };

  const content = (
      <>
      <div className="space-y-6" data-testid="lecturer-availability-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dostupnost lektora</h1>
            <p className="text-sm text-gray-500 mt-1">Správa pravidelných časů a blokací</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              onClick={() => { setShowAddRecurring(true); setRecurringForm({ days_of_week: [], start_time: '08:00', end_time: '12:00' }); }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              data-testid="add-recurring-btn"
            >
              <Plus className="w-4 h-4 mr-1" />
              Pravidelný čas
            </Button>
            <Button
              onClick={() => { setShowAddOneOff(true); setOneOffForm({ specific_date: '', start_time: '09:00', end_time: '12:00' }); }}
              variant="outline"
              className="border-amber-300 text-amber-700 hover:bg-amber-50"
              data-testid="add-oneoff-btn"
            >
              <CalendarPlus className="w-4 h-4 mr-1" />
              Jednorázový čas
            </Button>
            <Button
              onClick={() => { setShowAddTimeOff(true); setTimeOffForm({ start_date: '', end_date: '', start_time: '', end_time: '', reason: '' }); }}
              variant="outline"
              className="border-red-300 text-red-600 hover:bg-red-50"
              data-testid="add-timeoff-btn"
            >
              <Ban className="w-4 h-4 mr-1" />
              Přidat blokaci
            </Button>
          </div>
        </div>

        {/* Lecturer selector + View toggle */}
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            {onViewToggle && (
              <div className="flex items-center gap-2 border border-gray-200 rounded-lg p-1 shrink-0" data-testid="view-toggle">
                <button onClick={() => onViewToggle('program')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${viewToggle === 'program' ? 'bg-slate-800 text-white' : 'text-gray-500 hover:text-gray-700'}`} data-testid="view-mode-program">
                  Programová
                </button>
                <button onClick={() => onViewToggle('personal')} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${viewToggle === 'personal' ? 'bg-slate-800 text-white' : 'text-gray-500 hover:text-gray-700'}`} data-testid="view-mode-personal">
                  Osobní
                </button>
              </div>
            )}
            {isAdmin && teamMembers.length > 0 && (
              <div className="flex items-center gap-2 flex-1">
                <Label className="text-sm font-medium whitespace-nowrap">Lektor:</Label>
                <Select
                  value={selectedLecturer || 'self'}
                  onValueChange={(val) => setSelectedLecturer(val === 'self' ? null : val)}
                >
                  <SelectTrigger className="w-64" data-testid="lecturer-selector">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="self">Můj kalendář</SelectItem>
                    {teamMembers.map(m => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.name || m.email} ({m.role})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </Card>

        {/* Personal calendar section — hidden for ucetni/pokladni */}
        {canPersonalCalendar && (
        <div className="space-y-4" data-testid="personal-calendar-section">
        <div>
          <h2 className="font-semibold text-slate-900">Propojit osobní kalendář</h2>
          <p className="text-sm text-gray-500">Obsazené termíny z vašeho osobního kalendáře zablokují vaši dostupnost. Export rezervací do kalendáře nastavíte v <strong>Rezervace → Synchronizace kalendáře</strong>.</p>
        </div>

        {/* Outlook Integration Card */}
        <Card className="p-4 border border-slate-200" data-testid="outlook-integration-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${outlookStatus.connected ? 'bg-blue-100' : 'bg-gray-100'}`}>
                <CalendarDays className={`w-5 h-5 ${outlookStatus.connected ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="font-medium text-slate-800 text-sm">Outlook kalendář</p>
                {outlookStatus.connected ? (
                  <p className="text-xs text-green-600">
                    Připojeno
                    {outlookStatus.last_sync_at && ` · Poslední sync: ${new Date(outlookStatus.last_sync_at).toLocaleString('cs-CZ')}`}
                  </p>
                ) : (
                  <p className="text-xs text-gray-500">Nepřipojeno — události z Outlooku neblokují rezervace</p>
                )}
                {outlookStatus.sync_error && (
                  <p className="text-xs text-red-500 mt-0.5">{outlookStatus.sync_error}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {outlookStatus.connected ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={syncOutlook}
                    disabled={outlookSyncing}
                    data-testid="sync-outlook-btn"
                  >
                    <RefreshCw className={`w-4 h-4 mr-1 ${outlookSyncing ? 'animate-spin' : ''}`} />
                    Sync
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={disconnectOutlook}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                    data-testid="disconnect-outlook-btn"
                  >
                    <Unlink className="w-4 h-4 mr-1" />
                    Odpojit
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  onClick={connectOutlook}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                  data-testid="connect-outlook-btn"
                >
                  <ExternalLink className="w-4 h-4 mr-1" />
                  Připojit Outlook
                </Button>
              )}
            </div>
          </div>

          {/* Single personal-page toggle: use busy events as blocks */}
          {outlookStatus.connected && (
            <div className="mt-3 pt-3 border-t flex items-start justify-between gap-3" data-testid="outlook-import-settings">
              <div>
                <p className="text-sm font-medium text-slate-800">Používat obsazené termíny jako blokace</p>
                <p className="text-xs text-gray-500">Obsazené události z vašeho Outlooku zablokují vaši dostupnost. Nevytvářejí rezervace a jejich názvy nemusí vidět ostatní role.</p>
              </div>
              <Switch
                checked={!!outlookStatus.import_enabled}
                onCheckedChange={setOutlookImport}
                data-testid="outlook-import-toggle"
              />
            </div>
          )}

          {/* Outlook blocks inline controls (compact) */}
          {outlookBlocks.length > 0 && (
            <div className="mt-3 pt-3 border-t">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  {outlookBlocks.length} Outlook {outlookBlocks.length === 1 ? 'blok' : 'bloků'} tento týden
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {outlookBlocks.map(block => (
                  <button
                    key={block.id}
                    onClick={() => toggleBlockOverride(block.id)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                      block.override 
                        ? 'bg-amber-100 text-amber-700 border border-amber-300 hover:bg-amber-200' 
                        : 'bg-slate-100 text-slate-600 border border-slate-300 hover:bg-slate-200'
                    }`}
                    title={block.override ? 'Klikněte pro blokaci' : 'Klikněte pro povolení rezervací'}
                    data-testid={`toggle-override-${block.id}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${block.override ? 'bg-amber-500' : 'bg-slate-400'}`} />
                    {block.title || 'Outlook'}
                    <span className="text-[10px] opacity-70">
                      {new Date(block.start_time).toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Google Calendar Integration Card — mirrors Outlook */}
        <Card className="p-4 border border-slate-200" data-testid="google-integration-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${googleStatus.connected ? 'bg-green-100' : 'bg-gray-100'}`}>
                <CalendarDays className={`w-5 h-5 ${googleStatus.connected ? 'text-green-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="font-medium text-slate-800 text-sm">Google kalendář</p>
                {googleStatus.connected ? (
                  <p className="text-xs text-green-600">
                    Připojeno
                    {googleStatus.last_sync_at && ` · Poslední sync: ${new Date(googleStatus.last_sync_at).toLocaleString('cs-CZ')}`}
                  </p>
                ) : googleStatus.configured === false ? (
                  <p className="text-xs text-gray-500">Modul není nakonfigurován — kontaktujte správce platformy</p>
                ) : (
                  <p className="text-xs text-gray-500">Nepřipojeno — události z Google kalendáře neblokují rezervace</p>
                )}
                {googleStatus.sync_error && (
                  <p className="text-xs text-red-500 mt-0.5">{googleStatus.sync_error}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {googleStatus.connected ? (
                <>
                  {googleStatus.needs_reconnect && (
                    <Button
                      size="sm"
                      onClick={connectGoogle}
                      className="bg-amber-500 hover:bg-amber-600 text-white"
                      data-testid="reconnect-google-btn"
                    >
                      <ExternalLink className="w-4 h-4 mr-1" />
                      Znovu připojit
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={syncGoogle}
                    disabled={googleSyncing}
                    data-testid="sync-google-btn"
                  >
                    <RefreshCw className={`w-4 h-4 mr-1 ${googleSyncing ? 'animate-spin' : ''}`} />
                    Synchronizovat nyní
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowGoogleDisconnect(true)}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                    data-testid="disconnect-google-btn"
                  >
                    <Unlink className="w-4 h-4 mr-1" />
                    Odpojit
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  onClick={connectGoogle}
                  disabled={googleStatus.configured === false}
                  className="bg-green-600 hover:bg-green-700 text-white disabled:opacity-50"
                  data-testid="connect-google-btn"
                  title={googleStatus.configured === false ? 'Google OAuth není nakonfigurován' : 'Připojit Google kalendář'}
                >
                  <ExternalLink className="w-4 h-4 mr-1" />
                  Připojit Google
                </Button>
              )}
            </div>
          </div>

          {googleStatus.needs_reconnect && googleStatus.connected && (
            <div className="mt-3 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800" data-testid="google-reconnect-notice">
              Je potřeba znovu připojit Google účet — pro export rezervací chybí oprávnění ke kalendáři.
            </div>
          )}

          {/* Single personal-page toggle: use busy events as blocks */}
          {googleStatus.connected && (
            <div className="mt-3 pt-3 border-t flex items-start justify-between gap-3" data-testid="google-import-settings">
              <div>
                <p className="text-sm font-medium text-slate-800">Používat obsazené termíny jako blokace</p>
                <p className="text-xs text-gray-500">Obsazené události z vašeho Google kalendáře zablokují vaši dostupnost. Nevytvářejí rezervace a jejich názvy nemusí vidět ostatní role.</p>
              </div>
              <Switch
                checked={!!googleStatus.import_enabled}
                onCheckedChange={setGoogleImport}
                data-testid="google-import-toggle"
              />
            </div>
          )}

          {googleSyncResult && (
            <div className="mt-3 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600" data-testid="google-sync-result">
              Importováno {googleSyncResult.imported} blokací · vytvořeno {googleSyncResult.created} · aktualizováno {googleSyncResult.updated} · odstraněno {googleSyncResult.deleted} · chyb {googleSyncResult.errors}
            </div>
          )}

          {googleBlocks.length > 0 && (
            <div className="mt-3 pt-3 border-t">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  {googleBlocks.length} Google {googleBlocks.length === 1 ? 'blok' : 'bloků'} tento týden
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {googleBlocks.map(block => (
                  <button
                    key={block.id}
                    onClick={() => toggleGoogleBlockOverride(block.id)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                      block.override
                        ? 'bg-amber-100 text-amber-700 border border-amber-300 hover:bg-amber-200'
                        : 'bg-slate-100 text-slate-600 border border-slate-300 hover:bg-slate-200'
                    }`}
                    title={block.override ? 'Klikněte pro blokaci' : 'Klikněte pro povolení rezervací'}
                    data-testid={`toggle-google-override-${block.id}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${block.override ? 'bg-amber-500' : 'bg-slate-400'}`} />
                    {block.title || 'Google'}
                    <span className="text-[10px] opacity-70">
                      {new Date(block.start_time).toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Google disconnect dialog — choose what happens to exported events */}
        <Dialog open={showGoogleDisconnect} onOpenChange={setShowGoogleDisconnect}>
          <DialogContent className="sm:max-w-md" aria-describedby={undefined} data-testid="google-disconnect-dialog">
            <DialogHeader>
              <DialogTitle>Odpojit Google kalendář</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-1">
              <p className="text-sm text-gray-600">Co se má stát s událostmi, které do Google kalendáře vytvořilo Budeživo? Vaše osobní události zůstanou nedotčené.</p>
              <Button
                onClick={() => disconnectGoogle(true)}
                className="w-full bg-red-600 hover:bg-red-700 text-white"
                data-testid="disconnect-delete-events-btn"
              >
                Odstranit exportované události z Google kalendáře
              </Button>
              <Button
                onClick={() => disconnectGoogle(false)}
                variant="outline"
                className="w-full"
                data-testid="disconnect-keep-events-btn"
              >
                Ponechat je v Google kalendáři
              </Button>
              <Button onClick={() => setShowGoogleDisconnect(false)} variant="ghost" className="w-full">Zrušit</Button>
            </div>
          </DialogContent>
        </Dialog>
        </div>
        )}

        {/* Legend */}
        <div className="flex items-center gap-6 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-emerald-100 border border-emerald-200" />
            <span className="text-gray-600">Dostupný</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-red-100 border border-red-200" />
            <span className="text-gray-600">Blokace</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-gray-100 border border-gray-300" />
            <span className="text-gray-600">Externí kalendář (Outlook / Google)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-amber-100 border border-amber-300" />
            <span className="text-gray-600">Ručně povoleno</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-gray-50 border border-gray-100" />
            <span className="text-gray-600">Nedostupný</span>
          </div>
        </div>

        {/* Week Calendar */}
        <Card className="p-0 overflow-hidden" data-testid="week-calendar">
          {/* Week navigation */}
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <Button variant="ghost" size="sm" onClick={() => navigateWeek(-1)} data-testid="prev-week-btn">
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-semibold text-slate-900">
                {weekDays[0].toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long' })} – {weekDays[6].toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })}
              </h3>
              <Button variant="outline" size="sm" onClick={goToCurrentWeek} className="text-xs h-7">
                <CalendarDays className="w-3 h-3 mr-1" />
                Dnes
              </Button>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigateWeek(1)} data-testid="next-week-btn">
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          {/* Calendar grid */}
          <div className="overflow-x-auto">
            <div className="min-w-[640px]">
              {/* Day headers */}
              <div className="grid grid-cols-[60px_repeat(7,1fr)] border-b">
                <div className="p-2 text-xs text-gray-400 text-center" />
                {weekDays.map((d, i) => {
                  const isToday = formatDate(d) === formatDate(new Date());
                  return (
                    <div key={i} className={`p-2 text-center border-l ${isToday ? 'bg-slate-800 text-white' : ''}`}>
                      <div className="text-xs font-medium">{DAY_SHORT[i]}</div>
                      <div className={`text-lg font-bold ${isToday ? 'text-white' : 'text-slate-900'}`}>{d.getDate()}</div>
                    </div>
                  );
                })}
              </div>

              {/* Hour rows */}
              {HOURS.map(hour => (
                <div key={hour} className="grid grid-cols-[60px_repeat(7,1fr)]">
                  <div className="p-1 text-xs text-gray-400 text-right pr-2 flex items-center justify-end">
                    {hour}:00
                  </div>
                  {Array.from({ length: 7 }, (_, i) => (
                    <div key={i} className="border-l">
                      {renderCalendarCell(i, hour)}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Recurring blocks list */}
        <Card className="p-4 md:p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-emerald-600" />
              <h2 className="font-semibold text-slate-900">Pravidelná dostupnost</h2>
            </div>
            <div className="relative group">
              <Info className="w-4 h-4 text-gray-400 cursor-help" />
              <div className="absolute right-0 bottom-full mb-2 w-56 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                Pravidelné bloky se opakují každý týden. Můžete je kdykoli upravit nebo smazat.
              </div>
            </div>
          </div>

          {recurring.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Žádná pravidelná dostupnost není nastavena.</p>
              <p className="text-xs mt-1">Lektor není defaultně dostupný.</p>
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {recurring.map(r => (
                <div key={r.id} className="flex items-center justify-between p-3 bg-emerald-50 border border-emerald-200 rounded-lg" data-testid={`recurring-${r.id}`}>
                  <div>
                    <p className="font-medium text-sm text-slate-900">{DAY_NAMES[r.day_of_week]}</p>
                    <p className="text-xs text-emerald-700">{r.start_time} – {r.end_time}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setEditingRecurring({ ...r })}>
                      <Edit2 className="w-3.5 h-3.5 text-gray-500" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:text-red-600" onClick={() => handleDeleteRecurring(r.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* One-off blocks list */}
        {oneOffs.length > 0 && (
          <Card className="p-4 md:p-6 space-y-4">
            <div className="flex items-center gap-2">
              <CalendarPlus className="w-5 h-5 text-amber-600" />
              <h2 className="font-semibold text-slate-900">Jednorázové bloky</h2>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {oneOffs.map(o => (
                <div key={o.id} className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg" data-testid={`oneoff-${o.id}`}>
                  <div>
                    <p className="font-medium text-sm text-slate-900">{o.specific_date}</p>
                    <p className="text-xs text-amber-700">{o.start_time} – {o.end_time}</p>
                  </div>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:text-red-600" onClick={() => handleDeleteRecurring(o.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Time-off list */}
        <Card className="p-4 md:p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Ban className="w-5 h-5 text-red-500" />
              <h2 className="font-semibold text-slate-900">Blokace / výjimky</h2>
            </div>
            <div className="relative group">
              <Info className="w-4 h-4 text-gray-400 cursor-help" />
              <div className="absolute right-0 bottom-full mb-2 w-56 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                Blokace má vyšší prioritu než pravidelná dostupnost. Překrývá a odečítá čas.
              </div>
            </div>
          </div>

          {timeOffs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Ban className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Žádné blokace.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {timeOffs.map(t => (
                <div key={t.id} className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg" data-testid={`timeoff-${t.id}`}>
                  <div>
                    <p className="font-medium text-sm text-slate-900">
                      {t.start_date === t.end_date ? t.start_date : `${t.start_date} – ${t.end_date}`}
                      {t.start_time && t.end_time ? ` (${t.start_time} – ${t.end_time})` : ' (celý den)'}
                    </p>
                    {t.reason && <p className="text-xs text-red-600">{t.reason}</p>}
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setEditingTimeOff({ ...t })}>
                      <Edit2 className="w-3.5 h-3.5 text-gray-500" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:text-red-600" onClick={() => handleDeleteTimeOff(t.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ====== DIALOG: Add Recurring ====== */}
      <Dialog open={showAddRecurring} onOpenChange={setShowAddRecurring}>
        <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Přidat pravidelný čas</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="text-sm font-medium">Dny v týdnu</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {DAY_NAMES.map((name, i) => (
                  <label
                    key={i}
                    className={`flex items-center gap-1.5 px-3 py-1.5 border rounded-lg cursor-pointer text-sm transition-colors ${
                      recurringForm.days_of_week.includes(i) ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : 'border-gray-200 hover:border-gray-300'
                    }`}
                    data-testid={`recurring-day-${i}`}
                  >
                    <Checkbox
                      checked={recurringForm.days_of_week.includes(i)}
                      onCheckedChange={() => toggleDay(i)}
                      className="hidden"
                    />
                    {DAY_SHORT[i]}
                  </label>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm">Čas od</Label>
                <Input
                  type="time"
                  value={recurringForm.start_time}
                  onChange={e => setRecurringForm({ ...recurringForm, start_time: e.target.value })}
                  data-testid="recurring-start-time"
                />
              </div>
              <div>
                <Label className="text-sm">Čas do</Label>
                <Input
                  type="time"
                  value={recurringForm.end_time}
                  onChange={e => setRecurringForm({ ...recurringForm, end_time: e.target.value })}
                  data-testid="recurring-end-time"
                />
              </div>
            </div>
            <p className="text-xs text-gray-500">Opakuje se každý týden.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddRecurring(false)}>Zrušit</Button>
            <Button onClick={handleAddRecurring} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="save-recurring-btn">
              Přidat
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ====== DIALOG: Edit Recurring ====== */}
      <Dialog open={!!editingRecurring} onOpenChange={() => setEditingRecurring(null)}>
        <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Upravit pravidelný čas</DialogTitle>
          </DialogHeader>
          {editingRecurring && (
            <div className="space-y-4 py-2">
              <div>
                <Label className="text-sm">Den</Label>
                <Select
                  value={String(editingRecurring.day_of_week)}
                  onValueChange={(val) => setEditingRecurring({ ...editingRecurring, day_of_week: parseInt(val) })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {DAY_NAMES.map((name, i) => (
                      <SelectItem key={i} value={String(i)}>{name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm">Čas od</Label>
                  <Input
                    type="time"
                    value={editingRecurring.start_time}
                    onChange={e => setEditingRecurring({ ...editingRecurring, start_time: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="text-sm">Čas do</Label>
                  <Input
                    type="time"
                    value={editingRecurring.end_time}
                    onChange={e => setEditingRecurring({ ...editingRecurring, end_time: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingRecurring(null)}>Zrušit</Button>
            <Button onClick={handleUpdateRecurring} className="bg-slate-800 hover:bg-slate-900 text-white">
              Uložit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ====== DIALOG: Add Time Off ====== */}
      {/* One-off availability dialog */}
      <Dialog open={showAddOneOff} onOpenChange={setShowAddOneOff}>
        <DialogContent aria-describedby="oneoff-desc">
          <DialogHeader>
            <DialogTitle>Přidat jednorázovou dostupnost</DialogTitle>
          </DialogHeader>
          <p id="oneoff-desc" className="text-sm text-gray-500 mb-4">
            Příležitostný čas — platí pouze pro jedno konkrétní datum.
          </p>
          <div className="space-y-4">
            <div>
              <Label>Datum</Label>
              <Input
                type="date"
                value={oneOffForm.specific_date}
                onChange={(e) => setOneOffForm({ ...oneOffForm, specific_date: e.target.value })}
                data-testid="oneoff-date"
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Od</Label>
                <Input
                  type="time"
                  value={oneOffForm.start_time}
                  onChange={(e) => setOneOffForm({ ...oneOffForm, start_time: e.target.value })}
                  data-testid="oneoff-start"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Do</Label>
                <Input
                  type="time"
                  value={oneOffForm.end_time}
                  onChange={(e) => setOneOffForm({ ...oneOffForm, end_time: e.target.value })}
                  data-testid="oneoff-end"
                  className="mt-1"
                />
              </div>
            </div>
            <Button
              onClick={handleAddOneOff}
              className="w-full bg-amber-600 hover:bg-amber-700 text-white"
              data-testid="oneoff-submit"
            >
              Přidat jednorázový čas
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Time-off dialog */}
      <Dialog open={showAddTimeOff} onOpenChange={setShowAddTimeOff}>
        <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Přidat blokaci</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm">Datum od</Label>
                <Input
                  type="date"
                  value={timeOffForm.start_date}
                  onChange={e => setTimeOffForm({ ...timeOffForm, start_date: e.target.value })}
                  data-testid="timeoff-start-date"
                />
              </div>
              <div>
                <Label className="text-sm">Datum do</Label>
                <Input
                  type="date"
                  value={timeOffForm.end_date}
                  onChange={e => setTimeOffForm({ ...timeOffForm, end_date: e.target.value })}
                  placeholder="Stejný den"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm">Čas od <span className="text-gray-400">(volitelné)</span></Label>
                <Input
                  type="time"
                  value={timeOffForm.start_time}
                  onChange={e => setTimeOffForm({ ...timeOffForm, start_time: e.target.value })}
                  data-testid="timeoff-start-time"
                />
              </div>
              <div>
                <Label className="text-sm">Čas do <span className="text-gray-400">(volitelné)</span></Label>
                <Input
                  type="time"
                  value={timeOffForm.end_time}
                  onChange={e => setTimeOffForm({ ...timeOffForm, end_time: e.target.value })}
                  data-testid="timeoff-end-time"
                />
              </div>
            </div>
            <p className="text-xs text-gray-500">Ponechte čas prázdný pro celodenní blokaci.</p>
            <div>
              <Label className="text-sm">Důvod <span className="text-gray-400">(volitelný)</span></Label>
              <Input
                value={timeOffForm.reason}
                onChange={e => setTimeOffForm({ ...timeOffForm, reason: e.target.value })}
                placeholder="Např. Porada, Dovolená, Nemoc..."
                data-testid="timeoff-reason"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddTimeOff(false)}>Zrušit</Button>
            <Button onClick={handleAddTimeOff} className="bg-red-600 hover:bg-red-700 text-white" data-testid="save-timeoff-btn">
              Přidat blokaci
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ====== DIALOG: Edit Time Off ====== */}
      <Dialog open={!!editingTimeOff} onOpenChange={() => setEditingTimeOff(null)}>
        <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Upravit blokaci</DialogTitle>
          </DialogHeader>
          {editingTimeOff && (
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm">Datum od</Label>
                  <Input
                    type="date"
                    value={editingTimeOff.start_date}
                    onChange={e => setEditingTimeOff({ ...editingTimeOff, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="text-sm">Datum do</Label>
                  <Input
                    type="date"
                    value={editingTimeOff.end_date}
                    onChange={e => setEditingTimeOff({ ...editingTimeOff, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm">Čas od</Label>
                  <Input
                    type="time"
                    value={editingTimeOff.start_time || ''}
                    onChange={e => setEditingTimeOff({ ...editingTimeOff, start_time: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="text-sm">Čas do</Label>
                  <Input
                    type="time"
                    value={editingTimeOff.end_time || ''}
                    onChange={e => setEditingTimeOff({ ...editingTimeOff, end_time: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label className="text-sm">Důvod</Label>
                <Input
                  value={editingTimeOff.reason || ''}
                  onChange={e => setEditingTimeOff({ ...editingTimeOff, reason: e.target.value })}
                  placeholder="Důvod blokace"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingTimeOff(null)}>Zrušit</Button>
            <Button onClick={handleUpdateTimeOff} className="bg-slate-800 hover:bg-slate-900 text-white">
              Uložit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConnectedGuideDialog
        open={!!connectedGuide}
        provider={connectedGuide}
        onClose={() => setConnectedGuide(null)}
      />
      </>
  );
  return embedded ? content : <AdminLayout>{content}</AdminLayout>;
};
