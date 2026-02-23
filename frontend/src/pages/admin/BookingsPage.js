import React, { useEffect, useState, useContext } from 'react';
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
  AlertCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Role permissions helper
const PERMISSIONS = {
  admin: { canEditAll: true, canEditAttendance: true, canAssignLecturer: true },
  spravce: { canEditAll: true, canEditAttendance: true, canAssignLecturer: true },
  edukator: { canEditAll: true, canEditAttendance: true, canAssignLecturer: true },
  pokladni: { canEditAll: false, canEditAttendance: true, canAssignLecturer: false },
  lektor: { canEditAll: false, canEditAttendance: false, canAssignLecturer: true },
  viewer: { canEditAll: false, canEditAttendance: false, canAssignLecturer: false },
};

export const BookingsPage = () => {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [currentUserRole, setCurrentUserRole] = useState('viewer');
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});

  useEffect(() => {
    fetchBookings();
    fetchCurrentUserRole();
  }, []);

  const fetchBookings = async () => {
    try {
      const response = await axios.get(`${API}/bookings`);
      setBookings(response.data);
    } catch (error) {
      toast.error(t('common.error'));
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

  const getPermissions = () => {
    return PERMISSIONS[currentUserRole] || PERMISSIONS.viewer;
  };

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
      await axios.put(`${API}/bookings/${selectedBooking.id}`, editData);
      toast.success('Rezervace byla aktualizována');
      fetchBookings();
      setSelectedBooking(prev => ({ ...prev, ...editData }));
      setEditMode(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při aktualizaci');
    }
  };

  const assignLecturer = async () => {
    if (!selectedBooking) return;
    
    try {
      const response = await axios.post(`${API}/bookings/${selectedBooking.id}/assign-lecturer`);
      toast.success(`Lektor ${response.data.lecturer_name} byl přiřazen`);
      fetchBookings();
      // Update selected booking
      const updatedBooking = await axios.get(`${API}/bookings/${selectedBooking.id}`);
      setSelectedBooking(updatedBooking.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při přiřazení lektora');
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
      toast.error(error.response?.data?.detail || 'Chyba při odhlášení lektora');
    }
  };

  const openDetail = (booking) => {
    setSelectedBooking(booking);
    setEditData({
      actual_students: booking.actual_students || '',
      actual_teachers: booking.actual_teachers || '',
      notes: booking.notes || '',
    });
    setEditMode(false);
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
    const canAssign = permissions.canAssignLecturer;
    const isAssignedToMe = selectedBooking.assigned_lecturer_id === user?.id;
    const hasAssignedLecturer = !!selectedBooking.assigned_lecturer_id;

    return (
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Detail rezervace</span>
              {getStatusBadge(selectedBooking.status)}
            </DialogTitle>
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

            {/* Datum a čas */}
            <Card className="p-4">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Datum a čas
              </h3>
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

              {/* Skutečná účast - editovatelné pokladním */}
              {(selectedBooking.status === 'confirmed' || selectedBooking.status === 'completed') && (
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-slate-700">Skutečná účast</span>
                    {canEditAttendance && !editMode && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setEditMode(true)}
                        data-testid="edit-attendance-btn"
                      >
                        <Edit className="w-4 h-4 mr-1" />
                        Upravit
                      </Button>
                    )}
                  </div>

                  {editMode && canEditAttendance ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs text-gray-500">Skutečný počet studentů</Label>
                          <Input
                            type="number"
                            value={editData.actual_students}
                            onChange={(e) => setEditData({ ...editData, actual_students: parseInt(e.target.value) || 0 })}
                            placeholder="0"
                            data-testid="actual-students-input"
                          />
                        </div>
                        <div>
                          <Label className="text-xs text-gray-500">Skutečný počet pedagogů</Label>
                          <Input
                            type="number"
                            value={editData.actual_teachers}
                            onChange={(e) => setEditData({ ...editData, actual_teachers: parseInt(e.target.value) || 0 })}
                            placeholder="0"
                            data-testid="actual-teachers-input"
                          />
                        </div>
                      </div>
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditMode(false)}
                        >
                          Zrušit
                        </Button>
                        <Button
                          size="sm"
                          onClick={updateBooking}
                          className="bg-slate-800 text-white"
                          data-testid="save-attendance-btn"
                        >
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

            {/* Kontaktní údaje */}
            <Card className="p-4">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <User className="w-5 h-5" />
                Kontaktní údaje
              </h3>
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
                <div className="flex items-center justify-between">
                  <p className="text-gray-500 text-sm">Žádný lektor není přiřazen</p>
                  {(canAssign || currentUserRole === 'lektor') && (
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
                {editMode ? (
                  <Textarea
                    value={editData.notes}
                    onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                    placeholder="Přidejte interní poznámku..."
                    rows={3}
                    data-testid="notes-textarea"
                  />
                ) : (
                  <p className="text-sm text-gray-700">{selectedBooking.notes || 'Žádné poznámky'}</p>
                )}
              </Card>
            )}

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
          <Badge variant="outline" className="text-sm">
            Role: {currentUserRole}
          </Badge>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto"></div>
          </div>
        ) : bookings.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-gray-500">Zatím nemáte žádné rezervace</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {bookings.map((booking) => (
              <Card 
                key={booking.id} 
                className="p-4 md:p-6 cursor-pointer hover:shadow-md transition-shadow" 
                data-testid={`booking-card-${booking.id}`}
                onClick={() => openDetail(booking)}
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-slate-900">{booking.school_name}</h3>
                      {getStatusBadge(booking.status)}
                      {booking.assigned_lecturer_name && (
                        <Badge variant="outline" className="text-xs">
                          <User className="w-3 h-3 mr-1" />
                          {booking.assigned_lecturer_name}
                        </Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
