import React, { useEffect, useState, useContext, useMemo } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import axios from 'axios';
import { 
  Calendar, 
  Clock, 
  Users, 
  Phone, 
  Mail, 
  School, 
  User,
  Check,
  X,
  Edit,
  UserPlus,
  UserMinus,
  Eye,
  AlertCircle,
  Link as LinkIcon,
  Copy,
  CheckSquare,
  Square,
  Filter,
  Download,
  CalendarPlus,
  Bell
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { API } from '../../config/api';

// Helper to download ICS with signed token
const downloadIcs = async (entityType, entityId, token) => {
  try {
    const tokenRes = await axios.get(`${API}/calendar/feed-token/${entityType}/${entityId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const signedToken = tokenRes.data.token;
    window.open(`${API}/calendar/${entityType}/${entityId}.ics?token=${signedToken}`, '_blank');
  } catch {
    toast.error('Nepodařilo se vygenerovat ICS odkaz');
  }
};

const downloadReservationIcs = async (reservationId, token) => {
  try {
    const tokenRes = await axios.get(`${API}/calendar/feed-token/reservation/${reservationId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const signedToken = tokenRes.data.token;
    window.open(`${API}/calendar/reservation/${reservationId}.ics?token=${signedToken}`, '_blank');
  } catch {
    toast.error('Nepodařilo se vygenerovat ICS odkaz');
  }
};

// Role permissions helper
const PERMISSIONS = {
  admin: { canEditAll: true, canEditAttendance: true, canAssignLecturer: true, canEditDateTime: true, canEditContact: true },
  spravce: { canEditAll: true, canEditAttendance: true, canAssignLecturer: true, canEditDateTime: true, canEditContact: true },
  edukator: { canEditAll: true, canEditAttendance: true, canAssignLecturer: true, canEditDateTime: true, canEditContact: true },
  pokladni: { canEditAll: false, canEditAttendance: true, canAssignLecturer: false, canEditDateTime: false, canEditContact: false },
  lektor: { canEditAll: false, canEditAttendance: false, canAssignLecturer: true, canEditDateTime: false, canEditContact: false },
  viewer: { canEditAll: false, canEditAttendance: false, canAssignLecturer: false, canEditDateTime: false, canEditContact: false },
};

export const BookingsPage = () => {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [currentUserRole, setCurrentUserRole] = useState('viewer');
  const [editMode, setEditMode] = useState(null);
  const [editData, setEditData] = useState({});
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedLecturer, setSelectedLecturer] = useState('');
  // Bulk actions state
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchBookings();
    fetchCurrentUserRole();
    fetchTeamMembers();
  }, []);

  const fetchBookings = async () => {
    try {
      const response = await axios.get(`${API}/bookings`);
      setBookings(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      toast.error(t('common.error'));
      setBookings([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentUserRole = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setCurrentUserRole(response.data.role || 'viewer');
    } catch (error) {
      console.error('Failed to fetch user role');
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API}/team`);
      // Filter only lecturers and educators (any status - active or null)
      const lecturers = (response.data || []).filter(
        m => ['lektor', 'edukator', 'admin', 'spravce'].includes(m.role)
      );
      setTeamMembers(lecturers);
    } catch (error) {
      console.error('Failed to fetch team members');
    }
  };

  const getPermissions = () => {
    return PERMISSIONS[currentUserRole] || PERMISSIONS.viewer;
  };

  // Filtered bookings based on status filter and search
  const filteredBookings = useMemo(() => {
    let filtered = bookings;
    if (statusFilter !== 'all') {
      filtered = filtered.filter(b => b.status === statusFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(b =>
        (b.school_name || '').toLowerCase().includes(q) ||
        (b.contact_name || '').toLowerCase().includes(q) ||
        (b.contact_email || '').toLowerCase().includes(q) ||
        (b.program_name || '').toLowerCase().includes(q)
      );
    }
    return filtered;
  }, [bookings, statusFilter, searchQuery]);

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredBookings.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredBookings.map(b => b.id)));
    }
  };

  const bulkUpdateStatus = async (status) => {
    if (selectedIds.size === 0) return;
    const labels = { confirmed: 'potvrzení', cancelled: 'zrušení', completed: 'dokončení' };
    setBulkLoading(true);
    try {
      const response = await axios.post(`${API}/bookings/bulk-status`, {
        booking_ids: Array.from(selectedIds),
        status
      });
      toast.success(response.data.message);
      setSelectedIds(new Set());
      fetchBookings();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : `Chyba při hromadném ${labels[status]}`);
    } finally {
      setBulkLoading(false);
    }
  };

  const statusCounts = useMemo(() => {
    const counts = { all: bookings.length, pending: 0, confirmed: 0, cancelled: 0, completed: 0 };
    bookings.forEach(b => {
      if (counts[b.status] !== undefined) counts[b.status]++;
    });
    return counts;
  }, [bookings]);

  const updateStatus = async (id, status) => {
    try {
      await axios.patch(`${API}/bookings/${id}/status?status=${status}`);
      toast.success('Stav rezervace byl aktualizován');
      fetchBookings();
      if (selectedBooking?.id === id) {
        setSelectedBooking(prev => ({ ...prev, status }));
      }
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const updateBooking = async () => {
    if (!selectedBooking) return;
    
    try {
      // Only send fields relevant to the current edit mode
      let payload = {};
      if (editMode === 'datetime') {
        payload = { date: editData.date, time_block: editData.time_block };
      } else if (editMode === 'attendance') {
        payload = { actual_students: editData.actual_students || 0, actual_teachers: editData.actual_teachers || 0 };
      } else if (editMode === 'contact') {
        payload = { contact_name: editData.contact_name, contact_email: editData.contact_email, contact_phone: editData.contact_phone };
      } else if (editMode === 'notes') {
        payload = { notes: editData.notes };
      } else {
        payload = editData;
      }

      await axios.put(`${API}/bookings/${selectedBooking.id}`, payload);
      toast.success('Rezervace byla aktualizována');
      fetchBookings();
      setSelectedBooking(prev => ({ ...prev, ...payload }));
      setEditMode(null);
    } catch (error) {
      const detail = error.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Chyba při aktualizaci rezervace';
      toast.error(msg);
    }
  };

  const assignLecturer = async () => {
    if (!selectedBooking) return;
    
    try {
      const response = await axios.post(`${API}/bookings/${selectedBooking.id}/assign-lecturer`);
      toast.success(`Lektor ${response.data.lecturer_name} byl přiřazen`);
      fetchBookings();
      const updatedBooking = await axios.get(`${API}/bookings/${selectedBooking.id}`);
      setSelectedBooking(updatedBooking.data);
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Chyba při přiřazení lektora');
    }
  };

  const assignLecturerByAdmin = async (lecturerId) => {
    if (!selectedBooking || !lecturerId) return;
    
    try {
      const response = await axios.post(`${API}/bookings/${selectedBooking.id}/assign-lecturer-admin`, {
        lecturer_id: lecturerId
      });
      toast.success(`Lektor ${response.data.lecturer_name} byl přiřazen`);
      fetchBookings();
      const updatedBooking = await axios.get(`${API}/bookings/${selectedBooking.id}`);
      setSelectedBooking(updatedBooking.data);
      setSelectedLecturer('');
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Chyba při přiřazení lektora');
    }
  };

  const unassignLecturer = async () => {
    if (!selectedBooking) return;
    
    try {
      await axios.delete(`${API}/bookings/${selectedBooking.id}/unassign-lecturer`);
      toast.success('Lektor byl odhlášen');
      fetchBookings();
      setSelectedBooking(prev => ({
        ...prev,
        assigned_lecturer_id: null,
        assigned_lecturer_name: null,
        assigned_lecturer_at: null
      }));
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Chyba při odhlášení lektora');
    }
  };

  const openDetail = (booking) => {
    setSelectedBooking(booking);
    setEditData({
      actual_students: booking.actual_students || '',
      actual_teachers: booking.actual_teachers || '',
      notes: booking.notes || '',
      date: booking.date || '',
      time_block: booking.time_block || '',
      contact_email: booking.contact_email || '',
      contact_phone: booking.contact_phone || '',
      contact_name: booking.contact_name || '',
    });
    setEditMode(null);
    setShowDetailModal(true);
  };

  const getStatusBadge = (status) => {
    const variants = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      completed: 'bg-blue-100 text-blue-800',
    };
    const labels = {
      pending: 'Čeká na potvrzení',
      confirmed: 'Potvrzeno',
      cancelled: 'Zrušeno',
      completed: 'Dokončeno',
    };
    return (
      <Badge className={variants[status] || 'bg-gray-100 text-gray-800'}>
        {labels[status] || status}
      </Badge>
    );
  };

  const getGroupTypeLabel = (groupType) => {
    const labels = {
      'ms_3_6': 'MŠ (3-6 let)',
      'zs1_7_12': 'I. stupeň ZŠ',
      'zs2_12_15': 'II. stupeň ZŠ',
      'ss_14_18': 'SŠ',
      'adults': 'Dospělí',
    };
    return labels[groupType] || groupType;
  };

  const permissions = getPermissions();

  const renderDetailModal = () => {
    if (!selectedBooking) return null;

    const canEditAttendance = permissions.canEditAttendance;
    const canEditDateTime = permissions.canEditDateTime;
    const canEditContact = permissions.canEditContact;
    const canAssign = permissions.canAssignLecturer;
    const isAssignedToMe = selectedBooking.assigned_lecturer_id === user?.id;
    const hasAssignedLecturer = !!selectedBooking.assigned_lecturer_id;

    return (
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
        <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-2xl max-h-[85dvh] sm:max-h-[90vh] overflow-y-auto" aria-describedby="booking-detail-description">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{selectedBooking.program_name || 'Detail rezervace'}</span>
              {getStatusBadge(selectedBooking.status)}
            </DialogTitle>
            <p id="booking-detail-description" className="sr-only">
              Detailní informace o rezervaci včetně počtu účastníků, kontaktních údajů a přiřazeného lektora.
            </p>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Základní informace */}
            <Card className="p-4 bg-slate-50">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <School className="w-5 h-5" />
                Škola / Skupina
              </h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Název:</span>
                  <p className="font-medium">{selectedBooking.school_name}</p>
                </div>
                <div>
                  <span className="text-gray-500">Typ skupiny:</span>
                  <p className="font-medium">{getGroupTypeLabel(selectedBooking.group_type)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Třída / Věk:</span>
                  <p className="font-medium">{selectedBooking.age_or_class || '-'}</p>
                </div>
              </div>
            </Card>

            {/* Datum a čas - editable by admin */}
            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                  <Calendar className="w-5 h-5" />
                  Datum a čas
                </h3>
                {canEditDateTime && editMode !== 'datetime' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditMode('datetime')}
                    data-testid="edit-datetime-btn"
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    Upravit
                  </Button>
                )}
              </div>
              
              {editMode === 'datetime' ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs text-gray-500">Datum</Label>
                      <Input
                        type="date"
                        value={editData.date}
                        onChange={(e) => setEditData({ ...editData, date: e.target.value })}
                        data-testid="edit-date-input"
                      />
                    </div>
                    <div>
                      <Label className="text-xs text-gray-500">Časový blok</Label>
                      <Input
                        type="text"
                        value={editData.time_block}
                        onChange={(e) => setEditData({ ...editData, time_block: e.target.value })}
                        placeholder="09:00-10:30"
                        data-testid="edit-time-input"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <Button size="sm" variant="outline" onClick={() => setEditMode(null)}>Zrušit</Button>
                    <Button size="sm" onClick={updateBooking} className="bg-slate-800 text-white" data-testid="save-datetime-btn">
                      Uložit
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Datum:</span>
                    <p className="font-medium">{selectedBooking.date}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Časový blok:</span>
                    <p className="font-medium">{selectedBooking.time_block}</p>
                  </div>
                </div>
              )}
            </Card>

            {/* Počet účastníků */}
            <Card className="p-4">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Users className="w-5 h-5" />
                Počet účastníků
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-sm">
                  <span className="text-gray-500">Rezervováno studentů:</span>
                  <p className="font-medium text-lg">{selectedBooking.num_students}</p>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">Rezervováno pedagogů:</span>
                  <p className="font-medium text-lg">{selectedBooking.num_teachers || 1}</p>
                </div>
              </div>

              {/* Skutečná účast */}
              {(selectedBooking.status === 'confirmed' || selectedBooking.status === 'completed') && (
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-slate-700">Skutečná účast</span>
                    {canEditAttendance && editMode !== 'attendance' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setEditMode('attendance')}
                        data-testid="edit-attendance-btn"
                      >
                        <Edit className="w-4 h-4 mr-1" />
                        Upravit
                      </Button>
                    )}
                  </div>

                  {editMode === 'attendance' ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs text-gray-500">Skutečný počet studentů</Label>
                          <Input
                            type="number"
                            value={editData.actual_students}
                            onChange={(e) => setEditData({ ...editData, actual_students: parseInt(e.target.value) || 0 })}
                            data-testid="actual-students-input"
                          />
                        </div>
                        <div>
                          <Label className="text-xs text-gray-500">Skutečný počet pedagogů</Label>
                          <Input
                            type="number"
                            value={editData.actual_teachers}
                            onChange={(e) => setEditData({ ...editData, actual_teachers: parseInt(e.target.value) || 0 })}
                            data-testid="actual-teachers-input"
                          />
                        </div>
                      </div>
                      <div className="flex gap-2 justify-end">
                        <Button size="sm" variant="outline" onClick={() => setEditMode(null)}>Zrušit</Button>
                        <Button size="sm" onClick={updateBooking} className="bg-slate-800 text-white" data-testid="save-attendance-btn">
                          Uložit
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-green-50 p-3 rounded-lg">
                        <span className="text-xs text-gray-500 block">Dorazilo studentů</span>
                        <span className="text-xl font-bold text-green-700">
                          {selectedBooking.actual_students ?? '-'}
                        </span>
                      </div>
                      <div className="bg-green-50 p-3 rounded-lg">
                        <span className="text-xs text-gray-500 block">Dorazilo pedagogů</span>
                        <span className="text-xl font-bold text-green-700">
                          {selectedBooking.actual_teachers ?? '-'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* Kontaktní údaje - editable */}
            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                  <User className="w-5 h-5" />
                  Kontaktní údaje
                </h3>
                {canEditContact && editMode !== 'contact' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditMode('contact')}
                    data-testid="edit-contact-btn"
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    Upravit
                  </Button>
                )}
              </div>
              
              {editMode === 'contact' ? (
                <div className="space-y-3">
                  <div>
                    <Label className="text-xs text-gray-500">Jméno kontaktu</Label>
                    <Input
                      value={editData.contact_name}
                      onChange={(e) => setEditData({ ...editData, contact_name: e.target.value })}
                      data-testid="edit-contact-name"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">Email</Label>
                    <Input
                      type="email"
                      value={editData.contact_email}
                      onChange={(e) => setEditData({ ...editData, contact_email: e.target.value })}
                      data-testid="edit-contact-email"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">Telefon</Label>
                    <Input
                      value={editData.contact_phone}
                      onChange={(e) => setEditData({ ...editData, contact_phone: e.target.value })}
                      data-testid="edit-contact-phone"
                    />
                  </div>
                  <div className="flex gap-2 justify-end">
                    <Button size="sm" variant="outline" onClick={() => setEditMode(null)}>Zrušit</Button>
                    <Button size="sm" onClick={updateBooking} className="bg-slate-800 text-white" data-testid="save-contact-btn">
                      Uložit
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span>{selectedBooking.contact_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-gray-400" />
                    <a href={`mailto:${selectedBooking.contact_email}`} className="text-blue-600 hover:underline">
                      {selectedBooking.contact_email}
                    </a>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-gray-400" />
                    <a href={`tel:${selectedBooking.contact_phone}`} className="text-blue-600 hover:underline">
                      {selectedBooking.contact_phone}
                    </a>
                  </div>
                </div>
              )}
            </Card>

            {/* Přiřazený lektor */}
            <Card className="p-4">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <UserPlus className="w-5 h-5" />
                Přiřazený lektor
              </h3>
              
              {hasAssignedLecturer ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-slate-600" />
                    </div>
                    <div>
                      <p className="font-medium">{selectedBooking.assigned_lecturer_name}</p>
                      <p className="text-xs text-gray-500">
                        Přiřazen: {selectedBooking.assigned_lecturer_at ? new Date(selectedBooking.assigned_lecturer_at).toLocaleString('cs-CZ') : '-'}
                      </p>
                      {selectedBooking.assignment_source && (
                        <p className="text-xs mt-1">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                              selectedBooking.assignment_source === 'default_program' ? 'bg-emerald-50 text-emerald-700' :
                              selectedBooking.assignment_source === 'auto_suggest' ? 'bg-sky-50 text-sky-700' :
                              selectedBooking.assignment_source === 'manual_admin' ? 'bg-amber-50 text-amber-700' :
                              'bg-slate-100 text-slate-600'
                            }`}
                            data-testid="assignment-source-badge"
                          >
                            {selectedBooking.assignment_source === 'default_program' ? 'Výchozí lektor programu' :
                             selectedBooking.assignment_source === 'auto_suggest' ? 'Auto-výběr' :
                             selectedBooking.assignment_source === 'manual_admin' ? 'Ručně přiřazeno' :
                             selectedBooking.assignment_source}
                          </span>
                        </p>
                      )}
                      {selectedBooking.assignment_reason && (
                        <p className="text-xs text-slate-500 mt-1" data-testid="assignment-reason">
                          {selectedBooking.assignment_reason}
                        </p>
                      )}
                    </div>
                  </div>
                  {(permissions.canEditAll || isAssignedToMe) && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={unassignLecturer}
                      className="text-red-600 hover:bg-red-50"
                      data-testid="unassign-lecturer-btn"
                    >
                      <UserMinus className="w-4 h-4 mr-1" />
                      Odhlásit
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-gray-500 text-sm">Žádný lektor není přiřazen</p>
                  
                  {/* Admin can assign specific lecturer from dropdown */}
                  {permissions.canEditAll && teamMembers.length > 0 && (
                    <div className="flex gap-2 items-end">
                      <div className="flex-1">
                        <Label className="text-xs text-gray-500 mb-1 block">Vybrat lektora</Label>
                        <Select value={selectedLecturer} onValueChange={setSelectedLecturer}>
                          <SelectTrigger data-testid="select-lecturer-dropdown">
                            <SelectValue placeholder="Vyberte lektora..." />
                          </SelectTrigger>
                          <SelectContent>
                            {teamMembers
                              .filter(m => (m.lecturer_mode || 'main') === 'main')
                              .map(member => (
                                <SelectItem key={member.id} value={member.id}>
                                  {member.name || member.email}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => assignLecturerByAdmin(selectedLecturer)}
                        disabled={!selectedLecturer}
                        className="bg-slate-800 text-white"
                        data-testid="assign-selected-lecturer-btn"
                      >
                        <UserPlus className="w-4 h-4 mr-1" />
                        Přiřadit
                      </Button>
                    </div>
                  )}
                  
                  {/* Self-assign button for lecturers */}
                  {(currentUserRole === 'lektor' || currentUserRole === 'edukator') && !permissions.canEditAll && (
                    <Button
                      size="sm"
                      onClick={assignLecturer}
                      className="bg-slate-800 text-white"
                      data-testid="assign-lecturer-btn"
                    >
                      <UserPlus className="w-4 h-4 mr-1" />
                      Přihlásit se
                    </Button>
                  )}
                </div>
              )}
            </Card>

            {/* Poznámky */}
            {selectedBooking.special_requirements && (
              <Card className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  Speciální požadavky
                </h3>
                <p className="text-sm text-gray-700">{selectedBooking.special_requirements}</p>
              </Card>
            )}

            {/* Interní poznámky */}
            {permissions.canEditAll && (
              <Card className="p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Interní poznámky</h3>
                {editMode === 'notes' ? (
                  <div className="space-y-3">
                    <Textarea
                      value={editData.notes}
                      onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                      placeholder="Přidejte interní poznámku..."
                      rows={3}
                      data-testid="notes-textarea"
                    />
                    <div className="flex gap-2 justify-end">
                      <Button size="sm" variant="outline" onClick={() => setEditMode(null)}>Zrušit</Button>
                      <Button size="sm" onClick={updateBooking} className="bg-slate-800 text-white">Uložit</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-700">{selectedBooking.notes || 'Žádné poznámky'}</p>
                    <Button size="sm" variant="ghost" onClick={() => setEditMode('notes')}>
                      <Edit className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </Card>
            )}

            {/* Souhlas s podmínkami */}
            {selectedBooking.terms_accepted !== undefined && (
              <Card className="p-4 bg-gray-50" data-testid="terms-acceptance-card">
                <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  Souhlas s podmínkami
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">Souhlas udělen:</span>
                    <span className={`font-medium ${selectedBooking.terms_accepted ? 'text-green-600' : 'text-red-600'}`}>
                      {selectedBooking.terms_accepted ? 'Ano' : 'Ne'}
                    </span>
                  </div>
                  {selectedBooking.terms_accepted_at && (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">Datum a čas:</span>
                      <span className="font-medium">
                        {new Date(selectedBooking.terms_accepted_at).toLocaleString('cs-CZ')}
                      </span>
                    </div>
                  )}
                  {selectedBooking.terms_accepted_text_version && (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">Verze podmínek:</span>
                      <span className="font-medium">{selectedBooking.terms_accepted_text_version}</span>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Outlook export */}
            <div className="pt-3 border-t">
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => {
                  downloadReservationIcs(selectedBooking.id, localStorage.getItem('token'));
                  toast.success('ICS soubor se stahuje');
                }}
                data-testid="add-to-outlook-btn"
              >
                <Download className="w-4 h-4 mr-2" />
                Přidat do Outlooku (.ics)
              </Button>
            </div>

            {/* Akce */}
            <div className="flex gap-2 pt-4 border-t">
              {selectedBooking.status === 'pending' && permissions.canEditAll && (
                <>
                  <Button
                    onClick={() => updateStatus(selectedBooking.id, 'confirmed')}
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                    data-testid="confirm-booking-modal"
                  >
                    <Check className="w-4 h-4 mr-2" />
                    Potvrdit rezervaci
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => updateStatus(selectedBooking.id, 'cancelled')}
                    className="flex-1 text-red-600 hover:bg-red-50"
                    data-testid="cancel-booking-modal"
                  >
                    <X className="w-4 h-4 mr-2" />
                    Zrušit rezervaci
                  </Button>
                </>
              )}
              {selectedBooking.status === 'confirmed' && permissions.canEditAll && (
                <Button
                  onClick={() => updateStatus(selectedBooking.id, 'completed')}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                  data-testid="complete-booking-modal"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Označit jako dokončené
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900">Rezervace</h1>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin/waitlist')}
              data-testid="bookings-waitlist-btn"
            >
              <Bell className="w-4 h-4 mr-1.5" />
              <span className="hidden sm:inline">Zájemci</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const instId = user?.institution_id;
                if (instId) {
                  downloadIcs('institution', instId, localStorage.getItem('token'));
                  toast.success('ICS feed se stahuje');
                }
              }}
              data-testid="export-ics-feed-btn"
            >
              <CalendarPlus className="w-4 h-4 mr-1.5" />
              <span className="hidden sm:inline">Outlook kalendář</span>
            </Button>
            <Badge variant="outline" className="text-sm">
              Role: {currentUserRole}
            </Badge>
          </div>
        </div>

        {/* Filters & Search */}
        {!loading && bookings.length > 0 && (
          <div className="space-y-3">
            {/* Status filter tabs */}
            <div className="flex flex-wrap gap-2" data-testid="status-filter-bar">
              {[
                { key: 'all', label: 'Vše' },
                { key: 'pending', label: 'Čekající' },
                { key: 'confirmed', label: 'Potvrzené' },
                { key: 'cancelled', label: 'Zrušené' },
                { key: 'completed', label: 'Dokončené' },
              ].map(f => (
                <Button
                  key={f.key}
                  size="sm"
                  variant={statusFilter === f.key ? 'default' : 'outline'}
                  onClick={() => { setStatusFilter(f.key); setSelectedIds(new Set()); }}
                  className={statusFilter === f.key ? 'bg-slate-800 text-white' : ''}
                  data-testid={`filter-${f.key}`}
                >
                  {f.label}
                  <span className="ml-1.5 text-xs opacity-70">({statusCounts[f.key]})</span>
                </Button>
              ))}
            </div>
            {/* Search */}
            <Input
              placeholder="Hledat podle školy, kontaktu, programu..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="max-w-md"
              data-testid="booking-search-input"
            />
          </div>
        )}

        {/* Bulk action bar */}
        {selectedIds.size > 0 && permissions.canEditAll && (
          <Card className="p-3 bg-slate-50 border-slate-300 sticky top-0 z-10" data-testid="bulk-action-bar">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-slate-700" data-testid="selected-count">
                Vybráno: {selectedIds.size}
              </span>
              <div className="h-5 w-px bg-slate-300" />
              <Button
                size="sm"
                onClick={() => bulkUpdateStatus('confirmed')}
                disabled={bulkLoading}
                className="bg-green-600 hover:bg-green-700 text-white"
                data-testid="bulk-confirm-btn"
              >
                <Check className="w-4 h-4 mr-1" />
                Potvrdit vybrané
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => bulkUpdateStatus('cancelled')}
                disabled={bulkLoading}
                className="text-red-600 hover:bg-red-50 border-red-200"
                data-testid="bulk-cancel-btn"
              >
                <X className="w-4 h-4 mr-1" />
                Zrušit vybrané
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => bulkUpdateStatus('completed')}
                disabled={bulkLoading}
                className="text-blue-600 hover:bg-blue-50 border-blue-200"
                data-testid="bulk-complete-btn"
              >
                <Check className="w-4 h-4 mr-1" />
                Dokončit vybrané
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelectedIds(new Set())}
                data-testid="bulk-clear-btn"
              >
                Zrušit výběr
              </Button>
            </div>
          </Card>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto"></div>
          </div>
        ) : bookings.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-gray-500">Zatím nemáte žádné rezervace</p>
          </Card>
        ) : filteredBookings.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-gray-500">Žádné rezervace neodpovídají filtru</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {/* Select all row */}
            {permissions.canEditAll && filteredBookings.length > 1 && (
              <div className="flex items-center gap-3 px-2">
                <button
                  onClick={toggleSelectAll}
                  className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 transition-colors"
                  data-testid="select-all-btn"
                >
                  {selectedIds.size === filteredBookings.length ? (
                    <CheckSquare className="w-5 h-5 text-slate-800" />
                  ) : (
                    <Square className="w-5 h-5" />
                  )}
                  {selectedIds.size === filteredBookings.length ? 'Odznačit vše' : 'Vybrat vše'}
                </button>
                <span className="text-xs text-slate-400">({filteredBookings.length} rezervací)</span>
              </div>
            )}

            {filteredBookings.map((booking) => (
              <Card 
                key={booking.id} 
                className={`p-4 md:p-6 cursor-pointer hover:shadow-md transition-shadow ${selectedIds.has(booking.id) ? 'ring-2 ring-slate-400 bg-slate-50' : ''}`}
                data-testid={`booking-card-${booking.id}`}
                onClick={() => openDetail(booking)}
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Checkbox */}
                    {permissions.canEditAll && (
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleSelect(booking.id); }}
                        className="mt-1 flex-shrink-0"
                        data-testid={`select-booking-${booking.id}`}
                      >
                        {selectedIds.has(booking.id) ? (
                          <CheckSquare className="w-5 h-5 text-slate-800" />
                        ) : (
                          <Square className="w-5 h-5 text-slate-400" />
                        )}
                      </button>
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-slate-900">{booking.program_name || 'Program'}</h3>
                        {getStatusBadge(booking.status)}
                        {booking.assigned_lecturer_name && (
                          <Badge variant="outline" className="text-xs">
                            <User className="w-3 h-3 mr-1" />
                            {booking.assigned_lecturer_name}
                          </Badge>
                        )}
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                        <div className="min-w-0">
                          <span className="text-gray-500 block">Škola:</span>
                          <span className="font-medium truncate block" title={booking.school_name}>{booking.school_name}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Datum:</span>
                          <span className="font-medium">{booking.date}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Čas:</span>
                          <span className="font-medium">{booking.time_block}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Studentů:</span>
                          <span className="font-medium">
                            {booking.actual_students ?? booking.num_students}
                            {booking.actual_students !== null && booking.actual_students !== undefined && (
                              <span className="text-xs text-gray-400 ml-1">
                                (z {booking.num_students})
                              </span>
                            )}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 block">Kontakt:</span>
                          <span className="font-medium">{booking.contact_name}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openDetail(booking)}
                      data-testid={`view-booking-${booking.id}`}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      Detail
                    </Button>
                    {booking.status === 'pending' && permissions.canEditAll && (
                      <>
                        <Button
                          size="sm"
                          data-testid={`confirm-booking-${booking.id}`}
                          onClick={() => updateStatus(booking.id, 'confirmed')}
                          className="bg-green-600 hover:bg-green-700 text-white"
                        >
                          <Check className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          data-testid={`cancel-booking-${booking.id}`}
                          onClick={() => updateStatus(booking.id, 'cancelled')}
                          className="text-red-600 hover:bg-red-50"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {renderDetailModal()}
    </AdminLayout>
  );
};
