/**
 * DashboardPage - Vylepšený dashboard s přepínačem pohledů (Seznam/Kalendář)
 * 
 * Funkce:
 * - Statistické karty
 * - Přepínač mezi Seznam a Kalendář pohledem
 * - Seznam: Filtry (Nadcházející události, Nedávno vytvořené)
 * - Kalendář: Týdenní pohled s rezervacemi
 */
import React, { useEffect, useState, useContext, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { AuthContext } from '../../context/AuthContext';
import axios from 'axios';
import { 
  Calendar as CalendarIcon, 
  Users, 
  TrendingUp, 
  AlertCircle,
  List,
  LayoutGrid,
  ChevronLeft,
  ChevronRight,
  Clock,
  MapPin,
  School,
  CheckCircle,
  XCircle,
  Loader2,
  Eye
} from 'lucide-react';
import { API } from '../../config/api';
import { OnboardingWizard } from '../../components/admin/OnboardingWizard';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';

// ============ ViewSwitcher Component ============
const ViewSwitcher = ({ view, onViewChange }) => (
  <div className="flex bg-gray-100 rounded-lg p-1" data-testid="view-switcher">
    <button
      onClick={() => onViewChange('list')}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
        view === 'list'
          ? 'bg-white text-gray-900 shadow-sm'
          : 'text-gray-500 hover:text-gray-700'
      }`}
      data-testid="view-list-btn"
    >
      <List className="w-4 h-4" />
      Seznam
    </button>
    <button
      onClick={() => onViewChange('calendar')}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
        view === 'calendar'
          ? 'bg-white text-gray-900 shadow-sm'
          : 'text-gray-500 hover:text-gray-700'
      }`}
      data-testid="view-calendar-btn"
    >
      <LayoutGrid className="w-4 h-4" />
      Kalendář
    </button>
  </div>
);

// ============ Status Badge Component ============
const StatusBadge = ({ status }) => {
  const statusConfig = {
    confirmed: { label: 'Potvrzeno', class: 'bg-green-100 text-green-800', icon: CheckCircle },
    pending: { label: 'Čeká', class: 'bg-yellow-100 text-yellow-800', icon: Clock },
    cancelled: { label: 'Zrušeno', class: 'bg-red-100 text-red-800', icon: XCircle },
    completed: { label: 'Dokončeno', class: 'bg-blue-100 text-blue-800', icon: CheckCircle },
  };
  
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.class}`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
};

// ============ ReservationList Component ============
const ReservationList = ({ reservations, filter, onFilterChange, onSelectReservation }) => {
  const sortedReservations = useMemo(() => {
    if (!Array.isArray(reservations)) return [];
    
    const sorted = [...reservations];
    if (filter === 'upcoming') {
      // Sort by event date (ascending - nearest first)
      sorted.sort((a, b) => new Date(a.date) - new Date(b.date));
    } else {
      // Sort by creation date (descending - newest first)
      sorted.sort((a, b) => new Date(b.created_at || b.date) - new Date(a.created_at || a.date));
    }
    return sorted;
  }, [reservations, filter]);

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('cs-CZ', { 
        weekday: 'short', 
        day: 'numeric', 
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      {/* Filter Controls */}
      <div className="flex items-center justify-between">
        <Select value={filter} onValueChange={onFilterChange}>
          <SelectTrigger className="w-[220px]" data-testid="list-filter-select">
            <SelectValue placeholder="Seřadit podle" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="upcoming">Nadcházející události</SelectItem>
            <SelectItem value="recent">Nedávno vytvořené</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-gray-500">
          {sortedReservations.length} rezervací
        </span>
      </div>

      {/* Reservations List */}
      {sortedReservations.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <CalendarIcon className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p>Žádné rezervace k zobrazení</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedReservations.map((reservation) => (
            <div
              key={reservation.id}
              className="bg-white border rounded-xl p-4 hover:shadow-md transition-all cursor-pointer group"
              onClick={() => onSelectReservation(reservation)}
              data-testid={`reservation-card-${reservation.id}`}
            >
              <div className="flex items-start justify-between gap-4">
                {/* Left: Date & Time */}
                <div className="flex items-start gap-4">
                  <div className="bg-[#5a7aae]/10 rounded-lg p-3 text-center min-w-[70px]">
                    <div className="text-2xl font-bold text-[#5a7aae]">
                      {new Date(reservation.date).getDate()}
                    </div>
                    <div className="text-xs text-[#5a7aae] uppercase">
                      {new Date(reservation.date).toLocaleDateString('cs-CZ', { month: 'short' })}
                    </div>
                  </div>
                  
                  {/* Middle: Details */}
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 group-hover:text-[#5a7aae] transition-colors">
                      {reservation.program_name || 'Program'}
                    </h3>
                    <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <School className="w-4 h-4" />
                        {reservation.school_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {reservation.time_block || '9:00'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        {reservation.num_students || 0} žáků
                      </span>
                    </div>
                  </div>
                </div>

                {/* Right: Status & Actions */}
                <div className="flex flex-col items-end gap-2">
                  <StatusBadge status={reservation.status} />
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    Detail
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ============ WeekCalendar Component ============
const WeekCalendar = ({ reservations, currentDate, onDateChange, onSelectReservation }) => {
  // Generate week days
  const weekDays = useMemo(() => {
    const days = [];
    const startOfWeek = new Date(currentDate);
    const dayOfWeek = startOfWeek.getDay();
    // Adjust to Monday start
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    startOfWeek.setDate(startOfWeek.getDate() + diff);
    
    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + i);
      days.push(day);
    }
    return days;
  }, [currentDate]);

  // Get reservations for a specific date
  const getReservationsForDate = (date) => {
    if (!Array.isArray(reservations)) return [];
    const dateStr = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    return reservations.filter(r => r.date === dateStr);
  };

  // Time slots (8AM - 7PM)
  const timeSlots = useMemo(() => {
    const slots = [];
    for (let hour = 8; hour <= 19; hour++) {
      slots.push(`${hour}:00`);
    }
    return slots;
  }, []);

  // Navigate week
  const goToPreviousWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - 7);
    onDateChange(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + 7);
    onDateChange(newDate);
  };

  const goToToday = () => {
    onDateChange(new Date());
  };

  // Format month/year for header
  const monthYear = currentDate.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' });

  // Day names in Czech
  const dayNames = ['PO', 'ÚT', 'ST', 'ČT', 'PÁ', 'SO', 'NE'];

  // Get color for reservation based on program or status
  const getReservationColor = (reservation) => {
    const colors = [
      'bg-amber-400 border-amber-500',
      'bg-blue-400 border-blue-500',
      'bg-rose-400 border-rose-500',
      'bg-emerald-400 border-emerald-500',
      'bg-purple-400 border-purple-500',
      'bg-orange-400 border-orange-500',
    ];
    // Simple hash based on program name or id
    const hash = (reservation.program_id || reservation.program_name || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  // Parse time to get hour
  const getHourFromTime = (timeStr) => {
    if (!timeStr) return 9;
    const parts = timeStr.split(':');
    return parseInt(parts[0], 10) || 9;
  };

  return (
    <div className="space-y-4" data-testid="week-calendar">
      {/* Calendar Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={goToToday}
            className="px-4"
          >
            Dnes
          </Button>
          <Button variant="ghost" size="sm" onClick={goToPreviousWeek}>
            <ChevronLeft className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="sm" onClick={goToNextWeek}>
            <ChevronRight className="w-5 h-5" />
          </Button>
          <span className="text-lg font-semibold capitalize ml-2">
            {monthYear}
          </span>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-white border rounded-xl overflow-hidden">
        {/* Days Header */}
        <div className="grid grid-cols-8 border-b">
          <div className="p-3 text-xs text-gray-500 font-medium border-r">
            GMT+01
          </div>
          {weekDays.map((day, index) => {
            const isToday = day.toDateString() === new Date().toDateString();
            const hasReservations = getReservationsForDate(day).length > 0;
            
            return (
              <div 
                key={index} 
                className={`p-3 text-center border-r last:border-r-0 ${isToday ? 'bg-blue-50' : ''}`}
              >
                <div className="text-xs text-gray-500 font-medium">{dayNames[index]}</div>
                <div className={`text-2xl font-semibold ${isToday ? 'text-blue-600' : 'text-gray-900'}`}>
                  {day.getDate()}
                </div>
                {hasReservations && (
                  <div className="w-1.5 h-1.5 rounded-full bg-[#5a7aae] mx-auto mt-1"></div>
                )}
              </div>
            );
          })}
        </div>

        {/* Time Slots */}
        <div className="max-h-[500px] overflow-y-auto">
          {timeSlots.map((time, timeIndex) => (
            <div key={time} className="grid grid-cols-8 border-b last:border-b-0 min-h-[60px]">
              <div className="p-2 text-xs text-gray-500 border-r flex items-start justify-end pr-2">
                {time}
              </div>
              {weekDays.map((day, dayIndex) => {
                const dayReservations = getReservationsForDate(day);
                const hour = parseInt(time.split(':')[0], 10);
                const reservationsAtTime = dayReservations.filter(r => {
                  const startHour = getHourFromTime(r.time_block);
                  // Assume 2-hour duration for display
                  return hour >= startHour && hour < startHour + 2;
                });
                
                const isFirstHour = (r) => getHourFromTime(r.time_block) === hour;
                
                return (
                  <div 
                    key={dayIndex} 
                    className="border-r last:border-r-0 p-0.5 relative"
                  >
                    {reservationsAtTime.map((reservation, rIndex) => (
                      isFirstHour(reservation) && (
                        <div
                          key={reservation.id}
                          onClick={() => onSelectReservation(reservation)}
                          className={`absolute inset-x-0.5 rounded-md p-2 cursor-pointer text-white text-xs shadow-sm border-l-4 ${getReservationColor(reservation)} hover:brightness-95 transition-all`}
                          style={{
                            top: '2px',
                            height: 'calc(120px - 4px)',
                            zIndex: rIndex + 1
                          }}
                          data-testid={`calendar-event-${reservation.id}`}
                        >
                          <div className="font-semibold truncate">
                            {reservation.program_name || reservation.school_name}
                          </div>
                          <div className="opacity-90 truncate">
                            {reservation.time_block || '9:00'}
                          </div>
                        </div>
                      )
                    ))}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============ ReservationDetail Modal ============
const ReservationDetailModal = ({ reservation, open, onClose }) => {
  if (!reservation) return null;

  const formatDate = (dateStr) => {
    try {
      return new Date(dateStr).toLocaleDateString('cs-CZ', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Detail rezervace</span>
            <StatusBadge status={reservation.status} />
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {/* Program */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-lg text-gray-900">
              {reservation.program_name || 'Program'}
            </h3>
            <p className="text-gray-500 text-sm mt-1">
              {formatDate(reservation.date)} • {reservation.time_block || '9:00'}
            </p>
          </div>

          {/* School Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 uppercase">Škola</label>
              <p className="font-medium">{reservation.school_name}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase">Typ skupiny</label>
              <p className="font-medium">{reservation.group_type || '-'}</p>
            </div>
          </div>

          {/* Participants */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-gray-500 uppercase">Žáci</label>
              <p className="font-medium">{reservation.num_students || 0}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase">Učitelé</label>
              <p className="font-medium">{reservation.num_teachers || 0}</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase">Třída/Věk</label>
              <p className="font-medium">{reservation.age_or_class || '-'}</p>
            </div>
          </div>

          {/* Contact */}
          <div className="border-t pt-4">
            <label className="text-xs text-gray-500 uppercase">Kontakt</label>
            <p className="font-medium">{reservation.contact_name}</p>
            <p className="text-sm text-gray-500">{reservation.contact_email}</p>
            {reservation.contact_phone && (
              <p className="text-sm text-gray-500">{reservation.contact_phone}</p>
            )}
          </div>

          {/* Special Requirements */}
          {reservation.special_requirements && (
            <div className="border-t pt-4">
              <label className="text-xs text-gray-500 uppercase">Speciální požadavky</label>
              <p className="text-sm">{reservation.special_requirements}</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Zavřít
          </Button>
          <Button 
            className="bg-[#5a7aae] hover:bg-[#4a6a9e]"
            onClick={() => window.location.href = `/admin/bookings`}
          >
            Spravovat rezervace
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ============ Main DashboardPage ============
export const DashboardPage = () => {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  
  const [stats, setStats] = useState(null);
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // View state
  const [view, setView] = useState('list');
  const [listFilter, setListFilter] = useState('upcoming');
  const [calendarDate, setCalendarDate] = useState(new Date());
  
  // Modal state
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Onboarding state
  const [onboardingData, setOnboardingData] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    fetchData();
    fetchOnboardingStatus();
  }, []);

  const fetchOnboardingStatus = async () => {
    try {
      const res = await axios.get(`${API}/onboarding/status`);
      if (!res.data.completed) {
        setOnboardingData(res.data);
        setShowOnboarding(true);
      }
    } catch {
      // silently ignore - don't block dashboard
    }
  };

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      
      const [statsRes, bookingsRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats`, { headers }),
        axios.get(`${API}/bookings`, { headers })
      ]);
      
      setStats(statsRes.data);
      
      // Normalize and filter upcoming/active reservations
      const allBookings = Array.isArray(bookingsRes.data) ? bookingsRes.data : [];
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
      const upcomingBookings = allBookings.filter(b => 
        b.date >= today && b.status !== 'cancelled'
      );
      setReservations(upcomingBookings);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectReservation = (reservation) => {
    setSelectedReservation(reservation);
    setModalOpen(true);
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-[#5a7aae]" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6" data-testid="dashboard-page">
        {/* Onboarding Wizard */}
        {showOnboarding && (
          <Card className="p-6 md:p-8 border-2 border-[#5a7aae]/20 bg-white" data-testid="onboarding-card">
            <OnboardingWizard
              onboardingData={onboardingData}
              onComplete={() => setShowOnboarding(false)}
            />
          </Card>
        )}

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{t('dashboard.welcome')}</h1>
          <p className="text-muted-foreground mt-1">{user?.institution_name}</p>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="p-6" data-testid="dashboard-today-bookings">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.todayBookings')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats?.today_bookings || 0}</p>
              </div>
              <div className="w-12 h-12 bg-[#84A98C] rounded-full flex items-center justify-center">
                <CalendarIcon className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="p-6" data-testid="dashboard-upcoming-groups">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.upcomingGroups')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats?.upcoming_groups || 0}</p>
              </div>
              <div className="w-12 h-12 bg-[#E9C46A] rounded-full flex items-center justify-center">
                <Users className="w-6 h-6 text-slate-900" />
              </div>
            </div>
          </Card>

          <Card className="p-6" data-testid="dashboard-capacity-usage">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.capacityUsage')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">{stats?.capacity_usage?.toFixed(0) || 0}%</p>
              </div>
              <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="p-6" data-testid="dashboard-booking-limit">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('dashboard.bookingLimit')}</p>
                <p className="text-3xl font-bold text-slate-900 mt-2">
                  {stats?.bookings_used || 0}/{stats?.bookings_limit || 50}
                </p>
              </div>
              <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>
        </div>

        {/* Reservations Section */}
        <Card className="p-6">
          {/* Section Header with View Switcher */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <h2 className="text-xl font-semibold text-slate-900">
              Nadcházející rezervace
            </h2>
            <ViewSwitcher view={view} onViewChange={setView} />
          </div>

          {/* View Content with Transition */}
          <div className="transition-all duration-300">
            {view === 'list' ? (
              <ReservationList
                reservations={reservations}
                filter={listFilter}
                onFilterChange={setListFilter}
                onSelectReservation={handleSelectReservation}
              />
            ) : (
              <WeekCalendar
                reservations={reservations}
                currentDate={calendarDate}
                onDateChange={setCalendarDate}
                onSelectReservation={handleSelectReservation}
              />
            )}
          </div>
        </Card>
      </div>

      {/* Reservation Detail Modal */}
      <ReservationDetailModal
        reservation={selectedReservation}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </AdminLayout>
  );
};
