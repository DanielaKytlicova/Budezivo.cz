import React, { useState, useEffect } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Bell, Calendar, Users, School, Mail, Phone, Clock, ChevronDown, Filter } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';

const STATUS_MAP = {
  active: { label: 'Aktivní', bg: 'bg-blue-100 text-blue-700' },
  contacted: { label: 'Kontaktován', bg: 'bg-amber-100 text-amber-700' },
  booked: { label: 'Vyřešeno', bg: 'bg-green-100 text-green-700' },
  cancelled: { label: 'Zrušeno', bg: 'bg-gray-200 text-gray-600' },
  expired: { label: 'Expirováno', bg: 'bg-gray-200 text-gray-500' },
};

const TIME_LABELS = { morning: 'Dopoledne', midday: 'Kolem poledne', afternoon: 'Odpoledne', any: 'Kdykoliv' };

const formatDate = (d) => d ? new Date(d + 'T00:00:00').toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', year: 'numeric' }) : '';

export const WaitlistPage = () => {
  const [entries, setEntries] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterProgram, setFilterProgram] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [expanded, setExpanded] = useState(null);
  const [editDialog, setEditDialog] = useState(null);
  const [adminNote, setAdminNote] = useState('');
  const [newStatus, setNewStatus] = useState('');

  useEffect(() => { fetchEntries(); fetchPrograms(); }, []);
  useEffect(() => { fetchEntries(); }, [filterProgram, filterStatus]);

  const fetchEntries = async () => {
    try {
      let url = `${API}/waitlist?`;
      if (filterProgram !== 'all') url += `program_id=${filterProgram}&`;
      if (filterStatus !== 'all') url += `status=${filterStatus}&`;
      const res = await axios.get(url);
      setEntries(res.data || []);
    } catch { setEntries([]); }
    finally { setLoading(false); }
  };

  const fetchPrograms = async () => {
    try {
      const res = await axios.get(`${API}/programs`);
      setPrograms((res.data || []).filter(p => p.status !== 'archived'));
    } catch { /* */ }
  };

  const openEdit = (entry) => {
    setEditDialog(entry);
    setNewStatus(entry.status);
    setAdminNote(entry.admin_note || '');
  };

  const saveEdit = async () => {
    if (!editDialog) return;
    try {
      await axios.patch(`${API}/waitlist/${editDialog.id}`, { status: newStatus, admin_note: adminNote });
      toast.success('Záznam aktualizován');
      setEditDialog(null);
      fetchEntries();
    } catch { toast.error('Chyba při ukládání'); }
  };

  const activeCount = entries.filter(e => e.status === 'active').length;

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Zájemci o termín</h1>
            <p className="text-sm text-gray-500 mt-1">{activeCount} aktivních zájemců</p>
          </div>
        </div>

        {/* Filters */}
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex items-center gap-2 flex-1">
              <Filter className="w-4 h-4 text-gray-400" />
              <Select value={filterProgram} onValueChange={setFilterProgram}>
                <SelectTrigger className="w-full sm:w-56" data-testid="filter-program"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny programy</SelectItem>
                  {programs.map(p => <SelectItem key={p.id} value={p.id}>{p.name_cs}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-full sm:w-40" data-testid="filter-status"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Všechny statusy</SelectItem>
                {Object.entries(STATUS_MAP).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </Card>

        {/* Entries list */}
        {loading ? (
          <div className="text-center py-12"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-slate-800 mx-auto" /></div>
        ) : entries.length === 0 ? (
          <Card className="p-12 text-center">
            <Bell className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Zatím žádní zájemci</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {entries.map(entry => {
              const isExpanded = expanded === entry.id;
              const st = STATUS_MAP[entry.status] || STATUS_MAP.active;
              return (
                <Card key={entry.id} className="overflow-hidden" data-testid={`waitlist-entry-${entry.id}`}>
                  <button
                    type="button"
                    onClick={() => setExpanded(isExpanded ? null : entry.id)}
                    className="w-full text-left p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                    data-testid={`toggle-waitlist-${entry.id}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`} />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{entry.teacher_name}</p>
                        <p className="text-xs text-gray-500 truncate">{entry.school_name}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-2">
                      <span className="text-xs text-gray-500 hidden sm:inline">{entry.program_name}</span>
                      <span className="text-xs text-gray-500">
                        {entry.request_type === 'specific_date' ? formatDate(entry.requested_date) : `${formatDate(entry.range_start_date)} – ${formatDate(entry.range_end_date)}`}
                      </span>
                      <span className="text-xs text-gray-500 hidden sm:inline">{entry.participant_count} os.</span>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${st.bg}`}>{st.label}</span>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t px-4 pb-4 pt-3 space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                        <div className="flex items-center gap-2 text-gray-600">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          <span className="font-medium">{entry.program_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                          <Users className="w-4 h-4 text-gray-400" />
                          <span>{entry.participant_count} účastníků</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                          <Mail className="w-4 h-4 text-gray-400" />
                          <a href={`mailto:${entry.email}`} className="text-[#4A6FA5] hover:underline">{entry.email}</a>
                        </div>
                        {entry.phone && (
                          <div className="flex items-center gap-2 text-gray-600">
                            <Phone className="w-4 h-4 text-gray-400" />
                            <a href={`tel:${entry.phone}`} className="hover:underline">{entry.phone}</a>
                          </div>
                        )}
                        <div className="flex items-center gap-2 text-gray-600">
                          <Clock className="w-4 h-4 text-gray-400" />
                          <span>Preferovaný čas: {TIME_LABELS[entry.preferred_time_of_day] || entry.preferred_time_of_day}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                          <School className="w-4 h-4 text-gray-400" />
                          <span>{entry.school_name}</span>
                        </div>
                      </div>
                      {entry.notes && (
                        <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded"><strong>Poznámka:</strong> {entry.notes}</div>
                      )}
                      {entry.admin_note && (
                        <div className="text-sm text-blue-700 bg-blue-50 p-2 rounded"><strong>Admin:</strong> {entry.admin_note}</div>
                      )}
                      <div className="flex gap-2 pt-1">
                        <Button size="sm" variant="outline" onClick={() => openEdit(entry)} data-testid={`edit-waitlist-${entry.id}`}>
                          Změnit status
                        </Button>
                        {entry.status === 'active' && (
                          <Button size="sm" variant="outline" className="text-amber-600" onClick={async () => {
                            await axios.patch(`${API}/waitlist/${entry.id}`, { status: 'contacted' });
                            toast.success('Označeno jako kontaktován');
                            fetchEntries();
                          }}>Kontaktován</Button>
                        )}
                      </div>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Edit dialog */}
        <Dialog open={!!editDialog} onOpenChange={(o) => !o && setEditDialog(null)}>
          <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-md" aria-describedby="edit-waitlist-desc">
            <DialogHeader>
              <DialogTitle>Upravit záznam</DialogTitle>
              <p id="edit-waitlist-desc" className="text-sm text-gray-500">{editDialog?.teacher_name} — {editDialog?.school_name}</p>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <Label className="text-sm">Status</Label>
                <Select value={newStatus} onValueChange={setNewStatus}>
                  <SelectTrigger className="mt-1" data-testid="edit-status-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(STATUS_MAP).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm">Interní poznámka</Label>
                <Textarea value={adminNote} onChange={e => setAdminNote(e.target.value)} placeholder="Poznámka pro tým..." className="mt-1" rows={3} data-testid="admin-note-input" />
              </div>
              <div className="flex gap-2">
                <Button onClick={saveEdit} className="flex-1 bg-slate-800 text-white" data-testid="save-waitlist-status">Uložit</Button>
                <Button variant="outline" onClick={() => setEditDialog(null)} className="flex-1">Zrušit</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
};
