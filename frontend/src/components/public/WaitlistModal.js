import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { FieldError, FIELD_ERROR_CLASS } from '../ui/field-error';
import { Bell, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TIME_OPTIONS = [
  { value: 'morning', label: 'Dopoledne (8-12)' },
  { value: 'midday', label: 'Kolem poledne (11-13)' },
  { value: 'afternoon', label: 'Odpoledne (13-17)' },
  { value: 'any', label: 'Kdykoliv' },
];

// Map an exact slot time ("HH:MM") to the coarse preferred-time-of-day bucket.
const timeToPreferred = (time) => {
  if (!time || typeof time !== 'string') return 'any';
  const h = parseInt(time.split(':')[0], 10);
  if (Number.isNaN(h)) return 'any';
  if (h < 11) return 'morning';
  if (h < 13) return 'midday';
  if (h < 17) return 'afternoon';
  return 'any';
};

export const WaitlistModal = ({ open, onOpenChange, institutionId, programId, programName, prefilledDate, prefilledTime }) => {
  const [step, setStep] = useState('form'); // form, success
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [form, setForm] = useState({
    teacher_name: '',
    school_name: '',
    email: '',
    phone: '',
    participant_count: '',
    request_type: 'specific_date',
    requested_date: prefilledDate || '',
    range_start_date: '',
    range_end_date: '',
    preferred_time_of_day: timeToPreferred(prefilledTime),
    notes: '',
  });

  // Sync prefill (date + time) every time the modal opens or the prefilled slot
  // changes — useState's initializer only runs once, so without this the
  // date/time the user clicked wouldn't appear.
  useEffect(() => {
    if (!open) return;
    setForm(f => ({
      ...f,
      request_type: 'specific_date',
      requested_date: prefilledDate || '',
      preferred_time_of_day: timeToPreferred(prefilledTime),
      notes: prefilledTime
        ? `Zájem o termín ${prefilledDate || ''} ${prefilledTime}`.trim()
        : f.notes,
    }));
  }, [open, prefilledDate, prefilledTime]);

  const clearFieldError = (field) => {
    setFieldErrors(prev => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const updateField = (field, value) => {
    clearFieldError(field);
    setForm(f => ({ ...f, [field]: value }));
  };

  const validateForm = () => {
    const errors = {};
    if (!form.teacher_name.trim()) errors.teacher_name = 'Vyplňte jméno.';
    if (!form.school_name.trim()) errors.school_name = 'Vyplňte školu.';
    const email = form.email.trim();
    if (!email) {
      errors.email = 'Vyplňte e-mail.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Zadejte platnou e-mailovou adresu.';
    }
    if (!Number.isFinite(Number(form.participant_count)) || Number(form.participant_count) < 1) {
      errors.participant_count = 'Vyplňte počet žáků.';
    }
    if (form.request_type === 'specific_date' && !form.requested_date) {
      errors.requested_date = 'Vyberte datum.';
    }
    if (form.request_type === 'date_range') {
      if (!form.range_start_date) errors.range_start_date = 'Vyberte začátek rozsahu.';
      if (!form.range_end_date) errors.range_end_date = 'Vyberte konec rozsahu.';
      if (form.range_start_date && form.range_end_date && form.range_end_date < form.range_start_date) {
        errors.range_end_date = 'Konec rozsahu musí být po začátku.';
      }
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      toast.error('Zkontrolujte zvýrazněná pole.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/api/waitlist`, {
        institution_id: institutionId,
        program_id: programId,
        ...form,
        participant_count: parseInt(form.participant_count) || 1,
      });
      setStep('success');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail) toast.error(detail);
      else toast.error('Nepodařilo se odeslat');
    } finally { setSubmitting(false); }
  };

  const handleClose = () => {
    setStep('form');
    setForm(f => ({ ...f, teacher_name: '', school_name: '', email: '', phone: '', participant_count: '', notes: '' }));
    onOpenChange(false);
  };

  if (step === 'success') {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-md" aria-describedby="wl-success">
          <div className="text-center py-6">
            <CheckCircle className="w-14 h-14 text-green-500 mx-auto mb-4" />
            <h2 className="text-lg font-bold text-gray-900 mb-2">Zájem zaregistrován</h2>
            <p id="wl-success" className="text-sm text-gray-600 mb-4">
              Zařadili jsme vás mezi zájemce o program <strong>{programName}</strong>. Jakmile se uvolní vhodný termín, dáme vám vědět.
            </p>
            <Button onClick={handleClose} className="bg-slate-800 text-white">Zavřít</Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-lg max-h-[90dvh] overflow-y-auto" aria-describedby="wl-form-desc">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-[#4A6FA5]" />
            Hlídat volný termín
          </DialogTitle>
          <p id="wl-form-desc" className="text-sm text-gray-500 mt-1">
            {programName}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} noValidate className="space-y-4 py-2">
          {prefilledDate && prefilledTime && (
            <div className="rounded-lg border border-[#4A6FA5]/20 bg-[#4A6FA5]/5 p-3" data-testid="wl-prefilled-slot">
              <p className="text-sm text-[#4A6FA5]">
                Hlídáme termín: <strong>{new Date(prefilledDate).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })}</strong> v <strong>{prefilledTime}</strong>
              </p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label className="text-sm">Jméno <span className="text-red-500">*</span></Label>
              <Input value={form.teacher_name} onChange={e => updateField('teacher_name', e.target.value)} className={`mt-1 ${fieldErrors.teacher_name ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-teacher-name" />
              <FieldError message={fieldErrors.teacher_name} />
            </div>
            <div>
              <Label className="text-sm">Škola <span className="text-red-500">*</span></Label>
              <Input value={form.school_name} onChange={e => updateField('school_name', e.target.value)} className={`mt-1 ${fieldErrors.school_name ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-school-name" />
              <FieldError message={fieldErrors.school_name} />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label className="text-sm">Email <span className="text-red-500">*</span></Label>
              <Input type="email" value={form.email} onChange={e => updateField('email', e.target.value)} className={`mt-1 ${fieldErrors.email ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-email" />
              <FieldError message={fieldErrors.email} />
            </div>
            <div>
              <Label className="text-sm">Telefon</Label>
              <Input type="tel" value={form.phone} onChange={e => updateField('phone', e.target.value)} className="mt-1" data-testid="wl-phone" />
            </div>
          </div>

          <div>
            <Label className="text-sm">Počet žáků <span className="text-red-500">*</span></Label>
            <Input type="number" value={form.participant_count} onChange={e => updateField('participant_count', e.target.value)} className={`mt-1 w-32 ${fieldErrors.participant_count ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-participant-count" />
            <FieldError message={fieldErrors.participant_count} />
          </div>

          {/* Request type toggle */}
          <div>
            <Label className="text-sm mb-2 block">Typ požadavku</Label>
            <div className="flex gap-2">
              <button type="button" onClick={() => updateField('request_type', 'specific_date')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${form.request_type === 'specific_date' ? 'bg-slate-800 text-white border-slate-800' : 'border-gray-200 text-gray-600 hover:border-gray-400'}`}
                data-testid="wl-type-specific">Konkrétní datum</button>
              <button type="button" onClick={() => updateField('request_type', 'date_range')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${form.request_type === 'date_range' ? 'bg-slate-800 text-white border-slate-800' : 'border-gray-200 text-gray-600 hover:border-gray-400'}`}
                data-testid="wl-type-range">Časový rozsah</button>
            </div>
          </div>

          {form.request_type === 'specific_date' && (
            <div>
              <Label className="text-sm">Datum <span className="text-red-500">*</span></Label>
              <Input type="date" value={form.requested_date} onChange={e => updateField('requested_date', e.target.value)} className={`mt-1 ${fieldErrors.requested_date ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-date" />
              <FieldError message={fieldErrors.requested_date} />
            </div>
          )}

          {form.request_type === 'date_range' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-sm">Od <span className="text-red-500">*</span></Label>
                <Input type="date" value={form.range_start_date} onChange={e => updateField('range_start_date', e.target.value)} className={`mt-1 ${fieldErrors.range_start_date ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-range-start" />
                <FieldError message={fieldErrors.range_start_date} />
              </div>
              <div>
                <Label className="text-sm">Do <span className="text-red-500">*</span></Label>
                <Input type="date" value={form.range_end_date} onChange={e => updateField('range_end_date', e.target.value)} className={`mt-1 ${fieldErrors.range_end_date ? FIELD_ERROR_CLASS : ''}`} data-testid="wl-range-end" />
                <FieldError message={fieldErrors.range_end_date} />
              </div>
            </div>
          )}

          <div>
            <Label className="text-sm">Preferovaný čas</Label>
            <Select value={form.preferred_time_of_day} onValueChange={v => updateField('preferred_time_of_day', v)}>
              <SelectTrigger className="mt-1" data-testid="wl-time-pref"><SelectValue /></SelectTrigger>
              <SelectContent>
                {TIME_OPTIONS.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-sm">Poznámka</Label>
            <Textarea value={form.notes} onChange={e => updateField('notes', e.target.value)} placeholder="Další informace..." className="mt-1" rows={2} data-testid="wl-notes" />
          </div>

          <Button type="submit" disabled={submitting} className="w-full bg-[#4A6FA5] hover:bg-[#3d5e8e] text-white h-11" data-testid="wl-submit">
            {submitting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Odesílám...</> : <><Bell className="w-4 h-4 mr-2" /> Hlídat termín</>}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
