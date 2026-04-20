import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import { Calendar, Users, ArrowRight, CheckCircle, Loader2, AlertCircle, CreditCard, Copy, Download, ExternalLink } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card } from '../../components/ui/card';
import { BookingHeader } from '../../components/layout/BookingHeader';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PublicEventsPage() {
  const { institutionId } = useParams();
  const [step, setStep] = useState('list');
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [payingOnline, setPayingOnline] = useState(false);
  const [institutionData, setInstitutionData] = useState({
    name: '',
    logoUrl: null,
    primaryColor: '#5a7aae',
    secondaryColor: '#c5ac87',
    headerStyle: 'light',
  });

  useEffect(() => {
    fetchEvents();
    fetchTheme();
  }, [institutionId]);

  const fetchTheme = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/settings/theme/public/${institutionId}`);
      setInstitutionData({
        name: res.data.institution_name || '',
        logoUrl: res.data.logo_url,
        primaryColor: res.data.primary_color || '#5a7aae',
        secondaryColor: res.data.secondary_color || '#c5ac87',
        headerStyle: res.data.header_style || 'light',
      });
    } catch { /* fallback to defaults */ }
  };

  const fetchEvents = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/events/public/${institutionId}`);
      setEvents(res.data || []);
    } catch (err) {
      if (err.response?.status === 404) setError('Stránka nenalezena');
      else setError('Nepodařilo se načíst události');
    } finally { setLoading(false); }
  };

  const fetchEventDetail = async (eventId) => {
    try {
      const res = await axios.get(`${API_URL}/api/events/public/${institutionId}/${eventId}`);
      setSelectedEvent(res.data);
      // Auto-select date if only one available
      const availableDates = (res.data.dates || []).filter(d => d.spots_left > 0);
      if (availableDates.length === 1) {
        setSelectedDate(availableDates[0]);
      }
      setStep('detail');
    } catch { toast.error('Nepodařilo se načíst detail události'); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const emailField = selectedEvent.form_fields?.find(f => f.type === 'email');
      const nameField = selectedEvent.form_fields?.find(f => f.label?.toLowerCase().includes('jméno') || f.label?.toLowerCase().includes('name'));
      const res = await axios.post(`${API_URL}/api/events/public/${institutionId}/apply`, {
        event_id: selectedEvent.id,
        event_date_id: selectedDate?.id || null,
        applicant_data: formValues,
        applicant_email: emailField ? formValues[emailField.id] : null,
        applicant_name: nameField ? formValues[nameField.id] : null,
      });
      setResult(res.data);
      setStep('success');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Nepodařilo se odeslat přihlášku');
    } finally { setSubmitting(false); }
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('cs-CZ', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const shortDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const headerProps = {
    logoUrl: institutionData.logoUrl,
    institutionName: institutionData.name,
    primaryColor: institutionData.primaryColor,
    secondaryColor: institutionData.secondaryColor,
    headerStyle: institutionData.headerStyle,
  };

  if (loading) return (
    <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-[#5a7aae]" />
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <BookingHeader {...headerProps} />
      <div className="flex items-center justify-center p-4 mt-20">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    </div>
  );

  // Render a single form field on the public side
  const renderFormField = (field) => {
    if (field.type === 'checkbox') {
      return (
        <div key={field.id} className="py-1">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!formValues[field.id]}
              onChange={e => setFormValues(p => ({ ...p, [field.id]: e.target.checked }))}
              className="rounded mt-0.5 w-4 h-4 shrink-0"
              required={field.required}
              data-testid={`field-${field.id}`}
            />
            <span className="text-sm text-gray-700">
              {field.label} {field.required && <span className="text-red-500">*</span>}
            </span>
          </label>
        </div>
      );
    }

    return (
      <div key={field.id}>
        <Label className="text-sm font-medium text-gray-700">
          {field.label} {field.required && <span className="text-red-500">*</span>}
        </Label>
        {field.type === 'text' && (
          <Input value={formValues[field.id] || ''} onChange={e => setFormValues(p => ({ ...p, [field.id]: e.target.value }))} required={field.required} className="mt-1" data-testid={`field-${field.id}`} />
        )}
        {field.type === 'email' && (
          <Input type="email" value={formValues[field.id] || ''} onChange={e => setFormValues(p => ({ ...p, [field.id]: e.target.value }))} required={field.required} className="mt-1" data-testid={`field-${field.id}`} />
        )}
        {field.type === 'number' && (
          <Input type="tel" value={formValues[field.id] || ''} onChange={e => setFormValues(p => ({ ...p, [field.id]: e.target.value }))} required={field.required} className="mt-1" data-testid={`field-${field.id}`} />
        )}
        {field.type === 'select' && (
          <select value={formValues[field.id] || ''} onChange={e => setFormValues(p => ({ ...p, [field.id]: e.target.value }))} required={field.required} className="mt-1 w-full border border-gray-200 rounded-md px-3 py-2 text-sm bg-white" data-testid={`field-${field.id}`}>
            <option value="">Vyberte...</option>
            {(field.options || []).map((opt, i) => <option key={i} value={opt}>{opt}</option>)}
          </select>
        )}
      </div>
    );
  };

  // ===== SUCCESS =====
  if (step === 'success' && result) {
    return (
      <div className="min-h-screen bg-[#F8F9FA]">
        <BookingHeader {...headerProps} />
        <div className="py-8 px-4">
          <div className="max-w-lg mx-auto">
            <Card className="p-6 md:p-8 text-center">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Přihláška odeslána!</h1>
              <p className="text-gray-600 mb-6">Vaše přihláška byla úspěšně zaregistrována.</p>

              {result.qr_payload && result.total_amount > 0 && (
                <div className="border-t pt-6 mt-6 space-y-4">
                  <div className="flex items-center justify-center gap-2 text-slate-700">
                    <CreditCard className="w-5 h-5" />
                    <h2 className="text-lg font-semibold">Platební údaje</h2>
                  </div>
                  <div className="bg-white border rounded-xl p-6 inline-block mx-auto" data-testid="qr-code">
                    <QRCodeSVG value={result.qr_payload} size={200} level="M" />
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 text-left space-y-2 text-sm">
                    {result.payment_settings?.account_number && (
                      <div className="flex justify-between"><span className="text-gray-500">Číslo účtu:</span><span className="font-mono font-medium">{result.payment_settings.account_number}/{result.payment_settings.bank_code}</span></div>
                    )}
                    <div className="flex justify-between"><span className="text-gray-500">Částka:</span><span className="font-medium">{result.total_amount} Kč</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">Variabilní symbol:</span><span className="font-mono font-medium">{result.variable_symbol}</span></div>
                    {result.payment_settings?.account_name && (
                      <div className="flex justify-between"><span className="text-gray-500">Příjemce:</span><span className="font-medium">{result.payment_settings.account_name}</span></div>
                    )}
                  </div>
                  <Button variant="outline" className="w-full" onClick={() => { navigator.clipboard.writeText(`Účet: ${result.payment_settings?.account_number}/${result.payment_settings?.bank_code}\nČástka: ${result.total_amount} Kč\nVS: ${result.variable_symbol}`); toast.success('Platební údaje zkopírovány'); }} data-testid="copy-payment-btn">
                    <Copy className="w-4 h-4 mr-2" /> Kopírovat platební údaje
                  </Button>
                  <p className="text-xs text-gray-500">Naskenujte QR kód v bankovní aplikaci nebo zadejte údaje ručně.</p>
                </div>
              )}
              {(!result.qr_payload || result.total_amount === 0) && !result.payment_settings?.gateway_enabled && (
                <p className="text-sm text-gray-500">Organizátor vás bude kontaktovat s dalšími informacemi.</p>
              )}

              {/* Pay online via gateway (Comgate etc.) */}
              {result.payment_settings?.gateway_enabled && result.total_amount > 0 && (
                <div className="border-t pt-4 mt-4 space-y-2">
                  <Button
                    className="w-full bg-slate-900 hover:bg-slate-800 text-white"
                    onClick={async () => {
                      setPayingOnline(true);
                      try {
                        localStorage.setItem('bz_last_payment_institution', institutionId);
                        const res = await axios.post(`${API_URL}/api/event-payments/initiate`, {
                          institution_id: institutionId,
                          application_id: result.id,
                        });
                        if (res.data?.redirect_url) {
                          window.location.href = res.data.redirect_url;
                        } else {
                          toast.error('Nepodařilo se zahájit platbu');
                        }
                      } catch (e) {
                        toast.error(e.response?.data?.detail || 'Chyba platební brány');
                      } finally {
                        setPayingOnline(false);
                      }
                    }}
                    disabled={payingOnline}
                    data-testid="pay-online-btn"
                  >
                    {payingOnline ? (
                      <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Přesměrovávám...</>
                    ) : (
                      <><ExternalLink className="w-4 h-4 mr-2" /> Zaplatit online ({result.total_amount} Kč)</>
                    )}
                  </Button>
                  <p className="text-xs text-gray-500 text-center">
                    Po zaplacení se vaše přihláška automaticky potvrdí.
                  </p>
                </div>
              )}

              {/* PDF Download */}
              {result.pdf_url && (
                <div className="border-t pt-4 mt-4">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => window.open(`${API_URL}${result.pdf_url}`, '_blank')}
                    data-testid="download-pdf-btn"
                  >
                    <Download className="w-4 h-4 mr-2" /> Stáhnout potvrzení (PDF)
                  </Button>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // ===== FORM =====
  if (step === 'form' && selectedEvent) {
    return (
      <div className="min-h-screen bg-[#F8F9FA]">
        <BookingHeader {...headerProps} />
        <div className="py-8 px-4">
          <div className="max-w-lg mx-auto">
            <button onClick={() => setStep('detail')} className="text-sm text-[#5a7aae] hover:underline mb-4 inline-block" data-testid="back-to-detail">
              &larr; Zpět na detail
            </button>
            <Card className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-1">{selectedEvent.name}</h2>
              {selectedDate && <p className="text-sm text-gray-500 mb-2">Termín: {formatDate(selectedDate.start_datetime)}</p>}
              {selectedEvent.price > 0 && <p className="text-sm font-medium text-slate-700 mb-4">Cena: {selectedEvent.price} Kč</p>}

              <form onSubmit={handleSubmit} className="space-y-4">
                {(selectedEvent.form_fields || []).sort((a, b) => (a.order || 0) - (b.order || 0)).map(renderFormField)}
                <Button type="submit" disabled={submitting} className="w-full bg-[#5a7aae] hover:bg-[#4a6a9e] h-12 mt-6" data-testid="submit-application-btn">
                  {submitting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Odesílám...</> : 'Odeslat přihlášku'}
                </Button>
              </form>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // ===== DETAIL =====
  if (step === 'detail' && selectedEvent) {
    return (
      <div className="min-h-screen bg-[#F8F9FA]">
        <BookingHeader {...headerProps} />
        <div className="py-8 px-4">
          <div className="max-w-2xl mx-auto">
            <button onClick={() => { setStep('list'); setSelectedEvent(null); setSelectedDate(null); }} className="text-sm text-[#5a7aae] hover:underline mb-4 inline-block" data-testid="back-to-list">
              &larr; Zpět na seznam
            </button>
            <Card className="overflow-hidden">
              <div className="p-6 md:p-8">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">{selectedEvent.name}</h1>
                {selectedEvent.description && <p className="text-gray-600 mb-6 whitespace-pre-wrap">{selectedEvent.description}</p>}
                <div className="flex flex-wrap gap-4 mb-6 text-sm text-gray-500">
                  <span className="flex items-center gap-1"><Users className="w-4 h-4" /> Kapacita: {selectedEvent.capacity}</span>
                  {selectedEvent.price > 0 && <span className="font-medium text-slate-700">{selectedEvent.price} Kč</span>}
                </div>

                <h3 className="font-semibold text-slate-900 mb-3">Vyberte termín</h3>
                {(selectedEvent.dates || []).length === 0 ? (
                  <p className="text-sm text-gray-500">Žádné dostupné termíny.</p>
                ) : (
                  <div className="space-y-2 mb-6">
                    {selectedEvent.dates.map(d => {
                      const isFull = d.spots_left <= 0;
                      const isSelected = selectedDate?.id === d.id;
                      return (
                        <button key={d.id} type="button" disabled={isFull} onClick={() => setSelectedDate(isSelected ? null : d)}
                          className={`w-full text-left p-4 border rounded-lg transition-all ${isSelected ? 'border-[#5a7aae] bg-[#5a7aae]/5 ring-1 ring-[#5a7aae]' : isFull ? 'border-gray-200 bg-gray-50 opacity-60 cursor-not-allowed' : 'border-gray-200 hover:border-gray-300'}`}
                          data-testid={`date-option-${d.id}`}>
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="text-sm font-medium">{formatDate(d.start_datetime)}</p>
                              <p className="text-xs text-gray-500">do {shortDate(d.end_datetime)}</p>
                            </div>
                            <div className="text-right">
                              {isFull ? <span className="text-xs text-red-500 font-medium">Obsazeno</span> : <span className="text-xs text-green-600">{d.spots_left} volných míst</span>}
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
                <Button onClick={() => { setFormValues({}); setStep('form'); }} disabled={!selectedDate && (selectedEvent.dates || []).length > 0} className="w-full bg-[#5a7aae] hover:bg-[#4a6a9e] h-12" data-testid="proceed-to-form-btn">
                  Pokračovat k přihlášce <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // ===== LIST =====
  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <BookingHeader {...headerProps} />
      <div className="py-8 px-4">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">Události a přihlášky</h1>
          {events.length === 0 ? (
            <Card className="p-8 text-center">
              <Calendar className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Momentálně nejsou k dispozici žádné události.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {events.map(ev => (
                <Card key={ev.id} className="p-5 cursor-pointer hover:shadow-md transition-shadow" onClick={() => fetchEventDetail(ev.id)} data-testid={`public-event-${ev.id}`}>
                  <h2 className="text-lg font-semibold text-gray-900 mb-1">{ev.name}</h2>
                  {ev.description && <p className="text-sm text-gray-500 line-clamp-2 mb-3">{ev.description}</p>}
                  <div className="flex flex-wrap gap-3 text-sm text-gray-500">
                    <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {(ev.dates || []).length} termínů</span>
                    <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {ev.capacity} míst</span>
                    {ev.price > 0 && <span className="font-medium text-slate-700">{ev.price} Kč</span>}
                    {ev.price === 0 && <span className="text-green-600">Zdarma</span>}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
