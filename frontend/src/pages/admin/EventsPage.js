import React, { useEffect, useState, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Switch } from '../../components/ui/switch';
import { Plus, ArrowLeft, Calendar, Users, Trash2, Eye, CreditCard, ClipboardList, MoreVertical, Tag, ChevronUp, ChevronDown, Link as LinkIcon, Download, FileText, FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';
import { AuthContext } from '../../context/AuthContext';
import { EventUrlModal } from '../../components/admin/EventUrlModal';

const EVENT_TYPES = [
  { value: 'event', label: 'Jednorázová akce' },
  { value: 'camp', label: 'Příměstský tábor' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'course', label: 'Kurz' },
];

const FIELD_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'email', label: 'Email' },
  { value: 'number', label: 'Číslo' },
  { value: 'date', label: 'Datum' },
  { value: 'select', label: 'Výběr' },
  { value: 'checkbox', label: 'Zaškrtávátko' },
];

const getDefaultEvent = () => ({
  name: '',
  type: 'event',
  description: '',
  capacity: 30,
  price: 0,
  currency: 'CZK',
  is_active: true,
  form_fields: [],
});

export const EventsPage = () => {
  const { user } = useContext(AuthContext);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [formData, setFormData] = useState(getDefaultEvent());
  const [activeTab, setActiveTab] = useState('detail');
  const [eventDates, setEventDates] = useState([]);
  const [newDate, setNewDate] = useState({ start: '', end: '' });
  const [applications, setApplications] = useState([]);
  const [showAppDialog, setShowAppDialog] = useState(false);
  const [selectedApp, setSelectedApp] = useState(null);
  const [paymentSettings, setPaymentSettings] = useState(null);
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [expandedApp, setExpandedApp] = useState(null);

  useEffect(() => {
    fetchEvents();
    fetchPaymentSettings();
  }, []);

  const fetchEvents = async () => {
    try {
      const res = await axios.get(`${API}/events`);
      setEvents(Array.isArray(res.data) ? res.data : []);
    } catch { setEvents([]); }
    finally { setLoading(false); }
  };

  const fetchPaymentSettings = async () => {
    try {
      const res = await axios.get(`${API}/events/settings/payment`);
      setPaymentSettings(res.data);
    } catch { /* ignore */ }
  };

  const fetchEventDetail = async (eventId) => {
    try {
      const res = await axios.get(`${API}/events/${eventId}`);
      setEventDates(res.data.dates || []);
    } catch { setEventDates([]); }
  };

  const fetchApplications = async (eventId) => {
    try {
      const res = await axios.get(`${API}/events/${eventId}/applications`);
      setApplications(res.data || []);
    } catch { setApplications([]); }
  };

  const handleCreate = () => {
    setFormData(getDefaultEvent());
    setEditingEvent(null);
    setEventDates([]);
    setApplications([]);
    setActiveTab('detail');
    setShowDialog(true);
  };

  const handleEdit = async (event) => {
    setEditingEvent(event);
    setFormData({
      name: event.name || '',
      type: event.type || 'event',
      description: event.description || '',
      capacity: event.capacity || 30,
      price: event.price || 0,
      currency: event.currency || 'CZK',
      is_active: event.is_active !== false,
      form_fields: event.form_fields || [],
    });
    setActiveTab('detail');
    setShowDialog(true);
    await fetchEventDetail(event.id);
    await fetchApplications(event.id);
  };

  const handleSave = async () => {
    try {
      if (editingEvent) {
        await axios.put(`${API}/events/${editingEvent.id}`, formData);
        toast.success('Událost aktualizována');
      } else {
        const res = await axios.post(`${API}/events`, formData);
        setEditingEvent(res.data);
        toast.success('Událost vytvořena');
      }
      fetchEvents();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při ukládání');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Opravdu smazat tuto událost?')) return;
    try {
      await axios.delete(`${API}/events/${id}`);
      toast.success('Událost smazána');
      setShowDialog(false);
      fetchEvents();
    } catch { toast.error('Chyba při mazání'); }
  };

  const addDate = async () => {
    if (!editingEvent || !newDate.start || !newDate.end) return;
    try {
      await axios.post(`${API}/events/${editingEvent.id}/dates`, {
        start_datetime: newDate.start,
        end_datetime: newDate.end,
      });
      setNewDate({ start: '', end: '' });
      await fetchEventDetail(editingEvent.id);
      toast.success('Termín přidán');
    } catch { toast.error('Chyba při přidávání termínu'); }
  };

  const removeDate = async (dateId) => {
    if (!editingEvent) return;
    try {
      await axios.delete(`${API}/events/${editingEvent.id}/dates/${dateId}`);
      await fetchEventDetail(editingEvent.id);
      toast.success('Termín odstraněn');
    } catch { toast.error('Chyba'); }
  };

  const addFormField = () => {
    setFormData(prev => ({
      ...prev,
      form_fields: [...prev.form_fields, {
        id: `field_${Date.now()}`,
        type: 'text',
        label: '',
        required: false,
        options: null,
        order: prev.form_fields.length,
      }],
    }));
  };

  const updateFormField = (index, key, value) => {
    setFormData(prev => ({
      ...prev,
      form_fields: prev.form_fields.map((f, i) => i === index ? { ...f, [key]: value } : f),
    }));
  };

  const removeFormField = (index) => {
    setFormData(prev => ({
      ...prev,
      form_fields: prev.form_fields.filter((_, i) => i !== index),
    }));
  };

  const moveFormField = (index, direction) => {
    setFormData(prev => {
      const fields = [...prev.form_fields];
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= fields.length) return prev;
      [fields[index], fields[targetIndex]] = [fields[targetIndex], fields[index]];
      return { ...prev, form_fields: fields.map((f, i) => ({ ...f, order: i })) };
    });
  };

  const updateApplicationStatus = async (appId, status, paymentStatus) => {
    try {
      const body = {};
      if (status) body.status = status;
      if (paymentStatus) body.payment_status = paymentStatus;
      await axios.put(`${API}/events/applications/${appId}/status`, body);
      if (editingEvent) await fetchApplications(editingEvent.id);
      toast.success('Status aktualizován');
    } catch { toast.error('Chyba'); }
  };

  const savePaymentSettings = async (data) => {
    try {
      const res = await axios.put(`${API}/events/settings/payment`, data);
      setPaymentSettings(res.data);
      toast.success('Platební nastavení uloženo');
    } catch { toast.error('Chyba při ukládání'); }
  };

  const getPublicUrl = () => {
    if (!user) return '';
    return `${window.location.origin}/events/${user.institution_id}`;
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const statusBadge = (status) => {
    const map = {
      pending: 'bg-amber-100 text-amber-700',
      approved: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
      waitlist: 'bg-orange-100 text-orange-700',
    };
    const labels = { pending: 'Čeká', approved: 'Schváleno', rejected: 'Zamítnuto', waitlist: 'Čekací listina' };
    return <span className={`px-2 py-0.5 text-xs rounded-full ${map[status] || 'bg-gray-100'}`}>{labels[status] || status}</span>;
  };

  const payBadge = (status) => {
    const map = {
      unpaid: 'bg-gray-100 text-gray-600',
      pending: 'bg-amber-100 text-amber-700',
      paid: 'bg-green-100 text-green-700',
      not_required: 'bg-sky-100 text-sky-700',
    };
    const labels = { unpaid: 'Nezaplaceno', pending: 'Čeká platba', paid: 'Zaplaceno', not_required: 'Platba není vyžadována' };
    return <span className={`px-2 py-0.5 text-xs rounded-full ${map[status] || 'bg-gray-100'}`}>{labels[status] || status}</span>;
  };

  // ===== RENDER =====

  if (!showDialog) {
    return (
      <AdminLayout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-900">Události</h1>
              <p className="text-sm text-gray-500 mt-1">Akce, tábory, workshopy a přihlášky</p>
            </div>
            <Button onClick={handleCreate} className="bg-slate-800 text-white hover:bg-slate-700" data-testid="create-event-btn">
              <Plus className="w-4 h-4 mr-2" /> Nová událost
            </Button>
          </div>

          {/* URL generator banner + payment warning */}
          <Card className="p-4 bg-gray-50 border-gray-200">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                {(!paymentSettings || !paymentSettings.account_number) ? (
                  <div className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-amber-600" />
                    <div>
                      <p className="text-sm font-medium text-amber-800">Platební nastavení není dokončeno</p>
                      <p className="text-xs text-amber-600">Nastavte bankovní účet v Nastavení.</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600">
                    <span className="font-semibold">{events.length}</span> {events.length === 1 ? 'událost' : 'událostí'}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowUrlModal(true)}
                  className="shrink-0"
                  data-testid="generate-event-url-btn"
                >
                  <LinkIcon className="w-4 h-4 mr-2" />
                  Generovat URL pro web
                </Button>
              </div>
            </div>
          </Card>

          {loading ? (
            <div className="text-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto" /></div>
          ) : events.length === 0 ? (
            <Card className="p-12 text-center">
              <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 mb-4">Zatím nemáte žádné události</p>
              <Button onClick={handleCreate} className="bg-slate-800 text-white"><Plus className="w-4 h-4 mr-2" /> Vytvořit první událost</Button>
            </Card>
          ) : (
            <div className="space-y-4">
              {events.map(ev => (
                <Card key={ev.id} className="p-4 md:p-6 cursor-pointer hover:shadow-md transition-shadow" onClick={() => handleEdit(ev)} data-testid={`event-card-${ev.id}`}>
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-semibold text-slate-900 truncate">{ev.name}</h3>
                        {!ev.is_active && <span className="px-2 py-0.5 text-xs bg-gray-200 text-gray-600 rounded">neaktivní</span>}
                      </div>
                      <p className="text-sm text-gray-500 line-clamp-1 mb-3">{ev.description}</p>
                      <div className="flex flex-wrap gap-3 text-sm text-gray-500">
                        <span className="flex items-center gap-1"><Tag className="w-3.5 h-3.5" /> {EVENT_TYPES.find(t => t.value === ev.type)?.label || ev.type}</span>
                        <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {ev.capacity} míst</span>
                        <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {ev.dates_count || 0} termínů</span>
                        <span className="flex items-center gap-1"><ClipboardList className="w-3.5 h-3.5" /> {ev.applications_count || 0} přihlášek</span>
                        {ev.price > 0
                          ? <span className="font-medium text-slate-700">{ev.price} Kč</span>
                          : <span className="px-2 py-0.5 text-xs rounded-full bg-sky-100 text-sky-700" data-testid={`event-free-badge-${ev.id}`}>Zdarma</span>}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* URL Generator Modal */}
          <EventUrlModal
            open={showUrlModal}
            onOpenChange={setShowUrlModal}
            events={events}
            institutionId={user?.institution_id}
          />
        </div>
      </AdminLayout>
    );
  }

  // ===== EVENT EDITOR DIALOG =====
  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center gap-4 mb-4">
          <button onClick={() => setShowDialog(false)} className="p-2 hover:bg-gray-100 rounded-lg" data-testid="event-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h2 className="text-xl font-semibold text-slate-900">{editingEvent ? 'Upravit událost' : 'Nová událost'}</h2>
        </div>

        {/* Tabs */}
        <div className="flex border-b overflow-x-auto">
          {['detail', 'dates', 'form', 'applications', 'payment']
            .filter(tab => !(tab === 'payment' && (formData.price || 0) <= 0))
            .map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab ? 'border-slate-800 text-slate-900' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              data-testid={`event-tab-${tab}`}
            >
              {{ detail: 'Detail', dates: 'Termíny', form: 'Formulář', applications: 'Přihlášky', payment: 'Platby' }[tab]}
            </button>
          ))}
        </div>

        <div className="max-h-[65vh] overflow-y-auto pb-20">
          {/* DETAIL TAB */}
          {activeTab === 'detail' && (
            <div className="space-y-6">
              <Card className="p-4 md:p-6 space-y-4">
                <h3 className="font-semibold text-slate-900">Základní informace</h3>
                <div>
                  <Label className="text-gray-500 text-sm">Název události</Label>
                  <Input value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} placeholder="Příměstský tábor..." className="mt-1" data-testid="event-name-input" />
                </div>
                <div>
                  <Label className="text-gray-500 text-sm">Typ</Label>
                  <Select value={formData.type} onValueChange={v => setFormData(p => ({ ...p, type: v }))}>
                    <SelectTrigger className="mt-1" data-testid="event-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {EVENT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-gray-500 text-sm">Popis</Label>
                  <Textarea value={formData.description} onChange={e => setFormData(p => ({ ...p, description: e.target.value }))} rows={3} className="mt-1" data-testid="event-description-input" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-gray-500 text-sm">Kapacita</Label>
                    <Input type="number" value={formData.capacity} onChange={e => setFormData(p => ({ ...p, capacity: parseInt(e.target.value) || 0 }))} className="mt-1" data-testid="event-capacity-input" />
                  </div>
                  <div>
                    <Label className="text-gray-500 text-sm">Cena (Kč)</Label>
                    <Input
                      type="number"
                      min="0"
                      value={formData.price}
                      disabled={(formData.price || 0) <= 0}
                      onChange={e => setFormData(p => ({ ...p, price: parseFloat(e.target.value) || 0 }))}
                      className="mt-1 disabled:opacity-50"
                      data-testid="event-price-input"
                    />
                  </div>
                </div>
                {/* Free-event toggle: kept in sync with the price field */}
                <div className="flex items-center justify-between rounded-lg border border-sky-100 bg-sky-50/50 p-3">
                  <div>
                    <p className="font-medium text-slate-900">Akce je zdarma</p>
                    <p className="text-sm text-gray-500">Bez platby, QR kódu i platebních metod. Cena bude 0 Kč.</p>
                  </div>
                  <Switch
                    checked={(formData.price || 0) <= 0}
                    onCheckedChange={v => {
                      setFormData(p => ({ ...p, price: v ? 0 : (p.price > 0 ? p.price : 100) }));
                      if (v && activeTab === 'payment') setActiveTab('detail');
                    }}
                    data-testid="event-free-toggle"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-900">Aktivní</p>
                    <p className="text-sm text-gray-500">Událost je viditelná ve veřejné nabídce</p>
                  </div>
                  <Switch checked={formData.is_active} onCheckedChange={v => setFormData(p => ({ ...p, is_active: v }))} data-testid="event-active-toggle" />
                </div>
              </Card>
            </div>
          )}

          {/* DATES TAB */}
          {activeTab === 'dates' && (
            <div className="space-y-6">
              <Card className="p-4 md:p-6 space-y-4">
                <h3 className="font-semibold text-slate-900">Termíny</h3>
                {!editingEvent && <p className="text-sm text-amber-600">Nejprve uložte událost pro přidání termínů.</p>}
                {editingEvent && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs text-gray-500">Začátek</Label>
                        <Input type="datetime-local" value={newDate.start} onChange={e => setNewDate(p => ({ ...p, start: e.target.value }))} className="mt-1" data-testid="event-date-start" />
                      </div>
                      <div>
                        <Label className="text-xs text-gray-500">Konec</Label>
                        <Input type="datetime-local" value={newDate.end} onChange={e => setNewDate(p => ({ ...p, end: e.target.value }))} className="mt-1" data-testid="event-date-end" />
                      </div>
                    </div>
                    <Button onClick={addDate} disabled={!newDate.start || !newDate.end} className="bg-slate-800 text-white" data-testid="add-event-date-btn">
                      <Plus className="w-4 h-4 mr-2" /> Přidat termín
                    </Button>
                    {eventDates.length > 0 ? (
                      <div className="space-y-2 mt-4">
                        {eventDates.map(d => (
                          <div key={d.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div>
                              <p className="text-sm font-medium">{formatDate(d.start_datetime)}</p>
                              <p className="text-xs text-gray-500">do {formatDate(d.end_datetime)}</p>
                            </div>
                            <Button size="sm" variant="ghost" onClick={() => removeDate(d.id)} className="text-red-400 hover:text-red-600">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    ) : <p className="text-sm text-gray-500">Žádné termíny.</p>}
                  </>
                )}
              </Card>
            </div>
          )}

          {/* FORM BUILDER TAB */}
          {activeTab === 'form' && (
            <div className="space-y-6">
              <Card className="p-4 md:p-6 space-y-4">
                <h3 className="font-semibold text-slate-900">Přihlašovací formulář</h3>
                <p className="text-sm text-gray-500">Definujte pole, která musí zájemce vyplnit při přihlášení.</p>

                {formData.form_fields.map((field, idx) => (
                  <div key={field.id || idx} className="p-3 bg-gray-50 rounded-lg space-y-2" data-testid={`form-field-${idx}`}>
                    <div className="flex items-center gap-2">
                      <div className="flex flex-col shrink-0">
                        <button type="button" onClick={() => moveFormField(idx, -1)} disabled={idx === 0} className="p-0.5 text-gray-400 hover:text-gray-700 disabled:opacity-30" data-testid={`move-field-up-${idx}`}>
                          <ChevronUp className="w-4 h-4" />
                        </button>
                        <button type="button" onClick={() => moveFormField(idx, 1)} disabled={idx === formData.form_fields.length - 1} className="p-0.5 text-gray-400 hover:text-gray-700 disabled:opacity-30" data-testid={`move-field-down-${idx}`}>
                          <ChevronDown className="w-4 h-4" />
                        </button>
                      </div>
                      <Input value={field.label} onChange={e => updateFormField(idx, 'label', e.target.value)} placeholder="Název pole..." className="flex-1 text-sm" data-testid={`form-field-label-${idx}`} />
                      <select value={field.type} onChange={e => updateFormField(idx, 'type', e.target.value)} className="text-sm border rounded px-2 py-1.5 bg-white" data-testid={`form-field-type-${idx}`}>
                        {FIELD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                      </select>
                      <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer whitespace-nowrap">
                        <input type="checkbox" checked={field.required} onChange={e => updateFormField(idx, 'required', e.target.checked)} className="rounded" />
                        Povinné
                      </label>
                      <button onClick={() => removeFormField(idx)} className="p-1 text-red-400 hover:text-red-600 shrink-0"><Trash2 className="w-4 h-4" /></button>
                    </div>
                    {field.type === 'select' && (
                      <div className="space-y-1.5 pl-8">
                        <label className="text-xs text-gray-500">Možnosti výběru (každá na novém řádku):</label>
                        <textarea
                          value={(field.options || []).join('\n')}
                          onChange={e => updateFormField(idx, 'options', e.target.value.split('\n'))}
                          onBlur={e => updateFormField(idx, 'options', e.target.value.split('\n').filter(o => o.trim().length > 0))}
                          placeholder={"Možnost 1\nMožnost 2\nMožnost 3"}
                          className="w-full text-sm border rounded-md px-3 py-2 bg-white min-h-[80px] resize-y"
                          data-testid={`form-field-options-${idx}`}
                        />
                      </div>
                    )}
                  </div>
                ))}

                <button onClick={addFormField} className="w-full py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-gray-400" data-testid="add-form-field-btn">
                  <Plus className="w-4 h-4 inline mr-1" /> Přidat pole
                </button>
              </Card>
            </div>
          )}

          {/* APPLICATIONS TAB */}
          {activeTab === 'applications' && (
            <div className="space-y-6">
              <Card className="p-4 md:p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900">Přihlášky ({applications.length})</h3>
                  {editingEvent && applications.length > 0 && (
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => window.open(`${API}/events/${editingEvent.id}/export/xlsx`, '_blank')} data-testid="export-xlsx">
                        <FileSpreadsheet className="w-4 h-4 mr-1" /> XLSX
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => window.open(`${API}/events/${editingEvent.id}/export/csv`, '_blank')} data-testid="export-csv">
                        <Download className="w-4 h-4 mr-1" /> CSV
                      </Button>
                    </div>
                  )}
                </div>
                {!editingEvent && <p className="text-sm text-amber-600">Nejprve uložte událost.</p>}
                {editingEvent && applications.length === 0 && <p className="text-sm text-gray-500">Zatím žádné přihlášky.</p>}
                {applications.map(app => {
                  const fieldLabelMap = {};
                  (formData.form_fields || []).forEach(f => { fieldLabelMap[f.id] = f.label; });
                  const isExpanded = expandedApp === app.id;

                  return (
                  <div key={app.id} className="border rounded-lg overflow-hidden" data-testid={`application-${app.id}`}>
                    {/* Collapsed header — always visible */}
                    <button
                      type="button"
                      onClick={() => setExpandedApp(isExpanded ? null : app.id)}
                      className="w-full text-left p-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                      data-testid={`toggle-app-${app.id}`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{app.applicant_name || 'Bez jména'}</p>
                          <p className="text-xs text-gray-500 truncate">{app.applicant_email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-2">
                        {app.total_amount > 0 && <span className="text-xs text-gray-500">{app.total_amount} Kč</span>}
                        {statusBadge(app.status)}
                        {payBadge(app.payment_status)}
                      </div>
                    </button>

                    {/* Expanded detail */}
                    {isExpanded && (
                      <div className="border-t px-3 pb-3 space-y-3">
                        <div className="pt-3 flex items-center gap-4 text-xs text-gray-500">
                          <span>VS: {app.variable_symbol}</span>
                          <span>{app.created_at ? new Date(app.created_at).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}</span>
                        </div>
                        {app.applicant_data && Object.keys(app.applicant_data).length > 0 && (
                          <div className="text-xs text-gray-600 bg-gray-50 rounded p-2.5 space-y-1.5">
                            {Object.entries(app.applicant_data).map(([k, v]) => {
                              const label = fieldLabelMap[k] || k;
                              const displayValue = typeof v === 'boolean' ? (v ? 'Ano' : 'Ne') : String(v);
                              return (
                                <div key={k} className="flex gap-2">
                                  <span className="text-gray-400 shrink-0">{label}:</span>
                                  <span className="font-medium text-gray-700">{displayValue}</span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                        <div className="flex flex-wrap gap-2 pt-1">
                          {app.status === 'pending' && (
                            <>
                              <Button size="sm" variant="outline" className="text-green-600" onClick={() => updateApplicationStatus(app.id, 'approved')} data-testid={`approve-app-${app.id}`}>Schválit</Button>
                              <Button size="sm" variant="outline" className="text-red-600" onClick={() => updateApplicationStatus(app.id, 'rejected')} data-testid={`reject-app-${app.id}`}>Zamítnout</Button>
                            </>
                          )}
                          {app.status === 'waitlist' && (
                            <Button size="sm" variant="outline" className="text-orange-600" onClick={() => updateApplicationStatus(app.id, 'pending')} data-testid={`promote-app-${app.id}`}>Posunout z čekací listiny</Button>
                          )}
                          {app.payment_status !== 'paid' && app.total_amount > 0 && (
                            <Button size="sm" variant="outline" className="text-slate-600" onClick={() => updateApplicationStatus(app.id, null, 'paid')} data-testid={`mark-paid-${app.id}`}>Označit zaplaceno</Button>
                          )}
                          <Button size="sm" variant="outline" onClick={() => window.open(`${API}/events/applications/${app.id}/pdf`, '_blank')} data-testid={`pdf-${app.id}`}>
                            <FileText className="w-3.5 h-3.5 mr-1" /> PDF
                          </Button>
                        </div>
                      </div>
                    )}
                    </div>
                  );
                })}
              </Card>
            </div>
          )}

          {/* PAYMENT TAB */}
          {activeTab === 'payment' && (
            <div className="space-y-6">
              <Card className="p-4 md:p-6 space-y-4">
                <h3 className="font-semibold text-slate-900">Platební nastavení</h3>
                <p className="text-sm text-gray-500">Nastavení bankovního účtu pro příjem plateb za události.</p>
                <div>
                  <Label className="text-gray-500 text-sm">Číslo účtu</Label>
                  <Input value={paymentSettings?.account_number || ''} onChange={e => setPaymentSettings(p => ({ ...p, account_number: e.target.value }))} placeholder="1234567890" className="mt-1" data-testid="payment-account-number" />
                </div>
                <div>
                  <Label className="text-gray-500 text-sm">Kód banky</Label>
                  <Input value={paymentSettings?.bank_code || ''} onChange={e => setPaymentSettings(p => ({ ...p, bank_code: e.target.value }))} placeholder="0100" className="mt-1" data-testid="payment-bank-code" />
                </div>
                <div>
                  <Label className="text-gray-500 text-sm">Název účtu</Label>
                  <Input value={paymentSettings?.account_name || ''} onChange={e => setPaymentSettings(p => ({ ...p, account_name: e.target.value }))} placeholder="Vaše organizace" className="mt-1" data-testid="payment-account-name" />
                </div>
                <div>
                  <Label className="text-gray-500 text-sm">Režim platby</Label>
                  <Select value={paymentSettings?.payment_mode || 'qr'} onValueChange={v => setPaymentSettings(p => ({ ...p, payment_mode: v }))}>
                    <SelectTrigger className="mt-1" data-testid="payment-mode-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="qr">QR platba</SelectItem>
                      <SelectItem value="gateway">Platební brána</SelectItem>
                      <SelectItem value="both">QR + Brána</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {(paymentSettings?.payment_mode === 'gateway' || paymentSettings?.payment_mode === 'both') && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <p className="text-sm text-emerald-700">
                      Platební brána <strong>Comgate</strong> je aktivní. Po uložení můžete na rezervaci spustit platbu kartou.
                    </p>
                  </div>
                )}
                <Button onClick={() => savePaymentSettings(paymentSettings)} className="bg-slate-800 text-white" data-testid="save-payment-btn">Uložit platební nastavení</Button>
              </Card>
            </div>
          )}
        </div>

        {/* Fixed footer */}
        {activeTab !== 'payment' && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 flex gap-2 md:relative md:border-0 md:p-0 md:mt-4">
            <Button onClick={handleSave} className="flex-1 bg-slate-800 text-white hover:bg-slate-700" data-testid="save-event-btn">
              Uložit událost
            </Button>
            {editingEvent && (
              <Button variant="outline" onClick={() => handleDelete(editingEvent.id)} className="text-red-500 border-red-200 hover:bg-red-50" data-testid="delete-event-btn">
                <Trash2 className="w-5 h-5" />
              </Button>
            )}
          </div>
        )}
      </div>
    </AdminLayout>
  );
};
