import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
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

const AGE_GROUPS = {
  ms_3_6: 'MŠ (3-6 let)',
  zs1_7_12: 'ZŠ I. (7-12 let)',
  zs2_12_15: 'ZŠ II. (12-15 let)',
  ss_14_18: 'SŠ (14-18 let)',
  gym_14_18: 'GYM (14-18 let)',
  adults: 'Dospělí'
};

export const BookingPage = () => {
  const { institutionId } = useParams();
  const { t } = useTranslation();
  const { applyTheme } = useContext(ThemeContext);
  const [step, setStep] = useState(1);
  const [programs, setPrograms] = useState([]);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [calendarData, setCalendarData] = useState(null);
  const [timeBlocks, setTimeBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  
  const [formData, setFormData] = useState({
    program_id: '',
    date: '',
    time_block: '',
    school_name: '',
    group_type: 'ms_3_6',
    age_or_class: '',
    num_students: 15,
    special_requirements: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    gdpr_consent: false,
  });

  useEffect(() => {
    fetchTheme();
    fetchPrograms();
    fetchCalendar(currentYear, currentMonth);
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
      toast.error('Chyba při načítání programů');
    } finally {
      setLoading(false);
    }
  };

  const fetchCalendar = async (year, month) => {
    try {
      const response = await axios.get(`${API}/calendar/${institutionId}/${year}/${month}`);
      setCalendarData(response.data);
    } catch (error) {
      console.error('Error fetching calendar:', error);
    }
  };

  const fetchTimeBlocks = async (date) => {
    try {
      const response = await axios.get(`${API}/availability/${institutionId}/${formData.program_id}/${date}`);
      setTimeBlocks(response.data.time_blocks);
    } catch (error) {
      toast.error('Chyba při načítání volných bloků');
    }
  };

  const handleProgramSelect = (program) => {
    setSelectedProgram(program);
    setFormData({ ...formData, program_id: program.id });
    setStep(2);
  };

  const handleDateSelect = async (date) => {
    setFormData({ ...formData, date });
    await fetchTimeBlocks(date);
    setStep(3);
  };

  const handleTimeBlockSelect = (timeBlock) => {
    setFormData({ ...formData, time_block: timeBlock });
    setStep(4);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.gdpr_consent) {
      toast.error('Musíte souhlasit se zpracováním osobních údajů');
      return;
    }

    setSubmitting(true);

    try {
      await axios.post(`${API}/bookings/public/${institutionId}`, formData);
      setSuccess(true);
      toast.success('Rezervace byla odeslána');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při odeslání rezervace');
    } finally {
      setSubmitting(false);
    }
  };

  const renderCalendar = () => {
    if (!calendarData) return null;

    const daysInMonth = calendarData.dates.length;
    const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();
    const adjustedFirstDay = firstDay === 0 ? 6 : firstDay - 1;

    const monthNames = ['Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen', 'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec'];
    const dayNames = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];

    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <div className=\"flex items-center justify-between mb-6\">
          <button
            onClick={() => {
              const newMonth = currentMonth === 1 ? 12 : currentMonth - 1;
              const newYear = currentMonth === 1 ? currentYear - 1 : currentYear;
              setCurrentMonth(newMonth);
              setCurrentYear(newYear);
              fetchCalendar(newYear, newMonth);
            }}
            className=\"p-2 hover:bg-gray-100 rounded\"
          >
            <ChevronLeft className=\"w-5 h-5\" />
          </button>
          <h3 className=\"text-xl font-semibold\">{monthNames[currentMonth - 1]} {currentYear}</h3>
          <button
            onClick={() => {
              const newMonth = currentMonth === 12 ? 1 : currentMonth + 1;
              const newYear = currentMonth === 12 ? currentYear + 1 : currentYear;
              setCurrentMonth(newMonth);
              setCurrentYear(newYear);
              fetchCalendar(newYear, newMonth);
            }}
            className=\"p-2 hover:bg-gray-100 rounded\"
          >
            <ChevronRight className=\"w-5 h-5\" />
          </button>
        </div>

        <div className=\"grid grid-cols-7 gap-2 mb-2\">
          {dayNames.map((day) => (
            <div key={day} className=\"text-center text-sm font-medium text-gray-500 py-2\">
              {day}
            </div>
          ))}
        </div>

        <div className=\"grid grid-cols-7 gap-2\">
          {Array(adjustedFirstDay).fill(null).map((_, i) => (
            <div key={`empty-${i}`} className=\"aspect-square\" />
          ))}
          {calendarData.dates.map((dateInfo, i) => {
            const day = i + 1;
            const isPast = new Date(dateInfo.date) < new Date();
            const hasAvailability = dateInfo.has_availability && !isPast;

            return (
              <button
                key={day}
                onClick={() => hasAvailability && handleDateSelect(dateInfo.date)}
                disabled={!hasAvailability}
                className={`aspect-square rounded-lg flex flex-col items-center justify-center text-sm relative transition-colors ${
                  hasAvailability
                    ? 'bg-white border border-gray-200 hover:border-[var(--theme-accent)] hover:bg-[var(--theme-accent)]/10 cursor-pointer'
                    : 'bg-gray-50 text-gray-400 cursor-not-allowed'
                }`}
              >
                <span className=\"font-medium\">{day}</span>
                {hasAvailability && (
                  <div className=\"flex gap-1 mt-1\">
                    {[...Array(Math.min(dateInfo.available_blocks, 3))].map((_, i) => (
                      <div key={i} className=\"w-1 h-1 rounded-full bg-[var(--theme-secondary)]\" />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <div className=\"mt-6 p-4 bg-gray-50 rounded-md\">
          <p className=\"text-sm font-medium mb-2\">Legenda</p>
          <div className=\"flex items-center gap-2 text-sm\">
            <div className=\"flex gap-1\">
              <div className=\"w-1 h-1 rounded-full bg-[var(--theme-secondary)]\" />
              <div className=\"w-1 h-1 rounded-full bg-[var(--theme-secondary)]\" />
              <div className=\"w-1 h-1 rounded-full bg-[var(--theme-secondary)]\" />
            </div>
            <span className=\"text-gray-600\">Volné bloky</span>
          </div>
        </div>
      </div>
    );
  };

  if (success) {
    return (
      <div className=\"min-h-screen bg-[#FDFCF8]\">
        <Header />
        <div className=\"max-w-2xl mx-auto px-4 py-16\">
          <Card className=\"p-12 text-center\">
            <div className=\"mb-6 text-[#84A98C]\">
              <CheckCircle className=\"w-24 h-24 mx-auto\" />
            </div>
            <h1 className=\"text-3xl font-bold text-slate-900 mb-4\">Rezervace byla odeslána</h1>
            <p className=\"text-lg text-slate-600 mb-8\">
              Vaši rezervaci jsme přijali. Brzy vás budeme kontaktovat s potvrzením.
            </p>
            <Button
              onClick={() => window.location.reload()}
              className=\"bg-[var(--theme-accent)] text-slate-900 hover:bg-[var(--theme-accent)]/90\"
            >
              Vytvořit další rezervaci
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className=\"min-h-screen bg-[#FDFCF8]\">
      <Header />
      <div className=\"max-w-4xl mx-auto px-4 py-8\">
        {/* Progress indicator */}
        <div className=\"flex items-center justify-center mb-8\">
          {[1, 2, 3, 4].map((s) => (
            <React.Fragment key={s}>
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm ${
                  s === step
                    ? 'bg-[var(--theme-primary)] text-white'
                    : s < step
                    ? 'bg-[var(--theme-secondary)] text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {s}
              </div>
              {s < 4 && <div className=\"w-12 h-1 bg-gray-200 mx-2\" />}
            </React.Fragment>
          ))}
        </div>

        <p className=\"text-center text-sm text-gray-500 mb-8\">krok {step} ze 4</p>

        {/* Step 1: Program Selection */}
        {step === 1 && (
          <div>
            {loading ? (
              <div className=\"text-center py-12\">
                <div className=\"animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto\"></div>
              </div>
            ) : (
              <div className=\"space-y-4\">
                {programs.map((program) => (
                  <Card
                    key={program.id}
                    className=\"p-6 cursor-pointer hover:shadow-md transition-shadow\"
                    onClick={() => handleProgramSelect(program)}
                    data-testid={`program-card-${program.id}`}
                  >
                    <div className=\"flex justify-between items-start mb-3\">
                      <div>
                        <h3 className=\"text-xl font-semibold text-slate-900 mb-1\">{program.name_cs}</h3>
                        <p className=\"text-sm text-gray-500\">Doprovodný program</p>
                      </div>
                      <button className=\"px-4 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50\">
                        Detail
                      </button>
                    </div>
                    <p className=\"text-slate-600 mb-4\">{program.description_cs}</p>
                    <div className=\"flex gap-3\">
                      <span className=\"px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm\">
                        {AGE_GROUPS[program.age_group]}
                      </span>
                      <span className=\"px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm\">
                        {program.duration} min.
                      </span>
                    </div>
                  </Card>
                ))}
                <Button
                  className=\"w-full bg-slate-800 text-white hover:bg-slate-700 h-14 text-base\"
                  onClick={() => {
                    if (!formData.program_id) {
                      toast.error('Vyberte prosím program');
                      return;
                    }
                    setStep(2);
                  }}
                >
                  Vybrat datum a čas
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Calendar */}
        {step === 2 && (
          <div>
            <h2 className=\"text-2xl font-bold text-slate-900 mb-2\">Přehled</h2>
            <p className=\"text-gray-600 mb-6\">Přehled nabízených bloků pro doprovodné programy</p>
            {renderCalendar()}
            <Button
              variant=\"outline\"
              className=\"w-full mt-4\"
              onClick={() => setStep(1)}
            >
              <ChevronLeft className=\"w-4 h-4 mr-2\" />
              Zpět na výběr programu
            </Button>
          </div>
        )}

        {/* Step 3: Time Block Selection */}
        {step === 3 && (
          <div>
            <h2 className=\"text-2xl font-bold text-slate-900 mb-2\">Vyberte časový blok</h2>
            <p className=\"text-gray-600 mb-6\">
              {new Date(formData.date).toLocaleDateString('cs-CZ', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            <div className=\"space-y-3\">
              {timeBlocks.map((block) => (
                <button
                  key={block.time}
                  onClick={() => block.status === 'available' && handleTimeBlockSelect(block.time)}
                  disabled={block.status !== 'available'}
                  className={`w-full p-4 rounded-lg text-left transition-colors ${
                    formData.time_block === block.time
                      ? 'bg-gray-200 border-2 border-gray-400'
                      : block.status === 'available'
                      ? 'bg-white border border-gray-200 hover:border-[var(--theme-accent)] hover:bg-[var(--theme-accent)]/10'
                      : 'bg-gray-50 border border-gray-200 cursor-not-allowed'
                  }`}
                  data-testid={`time-block-${block.time}`}
                >
                  <div className=\"flex justify-between items-center\">
                    <div>
                      <p className=\"text-lg font-semibold\">{block.time}</p>
                      <p className=\"text-sm text-gray-500\">{block.status === 'available' ? 'Volný' : 'Obsazeno'}</p>
                    </div>
                    <div className=\"w-6 h-6 rounded-full border-2 border-gray-300\" />
                  </div>
                </button>
              ))}
            </div>
            <div className=\"mt-6 p-4 bg-blue-50 rounded-md border border-blue-100\">
              <p className=\"text-sm text-blue-900\">
                Všechny časové bloky jsou 90 min. dlouhé. Prosím přiďte o 10 minut dříve, aby bylo dost času na organizační prvky.
              </p>
            </div>
            <div className=\"flex gap-3 mt-6\">
              <Button
                variant=\"outline\"
                className=\"flex-1\"
                onClick={() => setStep(2)}
              >
                <ChevronLeft className=\"w-4 h-4 mr-2\" />
                Zpět
              </Button>
              <Button
                className=\"flex-1 bg-slate-800 text-white hover:bg-slate-700\"
                onClick={() => {
                  if (!formData.time_block) {
                    toast.error('Vyberte prosím časový blok');
                    return;
                  }
                  setStep(4);
                }}
              >
                Pokračovat na detail rezervace
              </Button>
            </div>
          </div>
        )}

        {/* Step 4: Group Info + Contact */}
        {step === 4 && (
          <form onSubmit={handleSubmit}>
            <div className=\"space-y-6\">
              <div>
                <h2 className=\"text-2xl font-bold text-slate-900 mb-2\">Informace o skupině</h2>
                <p className=\"text-gray-600 mb-4\">Řekněte nám o sobě víc</p>

                <div className=\"space-y-4\">
                  <div>
                    <Label>Škola /Název organizace *</Label>
                    <Input
                      value={formData.school_name}
                      onChange={(e) => setFormData({ ...formData, school_name: e.target.value })}
                      placeholder=\"Základní škola Komenského\"
                      required
                      className=\"mt-2\"
                      data-testid=\"booking-school-name\"
                    />
                  </div>

                  <div>
                    <Label>Typ skupiny *</Label>
                    <Select
                      value={formData.group_type}
                      onValueChange={(value) => setFormData({ ...formData, group_type: value })}
                    >
                      <SelectTrigger className=\"mt-2\" data-testid=\"booking-group-type\">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(AGE_GROUPS).map(([key, label]) => (
                          <SelectItem key={key} value={key}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Věk / Třída *</Label>
                    <Input
                      value={formData.age_or_class}
                      onChange={(e) => setFormData({ ...formData, age_or_class: e.target.value })}
                      placeholder=\"3-4 roky\"
                      required
                      className=\"mt-2\"
                      data-testid=\"booking-age-class\"
                    />
                  </div>

                  <div>
                    <Label>Počet osob *</Label>
                    <Input
                      type=\"number\"
                      value={formData.num_students}
                      onChange={(e) => setFormData({ ...formData, num_students: parseInt(e.target.value) })}
                      required
                      min={selectedProgram?.min_capacity || 5}
                      max={selectedProgram?.max_capacity || 30}
                      className=\"mt-2\"
                      data-testid=\"booking-num-students\"
                    />
                    <p className=\"text-xs text-gray-500 mt-1\">
                      Min. {selectedProgram?.min_capacity || 5}, Max {selectedProgram?.max_capacity || 30} osob.
                    </p>
                  </div>

                  <div>
                    <Label>Speciální požadavky</Label>
                    <Textarea
                      value={formData.special_requirements}
                      onChange={(e) => setFormData({ ...formData, special_requirements: e.target.value })}
                      placeholder=\"Zde můžete napsat, poznámku pro lektora, pokud máte speciální požadavky, rádi Vám vyjdeme vstříc.\"
                      className=\"mt-2\"
                      rows={3}
                      data-testid=\"booking-special-requirements\"
                    />
                  </div>
                </div>
              </div>

              <div>
                <h2 className=\"text-2xl font-bold text-slate-900 mb-2\">Kontaktní informace</h2>
                <p className=\"text-gray-600 mb-4\">Hlavní kontakt pro vytvoření rezervace</p>

                <div className=\"space-y-4\">
                  <div>
                    <Label>Jméno zodpovědné osoby *</Label>
                    <Input
                      value={formData.contact_name}
                      onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                      placeholder=\"Jméno Příjmení\"
                      required
                      className=\"mt-2\"
                      data-testid=\"booking-contact-name\"
                    />
                  </div>

                  <div>
                    <Label>Emailová adresa *</Label>
                    <Input
                      type=\"email\"
                      value={formData.contact_email}
                      onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                      placeholder=\"zakladni@skola.cz\"
                      required
                      className=\"mt-2\"
                      data-testid=\"booking-contact-email\"
                    />
                  </div>

                  <div>
                    <Label>Telefonní číslo *</Label>
                    <Input
                      type=\"tel\"
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                      placeholder=\"+ 420 722 960 890\"
                      required
                      className=\"mt-2\"
                      data-testid=\"booking-contact-phone\"
                    />
                  </div>

                  <div className=\"flex items-start space-x-2 pt-2\">
                    <Checkbox
                      id=\"gdpr\"
                      checked={formData.gdpr_consent}
                      onCheckedChange={(checked) => setFormData({ ...formData, gdpr_consent: checked })}
                      data-testid=\"booking-gdpr\"
                    />
                    <label htmlFor=\"gdpr\" className=\"text-sm text-slate-700 leading-relaxed cursor-pointer\">
                      Souhlasím se zpracováním osobních údajů v souladu s GDPR
                    </label>
                  </div>
                </div>
              </div>

              <div className=\"p-4 bg-blue-50 rounded-md border border-blue-100\">
                <p className=\"text-sm text-blue-900\">
                  Všechny časové bloky jsou 90 min. dlouhé. Prosím přiďte o 10 minut dříve, aby bylo dost času na organizační prvky.
                </p>
              </div>

              <div className=\"flex gap-3\">
                <Button
                  type=\"button\"
                  variant=\"outline\"
                  className=\"flex-1\"
                  onClick={() => setStep(3)}
                >
                  <ChevronLeft className=\"w-4 h-4 mr-2\" />
                  Zpět
                </Button>
                <Button
                  type=\"submit\"
                  disabled={submitting}
                  className=\"flex-1 bg-slate-800 text-white hover:bg-slate-700 h-14\"
                  data-testid=\"booking-submit\"
                >
                  {submitting ? 'Odesílání...' : 'Shrnout rezervace'}
                </Button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
