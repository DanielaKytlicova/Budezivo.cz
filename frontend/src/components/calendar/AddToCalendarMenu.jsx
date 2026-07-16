/**
 * Phase C — "Přidat do kalendáře" for a single reservation.
 * Offers deep-links (Google / Outlook web) and a downloadable .ics file
 * that works with any other calendar app (Apple, Thunderbird, …).
 */
import React, { useState } from 'react';
import { Button } from '../ui/button';
import { CalendarPlus, Download, ChevronDown } from 'lucide-react';
import { buildCalendarLinks, downloadReservationIcs } from './calendarUtils';

export const AddToCalendarMenu = ({ booking, token, durationMinutes }) => {
  const [open, setOpen] = useState(false);
  const links = buildCalendarLinks(booking, { durationMinutes });

  return (
    <div className="pt-3 border-t" data-testid="add-to-calendar">
      <Button
        variant="outline"
        size="sm"
        className="w-full justify-between"
        onClick={() => setOpen((o) => !o)}
        data-testid="add-to-calendar-toggle"
      >
        <span className="flex items-center">
          <CalendarPlus className="w-4 h-4 mr-2" />
          Přidat do kalendáře
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </Button>

      {open && (
        <div className="mt-2 grid gap-1.5" data-testid="add-to-calendar-options">
          {links && (
            <>
              <a href={links.google} target="_blank" rel="noopener noreferrer" data-testid="atc-google">
                <Button variant="ghost" size="sm" className="w-full justify-start text-[#4285F4] hover:bg-blue-50">
                  Google kalendář
                </Button>
              </a>
              <a href={links.outlookLive} target="_blank" rel="noopener noreferrer" data-testid="atc-outlook">
                <Button variant="ghost" size="sm" className="w-full justify-start text-[#0F6CBD] hover:bg-sky-50">
                  Outlook (outlook.com)
                </Button>
              </a>
              <a href={links.outlookOffice} target="_blank" rel="noopener noreferrer" data-testid="atc-outlook-office">
                <Button variant="ghost" size="sm" className="w-full justify-start text-[#0F6CBD] hover:bg-sky-50">
                  Outlook (Microsoft 365)
                </Button>
              </a>
            </>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-slate-600 hover:bg-slate-50"
            onClick={() => downloadReservationIcs(booking.id, token)}
            data-testid="atc-ics"
          >
            <Download className="w-4 h-4 mr-2" />
            Stáhnout .ics (ostatní kalendáře)
          </Button>
        </div>
      )}
    </div>
  );
};

export default AddToCalendarMenu;
