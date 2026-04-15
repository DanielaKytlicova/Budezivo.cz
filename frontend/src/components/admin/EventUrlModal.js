import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Link as LinkIcon, ExternalLink, Copy } from 'lucide-react';
import { toast } from 'sonner';

export const EventUrlModal = ({ open, onOpenChange, events, institutionId }) => {
  const [selectedEvent, setSelectedEvent] = useState('all');
  const [urlData, setUrlData] = useState(null);

  const generateUrl = (eventId = 'all') => {
    if (!institutionId) return;

    const baseUrl = "https://budezivo.cz";
    const previewBase = window.location.origin;
    const path = `/events/${institutionId}`;

    if (eventId === 'all') {
      const url = `${baseUrl}${path}`;
      setUrlData({
        url,
        previewUrl: `${previewBase}${path}`,
        event_name: 'Všechny události',
        embed_code: `<a href="${url}" target="_blank">Zobrazit události</a>`,
      });
    } else {
      const ev = events.find(e => e.id === eventId);
      const url = `${baseUrl}${path}?event=${eventId}`;
      setUrlData({
        url,
        previewUrl: `${previewBase}${path}?event=${eventId}`,
        event_name: ev?.name || 'Událost',
        embed_code: `<a href="${url}" target="_blank">${ev?.name || 'Událost'}</a>`,
      });
    }
  };

  const handleSelect = (id) => {
    setSelectedEvent(id);
    generateUrl(id);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Zkopírováno do schránky');
  };

  const handleOpenChange = (val) => {
    if (!val) { setSelectedEvent('all'); setUrlData(null); }
    onOpenChange(val);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="max-w-lg max-h-[85dvh] sm:max-h-[90vh] flex flex-col p-0 overflow-hidden"
        aria-describedby="event-url-description"
      >
        <div className="p-4 sm:p-6 pb-0 shrink-0">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <LinkIcon className="w-5 h-5" />
              URL pro vložení na web
            </DialogTitle>
            <p id="event-url-description" className="text-sm text-gray-500 mt-2">
              Vyberte událost a zkopírujte URL pro vložení na webové stránky.
            </p>
          </DialogHeader>
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain px-4 sm:px-6 pb-4 sm:pb-6">
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-sm font-medium text-slate-700 mb-2 block">Vyberte událost</Label>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-2">
                <button
                  type="button"
                  onClick={() => handleSelect('all')}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedEvent === 'all' ? 'bg-slate-800 text-white' : 'hover:bg-gray-100'
                  }`}
                  data-testid="event-url-select-all"
                >
                  Všechny události
                </button>
                {Array.isArray(events) && events.filter(e => e.is_active).map(ev => (
                  <button
                    key={ev.id}
                    type="button"
                    onClick={() => handleSelect(ev.id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                      selectedEvent === ev.id ? 'bg-slate-800 text-white' : 'hover:bg-gray-100'
                    }`}
                    data-testid={`event-url-select-${ev.id}`}
                  >
                    {ev.name}
                  </button>
                ))}
              </div>
            </div>

            {urlData && (
              <>
                <div>
                  <Label className="text-xs text-gray-500">Vybraná událost</Label>
                  <p className="font-medium">{urlData.event_name}</p>
                </div>

                <div>
                  <Label className="text-xs text-gray-500">URL pro události</Label>
                  <div className="flex gap-2 mt-1">
                    <Input value={urlData.url} readOnly className="flex-1 text-sm font-mono" data-testid="event-external-url" />
                    <Button size="sm" onClick={() => copyToClipboard(urlData.url)} className="bg-slate-800 text-white shrink-0" data-testid="event-copy-url">
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div>
                  <Label className="text-xs text-gray-500">HTML kód pro vložení</Label>
                  <div className="flex gap-2 mt-1">
                    <Input value={urlData.embed_code} readOnly className="flex-1 text-sm font-mono" />
                    <Button size="sm" variant="outline" onClick={() => copyToClipboard(urlData.embed_code)} className="shrink-0">
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t sticky bottom-0 bg-white pb-2">
                  <Button variant="outline" onClick={() => window.open(urlData.previewUrl, '_blank')} className="flex-1" data-testid="event-preview-url">
                    <ExternalLink className="w-4 h-4 mr-2" /> Náhled
                  </Button>
                  <Button onClick={() => handleOpenChange(false)} className="flex-1 bg-slate-800 text-white" data-testid="event-close-url-modal">
                    Zavřít
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
