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
  AlertTriangle,
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
  Eye,
  User
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

// Parse a time block string like "10:00-11:00" or "10:00" → {start: 10*60, end: 11*60}.
const parseTimeRange = (tb) => {
  if (!tb) return null;
  const m = String(tb).match(/^(\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?$/);
  if (!m) return null;
  const start = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
  const end = m[3] ? parseInt(m[3], 10) * 60 + parseInt(m[4], 10) : start + 60;
  return { start, end };
};

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

  // For each reservation, find any other reservation on the same date whose
  // time range overlaps with this one. If found, the booking is part of a
  // *parallel run* — multiple lecturers handling concurrent programs.
  // We expose this on the card so admins can see WHY the system permitted
  // the booking despite an apparent time clash (different lecturers).
  const overlapsByBookingId = useMemo(() => {
    const map = new Map();
    if (!Array.isArray(reservations)) return map;
    const active = reservations.filter(r => r.status !== 'cancelled');
    const byDate = new Map();
    active.forEach(r => {
      const list = byDate.get(r.date) || [];
      list.push(r);
      byDate.set(r.date, list);
    });
    byDate.forEach(list => {
      for (let i = 0; i < list.length; i++) {
        const a = list[i];
        const ar = parseTimeRange(a.time_block);
        if (!ar) continue;
        for (let j = i + 1; j < list.length; j++) {
          const b = list[j];
          const br = parseTimeRange(b.time_block);
          if (!br) continue;
          if (ar.start < br.end && br.start < ar.end) {
            (map.get(a.id) || map.set(a.id, []).get(a.id)).push(b);
            (map.get(b.id) || map.set(b.id, []).get(b.id)).push(a);
          }
        }
      }
    });
    return map;
  }, [reservations]);

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
          {sortedReservations.map((reservation) => {
            const overlapping = overlapsByBookingId.get(reservation.id) || [];
            return (
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
                      {reservation.assigned_lecturer_name && (
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-[#5a7aae]/10 text-[#5a7aae] font-medium"
                          data-testid={`reservation-lecturer-${reservation.id}`}
                          title="Přiřazený lektor pokrývá tento čas"
                        >
                          <User className="w-3 h-3" />
                          {reservation.assigned_lecturer_name}
                        </span>
                      )}
                    </div>
                    {overlapping.length > 0 && (
                      <div
                        className="mt-2 flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2 py-1.5"
                        data-testid={`reservation-overlap-${reservation.id}`}
                      >
                        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        <div className="leading-snug">
                          <span className="font-medium">Souběh ve stejném čase:</span>{' '}
                          {overlapping.slice(0, 2).map((o, i) => (
                            <span key={o.id}>
                              {i > 0 && ' · '}
                              {o.program_name || 'Program'} ({o.time_block})
                              {o.assigned_lecturer_name
                                ? <> – lektor: <span className="font-medium">{o.assigned_lecturer_name}</span></>
                                : <> – <span className="font-medium text-amber-800">bez přiřazeného lektora</span></>}
                            </span>
                          ))}
                          {overlapping.length > 2 && <span> +{overlapping.length - 2} další</span>}
                          {!reservation.assigned_lecturer_name && (
                            <div className="text-amber-800 mt-0.5">
                              ⚠ Této rezervaci ještě není přiřazen lektor — přiřaďte ho, jinak hrozí dvojitý slot.
                            </div>
                          )}
                        </div>
                      </div>
                    )}
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
            );
          })}
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

  // Get color for reservation based on program — deterministic, distinct hue per program.
  // We return inline-style hex values (NOT Tailwind class names) on purpose:
  // dynamically-built `bg-*-400` strings inside an array literal are unreliable
  // through Tailwind JIT/purge in production builds — some classes get stripped
  // out of the final CSS, which collapsed every program to the same colour.
  const PROGRAM_COLORS = [
    { bg: '#f59e0b', border: '#d97706' }, // amber
    { bg: '#3b82f6', border: '#2563eb' }, // blue
    { bg: '#f43f5e', border: '#e11d48' }, // rose
    { bg: '#10b981', border: '#059669' }, // emerald
    { bg: '#8b5cf6', border: '#7c3aed' }, // violet
    { bg: '#fb923c', border: '#ea580c' }, // orange
    { bg: '#06b6d4', border: '#0891b2' }, // cyan
    { bg: '#d946ef', border: '#c026d3' }, // fuchsia
    { bg: '#84cc16', border: '#65a30d' }, // lime
    { bg: '#ec4899', border: '#db2777' }, // pink
    { bg: '#14b8a6', border: '#0d9488' }, // teal
    { bg: '#6366f1', border: '#4f46e5' }, // indigo
  ];

  const getReservationColor = (reservation) => {
    const key = String(reservation.program_id || reservation.program_name || reservation.id || '');
    // 32-bit FNV-1a hash → strong distribution even on similar program titles.
    let hash = 0x811c9dc5;
    for (let i = 0; i < key.length; i++) {
      hash ^= key.charCodeAt(i);
      hash = (hash + ((hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24))) >>> 0;
    }
    return PROGRAM_COLORS[hash % PROGRAM_COLORS.length];
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
                    {(() => {
                      // Only render the events that *start* in this hour (first row of their slot).
                      const startingHere = reservationsAtTime.filter(isFirstHour);
                      const total = startingHere.length;
                      return startingHere.map((reservation, rIndex) => {
                        const color = getReservationColor(reservation);
                        return (
                        <div
                          key={reservation.id}
                          onClick={() => onSelectReservation(reservation)}
                          className="absolute rounded-md p-2 cursor-pointer text-white text-xs shadow-sm hover:brightness-95 transition-all overflow-hidden"
                          style={{
                            top: '2px',
                            bottom: '2px',
                            left: `calc(${(rIndex / total) * 100}% + 1px)`,
                            width: `calc(${(1 / total) * 100}% - 2px)`,
                            height: 'calc(120px - 4px)',
                            zIndex: rIndex + 1,
                            backgroundColor: color.bg,
                            borderLeft: `4px solid ${color.border}`,
                          }}
                          data-testid={`calendar-event-${reservation.id}`}
                          title={`${reservation.program_name || ''} · ${reservation.time_block || ''}${reservation.assigned_lecturer_name ? ' · ' + reservation.assigned_lecturer_name : ''}`}
                        >
                          <div className="font-semibold truncate leading-tight">
                            {reservation.program_name || reservation.school_name}
                          </div>
                          <div className="opacity-90 truncate text-[10px]">
                            {reservation.time_block || '9:00'}
                          </div>
                          {reservation.assigned_lecturer_name && total <= 2 && (
                            <div className="opacity-90 truncate text-[10px] mt-0.5">
                              {reservation.assigned_lecturer_name}
                            </div>
                          )}
                        </div>
                        );
                      });
                    })()}
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

  // Today's bookings for "Moje rezervace dnes" widget.
  // Visible for: lektor, edukátor, pokladní, admin, spravce.
  // For lektor/edukator: filtered to assigned_lecturer_id == current user.
  // For admin/spravce/pokladni: shows all institution bookings for today.
  const myTodayBookings = useMemo(() => {
    if (!Array.isArray(reservations) || !user) return [];
    const now = new Date();
    const today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    const role = user.role;
    const personalRoles = ['lektor', 'edukator'];
    return reservations
      .filter(b => b.date === today && b.status !== 'cancelled')
      .filter(b => personalRoles.includes(role)
        ? b.assigned_lecturer_id === user.id
        : true
      )
      .sort((a, b) => (a.time_block || '').localeCompare(b.time_block || ''));
  }, [reservations, user]);

  const showTodayWidget = !!user && ['admin','spravce','lektor','edukator','pokladni'].includes(user.role);

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

        {/* Moje rezervace dnes — quick view for lektor/edukator/pokladni/admin.
            Skryto, když nejsou žádné rezervace na dnešek (méně rušení). */}
        {showTodayWidget && myTodayBookings.length > 0 && (
          <Card className="p-6 border-l-4 border-l-[#5a7aae]" data-testid="today-bookings-widget">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#5a7aae]/10 flex items-center justify-center">
                  <CalendarIcon className="w-5 h-5 text-[#5a7aae]" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    {['lektor','edukator'].includes(user?.role) ? 'Moje rezervace dnes' : 'Rezervace dnes'}
                  </h2>
                  <p className="text-xs text-slate-500">
                    {new Date().toLocaleDateString('cs-CZ', { weekday: 'long', day: 'numeric', month: 'long' })}
                  </p>
                </div>
              </div>
              <Badge variant="outline" className="text-[#5a7aae] border-[#5a7aae]/30" data-testid="today-bookings-count">
                {myTodayBookings.length} {myTodayBookings.length === 1 ? 'rezervace' : (myTodayBookings.length >= 2 && myTodayBookings.length <= 4 ? 'rezervace' : 'rezervací')}
              </Badge>
            </div>

            <div className="space-y-2">
              {myTodayBookings.map((b) => (
                <button
                  key={b.id}
                  onClick={() => handleSelectReservation(b)}
                  className="w-full flex items-center gap-3 p-3 bg-slate-50 hover:bg-[#5a7aae]/5 rounded-lg border border-transparent hover:border-[#5a7aae]/20 transition-all text-left group"
                  data-testid={`today-booking-${b.id}`}
                >
                  <div className="w-14 flex-shrink-0 text-center">
                    <div className="text-base font-bold text-[#5a7aae]">
                      {b.time_block || '—'}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 truncate group-hover:text-[#5a7aae] transition-colors">
                      {b.program_name || 'Program'}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      <School className="inline w-3 h-3 mr-1 -mt-0.5" />
                      {b.school_name} · <Users className="inline w-3 h-3 mx-1 -mt-0.5" />{b.num_students || 0} žáků
                    </p>
                  </div>
                  <StatusBadge status={b.status} />
                </button>
              ))}
            </div>
          </Card>
        )}

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
