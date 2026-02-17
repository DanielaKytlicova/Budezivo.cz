import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { ThemeContext } from '../../context/ThemeContext';
import { Header } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card } from '../../components/ui/card';
import { Checkbox } from '../../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ChevronLeft, ChevronRight, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const BookingPage = () => {
  const { institutionId } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { applyTheme } = useContext(ThemeContext);
  const [step, setStep] = useState(1);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    program_id: '',
    date: '',
    time_slot: '09:00',
    school_name: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    num_students: 1,
    notes: '',
    gdpr_consent: false,
  });

  useEffect(() => {
    fetchTheme();
    fetchPrograms();
  }, []);

  const fetchTheme = async () => {
    try {
      const response = await axios.get(`${API}/settings/theme/public/${institutionId}`);
      applyTheme(response.data);
    } catch (error) {
      console.error('Error fetching theme:', error);
    }
  };

  const fetchPrograms = async () => {
    try {
      const response = await axios.get(`${API}/programs/public/${institutionId}`);
      setPrograms(response.data);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.gdpr_consent) {
      toast.error(t('booking.gdprConsent'));
      return;
    }

    setSubmitting(true);

    try {
      await axios.post(`${API}/bookings/public/${institutionId}`, formData);
      setSuccess(true);
      toast.success(t('booking.success'));
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    } finally {
      setSubmitting(false);
    }
  };

  const selectedProgram = programs.find((p) => p.id === formData.program_id);

  if (success) {
    return (
      <div className="min-h-screen bg-[#FDFCF8]">
        <Header />
        <div className="max-w-2xl mx-auto px-4 py-16">
          <Card className="p-12 text-center">
            <div className="mb-6 text-[#84A98C]">
              <CheckCircle className="w-24 h-24 mx-auto" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900 mb-4">{t('booking.success')}</h1>
            <p className="text-lg text-slate-600 mb-8">{t('booking.successMessage')}</p>
            <Button
              onClick={() => window.location.reload()}
              className="bg-[var(--theme-accent)] text-slate-900 hover:bg-[var(--theme-accent)]/90"
            >
              {t('booking.title')}
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      <Header />
      <div className="max-w-2xl mx-auto px-4 py-16">
        <Card className="p-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-8 text-center">{t('booking.title')}</h1>

          <div className="flex items-center justify-center mb-8">
            {[1, 2, 3].map((s) => (
              <React.Fragment key={s}>
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                    s === step
                      ? 'bg-[var(--theme-primary)] text-white'
                      : s < step
                      ? 'bg-[var(--theme-secondary)] text-white'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {s}
                </div>
                {s < 3 && <div className="w-12 h-1 bg-muted mx-2"></div>}
              </React.Fragment>
            ))}
          </div>

          <form onSubmit={handleSubmit} data-testid="booking-form">
            {step === 1 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-slate-900">{t('booking.step1')}</h2>
                {loading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {programs.map((program) => (
                      <div
                        key={program.id}
                        data-testid={`program-option-${program.id}`}
                        onClick={() => setFormData({ ...formData, program_id: program.id })}
                        className={`p-4 border rounded-md cursor-pointer transition-colors ${
                          formData.program_id === program.id
                            ? 'border-[var(--theme-primary)] bg-slate-50'
                            : 'border-border hover:bg-slate-50'
                        }`}
                      >
                        <h3 className="font-semibold text-slate-900">{program.name_cs}</h3>
                        <p className="text-sm text-muted-foreground mt-1">{program.description_cs}</p>
                        <div className="flex gap-4 mt-3 text-sm">
                          <span className="text-muted-foreground">⏱ {program.duration} min</span>
                          <span className="text-muted-foreground">👥 {program.capacity}</span>
                          {program.price > 0 && <span className="text-muted-foreground">💰 {program.price} Kč</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-slate-900">{t('booking.step2')}</h2>
                <div>
                  <Label htmlFor="date">{t('booking.selectDate')}</Label>
                  <Input
                    id="date"
                    type="date"
                    data-testid="booking-date-input"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                    className="mt-2"
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
                <div>
                  <Label htmlFor="time_slot">{t('booking.selectTime')}</Label>
                  <Select
                    value={formData.time_slot}
                    onValueChange={(value) => setFormData({ ...formData, time_slot: value })}
                  >
                    <SelectTrigger className="mt-2" data-testid="booking-time-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="09:00">09:00</SelectItem>
                      <SelectItem value="10:00">10:00</SelectItem>
                      <SelectItem value="11:00">11:00</SelectItem>
                      <SelectItem value="13:00">13:00</SelectItem>
                      <SelectItem value="14:00">14:00</SelectItem>
                      <SelectItem value="15:00">15:00</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-slate-900">{t('booking.step3')}</h2>
                <div>
                  <Label htmlFor="school_name">{t('booking.schoolName')}</Label>
                  <Input
                    id="school_name"
                    data-testid="booking-school-name-input"
                    value={formData.school_name}
                    onChange={(e) => setFormData({ ...formData, school_name: e.target.value })}
                    required
                    className="mt-2"
                  />
                </div>
                <div>
                  <Label htmlFor="contact_name">{t('booking.contactName')}</Label>
                  <Input
                    id="contact_name"
                    data-testid="booking-contact-name-input"
                    value={formData.contact_name}
                    onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                    required
                    className="mt-2"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="contact_email">{t('booking.contactEmail')}</Label>
                    <Input
                      id="contact_email"
                      type="email"
                      data-testid="booking-email-input"
                      value={formData.contact_email}
                      onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                      required
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label htmlFor="contact_phone">{t('booking.contactPhone')}</Label>
                    <Input
                      id="contact_phone"
                      type="tel"
                      data-testid="booking-phone-input"
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                      required
                      className="mt-2"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="num_students">{t('booking.numStudents')}</Label>
                  <Input
                    id="num_students"
                    type="number"
                    data-testid="booking-num-students-input"
                    value={formData.num_students}
                    onChange={(e) => setFormData({ ...formData, num_students: parseInt(e.target.value) })}
                    required
                    min="1"
                    className="mt-2"
                  />
                </div>
                <div>
                  <Label htmlFor="notes">{t('booking.notes')}</Label>
                  <Textarea
                    id="notes"
                    data-testid="booking-notes-input"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="mt-2"
                  />
                </div>
                <div className="flex items-start space-x-2">
                  <Checkbox
                    id="gdpr_consent"
                    data-testid="booking-gdpr-checkbox"
                    checked={formData.gdpr_consent}
                    onCheckedChange={(checked) => setFormData({ ...formData, gdpr_consent: checked })}
                  />
                  <label htmlFor="gdpr_consent" className="text-sm text-slate-700 leading-relaxed cursor-pointer">
                    {t('booking.gdprConsent')}
                  </label>
                </div>
              </div>
            )}

            <div className="flex gap-4 mt-8">
              {step > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  data-testid="booking-back-button"
                  onClick={() => setStep(step - 1)}
                  className="flex-1"
                >
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  {t('booking.back')}
                </Button>
              )}
              {step < 3 ? (
                <Button
                  type="button"
                  data-testid="booking-next-button"
                  onClick={() => {
                    if (step === 1 && !formData.program_id) {
                      toast.error(t('booking.selectProgram'));
                      return;
                    }
                    if (step === 2 && !formData.date) {
                      toast.error(t('booking.selectDate'));
                      return;
                    }
                    setStep(step + 1);
                  }}
                  className="flex-1 bg-[var(--theme-accent)] text-slate-900 hover:bg-[var(--theme-accent)]/90"
                >
                  {t('booking.next')}
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  data-testid="booking-submit-button"
                  disabled={submitting}
                  className="flex-1 bg-[var(--theme-secondary)] text-white hover:bg-[var(--theme-secondary)]/90"
                >
                  {submitting ? t('common.loading') : t('booking.submit')}
                </Button>
              )}
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
};
