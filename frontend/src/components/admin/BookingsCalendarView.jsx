import React, { useEffect, useMemo, useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  PROGRAM_CALENDAR_COLORS,
  programCalendarKey,
  buildProgramCalendarColorMap,
} from './programCalendarColors';

const toDateKey = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

const startOfWeek = (date) => {
  const result = new Date(date);
  const day = result.getDay();
  result.setDate(result.getDate() + (day === 0 ? -6 : 1 - day));
  result.setHours(0, 0, 0, 0);
  return result;
};

const addDays = (date, amount) => {
  const result = new Date(date);
  result.setDate(result.getDate() + amount);
  return result;
};

const parseTimeRange = (value) => {
  const match = String(value || '').match(/^(\d{1,2}):(\d{2})(?:\s*-\s*(\d{1,2}):(\d{2}))?$/);
  if (!match) return { start: 9 * 60, end: 10 * 60 };
  const start = Number(match[1]) * 60 + Number(match[2]);
  const end = match[3] ? Number(match[3]) * 60 + Number(match[4]) : start + 60;
  return { start, end };
};

const CalendarEvent = ({ booking, onSelect, collision, color, className = '', style = {} }) => (
  <button
    type="button"
    onClick={() => onSelect(booking)}
    className={`w-full rounded-md border px-2 py-1.5 text-left text-xs transition hover:brightness-95 ${className} ${
      collision ? 'ring-2 ring-orange-400' : ''
    } ${booking.status === 'cancelled' ? 'opacity-60' : ''}`}
    style={{ backgroundColor: color.bg, borderColor: color.border, color: color.text, ...style }}
    data-testid={`booking-calendar-event-${booking.id}`}
    title={`${booking.program_name || 'Program'} · ${booking.school_name || ''} · ${booking.time_block || ''}`}
  >
    <span className="block font-semibold truncate">{booking.time_block || '—'} · {booking.program_name || 'Program'}</span>
    <span className="block truncate opacity-80">{booking.school_name || booking.contact_name || '—'}</span>
    {booking.assigned_lecturer_name && <span className="block truncate opacity-70">{booking.assigned_lecturer_name}</span>}
  </button>
);

export const BookingsCalendarView = ({ bookings, colorBookings = bookings, onSelectBooking, collisionIndex, focusDate, focusRequestId }) => {
  const [mode, setMode] = useState('week');
  const [anchorDate, setAnchorDate] = useState(new Date());
  useEffect(() => {
    if (!focusDate) return;
    const next = new Date(`${focusDate}T12:00:00`);
    if (!Number.isNaN(next.getTime())) setAnchorDate(next);
  }, [focusDate, focusRequestId]);
  const byDate = useMemo(() => {
    const map = new Map();
    bookings.forEach((booking) => {
      const items = map.get(booking.date) || [];
      items.push(booking);
      map.set(booking.date, items);
    });
    map.forEach((items) => items.sort((a, b) => (a.time_block || '').localeCompare(b.time_block || '')));
    return map;
  }, [bookings]);
  const colorMap = useMemo(() => buildProgramCalendarColorMap(colorBookings), [colorBookings]);
  const colorFor = (booking) => colorMap[programCalendarKey(booking)] || PROGRAM_CALENDAR_COLORS[0];

  const visibleDays = useMemo(() => {
    if (mode === 'week') {
      const start = startOfWeek(anchorDate);
      return Array.from({ length: 7 }, (_, index) => addDays(start, index));
    }
    const first = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
    const start = startOfWeek(first);
    return Array.from({ length: 42 }, (_, index) => addDays(start, index));
  }, [anchorDate, mode]);

  const move = (direction) => {
    const next = new Date(anchorDate);
    if (mode === 'week') next.setDate(next.getDate() + direction * 7);
    else next.setMonth(next.getMonth() + direction);
    setAnchorDate(next);
  };

  const title = mode === 'week'
    ? `${visibleDays[0].toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short' })} – ${visibleDays[6].toLocaleDateString('cs-CZ', { day: 'numeric', month: 'short', year: 'numeric' })}`
    : anchorDate.toLocaleDateString('cs-CZ', { month: 'long', year: 'numeric' });

  return (
    <Card className="overflow-hidden" data-testid="bookings-calendar-view">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b p-3">
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" onClick={() => setAnchorDate(new Date())}>Dnes</Button>
          <Button variant="ghost" size="sm" aria-label="Předchozí období" onClick={() => move(-1)}><ChevronLeft className="h-4 w-4" /></Button>
          <Button variant="ghost" size="sm" aria-label="Následující období" onClick={() => move(1)}><ChevronRight className="h-4 w-4" /></Button>
          <span className="ml-2 font-semibold capitalize">{title}</span>
        </div>
        <div className="flex rounded-lg bg-slate-100 p-1">
          {['week', 'month'].map((value) => (
            <button key={value} type="button" onClick={() => setMode(value)} className={`rounded-md px-3 py-1.5 text-sm ${mode === value ? 'bg-white shadow-sm' : 'text-slate-600'}`}>
              {value === 'week' ? 'Týden' : 'Měsíc'}
            </button>
          ))}
        </div>
      </div>

      {mode === 'week' ? (
        <div className="overflow-x-auto">
          <div className="min-w-[900px]">
            <div className="grid grid-cols-8 border-b">
              <div className="border-r p-3 text-xs text-slate-500">GMT+01</div>
              {visibleDays.map((day) => {
                const dateKey = toDateKey(day);
                const today = dateKey === toDateKey(new Date());
                return (
                  <div key={dateKey} className={`border-r p-3 text-center last:border-r-0 ${today ? 'bg-blue-50' : ''}`}>
                    <div className="text-xs font-medium uppercase text-slate-500">{day.toLocaleDateString('cs-CZ', { weekday: 'short' })}</div>
                    <div className={`text-2xl font-semibold ${today ? 'text-blue-600' : 'text-slate-900'}`}>{day.getDate()}</div>
                  </div>
                );
              })}
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {Array.from({ length: 12 }, (_, index) => index + 8).map((hour) => (
                <div key={hour} className="grid min-h-[64px] grid-cols-8 border-b last:border-b-0">
                  <div className="border-r p-2 text-right text-xs text-slate-500">{hour}:00</div>
                  {visibleDays.map((day) => {
                    const dateKey = toDateKey(day);
                    const startsHere = (byDate.get(dateKey) || []).filter((booking) => Math.floor(parseTimeRange(booking.time_block).start / 60) === hour);
                    return (
                      <div key={dateKey} className="relative border-r p-0.5 last:border-r-0">
                        {startsHere.map((booking, index) => {
                          const range = parseTimeRange(booking.time_block);
                          const duration = Math.max(45, range.end - range.start);
                          return (
                            <CalendarEvent
                              key={booking.id}
                              booking={booking}
                              onSelect={onSelectBooking}
                              collision={collisionIndex.has(booking.id)}
                              color={colorFor(booking)}
                              className="absolute overflow-hidden shadow-sm"
                              style={{
                                top: `${((range.start % 60) / 60) * 64 + 2}px`,
                                left: `calc(${(index / startsHere.length) * 100}% + 1px)`,
                                width: `calc(${100 / startsHere.length}% - 2px)`,
                                height: `${Math.max(46, (duration / 60) * 64 - 4)}px`,
                                zIndex: index + 1,
                              }}
                            />
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7">
        {visibleDays.map((day) => {
          const dateKey = toDateKey(day);
          const dayBookings = byDate.get(dateKey) || [];
          const outsideMonth = mode === 'month' && day.getMonth() !== anchorDate.getMonth();
          const today = dateKey === toDateKey(new Date());
          return (
            <section key={dateKey} className={`min-h-36 border-b border-r p-2 ${outsideMonth ? 'bg-slate-50 text-slate-400' : 'bg-white'}`}>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="uppercase text-xs">{day.toLocaleDateString('cs-CZ', { weekday: 'short' })}</span>
                <span className={`flex h-7 w-7 items-center justify-center rounded-full ${today ? 'bg-slate-800 text-white' : ''}`}>{day.getDate()}</span>
              </div>
              <div className="space-y-1.5">
                {dayBookings.map((booking) => (
                  <CalendarEvent key={booking.id} booking={booking} onSelect={onSelectBooking} collision={collisionIndex.has(booking.id)} color={colorFor(booking)} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
      )}
    </Card>
  );
};
