import React, { useState, useEffect, useContext, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { ThemeContext } from '../../context/ThemeContext';
import { BookingHeader } from '../../components/layout/BookingHeader';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card } from '../../components/ui/card';
import { Checkbox } from '../../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ChevronLeft, ChevronRight, CheckCircle, SlidersHorizontal, X, Download, Bell } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { WaitlistModal } from '../../components/public/WaitlistModal';
import { API } from '../../config/api';

const AGE_GROUPS = {
  ms_3_6: 'MŠ (3-6 let)',
  zs1_7_12: 'ZŠ I. (7-12 let)',
  zs2_12_15: 'ZŠ II. (12-15 let)',
  ss_14_18: 'SŠ (14-18 let)',
  gym_14_18: 'GYM (14-18 let)',
  adults: 'Dospělí'
};

// Filter options — maps URL code to internal age_group/target_groups values
const AGE_FILTER_OPTIONS = [
  { code: 'MS', label: 'MŠ', longLabel: 'Mateřské školy', internalKeys: ['ms_3_6'] },
  { code: 'ZS1', label: 'ZŠ I.', longLabel: 'I. stupeň ZŠ', internalKeys: ['zs1_7_12'] },
  { code: 'ZS2', label: 'ZŠ II.', longLabel: 'II. stupeň ZŠ', internalKeys: ['zs2_12_15'] },
  { code: 'SS', label: 'SŠ', longLabel: 'Střední školy', internalKeys: ['ss_14_18', 'ss_15_19'] },
  { code: 'GYM', label: 'GYM', longLabel: 'Gymnázia', internalKeys: ['gym_14_18'] },
];

const DURATION_FILTER_OPTIONS = [
  { value: 'all', label: 'Všechny délky' },
  { value: 'short', label: 'Krátký (do 60 min)' },
  { value: 'medium', label: 'Střední (60–120 min)' },
  { value: 'long', label: 'Dlouhý (120+ min)' },
];

export const BookingPage = () => {
  const { institutionId } = useParams();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const { applyTheme } = useContext(ThemeContext);
  const [step, setStep] = useState(() => {
    // If program is preselected via URL, start at step 2
    const programParam = new URLSearchParams(window.location.search).get('program');
    return programParam ? 2 : 1;
  });
  const [programs, setPrograms] = useState([]);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [calendarData, setCalendarData] = useState(null);
  const [timeBlocks, setTimeBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [createdReservationId, setCreatedReservationId] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filter state — initialized from URL params
  const [ageFilters, setAgeFilters] = useState(() => {
    const ageParam = searchParams.get('age');
    if (ageParam) return ageParam.split(',').filter(Boolean).map(s => s.trim().toUpperCase());
    return [];
  });
  const [durationFilter, setDurationFilter] = useState(() => searchParams.get('duration') || 'all');
  const preselectedProgramId = searchParams.get('program') || null;
  const [showWaitlist, setShowWaitlist] = useState(false);
  const [waitlistDate, setWaitlistDate] = useState(null);
  
  // Data instituce pro header a theme
  const [institutionData, setInstitutionData] = useState({
    logoUrl: null,
    name: null,
    primaryColor: '#4A6FA5',
    secondaryColor: '#84A98C',
    accentColor: '#E9C46A',
    headerStyle: 'light',
    plan: 'free'
  });
  
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
    num_teachers: 1,
    special_requirements: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    gdpr_consent: false,
    terms_accepted: false,
    terms_accepted_text_version: 'v1',
  });

  useEffect(() => {
    fetchTheme();
    fetchInstitutionInfo();
    fetchPrograms();
    fetchCalendar(currentYear, currentMonth);
  }, []);

  const fetchTheme = async () => {
    try {
      const response = await axios.get(`${API}/settings/theme/public/${institutionId}`);
      applyTheme(response.data);
      // Uložit všechna theme data pro header
      setInstitutionData(prev => ({
        ...prev,
        logoUrl: response.data.logo_url,
        primaryColor: response.data.primary_color || '#4A6FA5',
        secondaryColor: response.data.secondary_color || '#84A98C',
        accentColor: response.data.accent_color || '#E9C46A',
        headerStyle: response.data.header_style || 'light'
      }));
    } catch (error) {
      console.error('Error fetching theme:', error);
    }
  };

  const fetchInstitutionInfo = async () => {
    try {
      const response = await axios.get(`${API}/public/institutions/${institutionId}`);
      setInstitutionData(prev => ({
        ...prev,
        name: response.data.name,
        logoUrl: response.data.logo_url || prev.logoUrl,
        plan: response.data.plan || 'free'
      }));
    } catch (error) {
      console.error('Error fetching institution info:', error);
    }
  };

  const fetchPrograms = async () => {
    try {
      const response = await axios.get(`${API}/programs/public/${institutionId}`);
      const allPrograms = Array.isArray(response.data) ? response.data : [];
      setPrograms(allPrograms);
      
      // Auto-select preselected program from URL parameter
      if (preselectedProgramId) {
        const preselected = allPrograms.find(p => p.id === preselectedProgramId);
        if (preselected) {
          setSelectedProgram(preselected);
          setFormData(prev => ({ ...prev, program_id: preselected.id }));
          setStep(2); // Jump to calendar step
          fetchCalendar(currentYear, currentMonth, preselected.id);
        }
      }
    } catch (error) {
      toast.error('Chyba při načítání programů');
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchCalendar = async (year, month, programId = null) => {
    try {
      let url = `${API}/calendar/${institutionId}/${year}/${month}`;
      if (programId) {
        url += `?program_id=${programId}`;
      }
      const response = await axios.get(url);
      setCalendarData(response.data);
    } catch (error) {
      console.error('Error fetching calendar:', error);
    }
  };

  const fetchTimeBlocks = async (date) => {
    try {
      const response = await axios.get(`${API}/availability/${institutionId}/${formData.program_id}/${date}`);
      setTimeBlocks(Array.isArray(response.data?.time_blocks) ? response.data.time_blocks : []);
    } catch (error) {
      toast.error('Chyba při načítání volných bloků');
      setTimeBlocks([]);
    }
  };

  // Client-side filtering of programs
  const filteredPrograms = useMemo(() => {
    let result = programs;
    
    if (ageFilters.length > 0) {
      // Build set of internal keys from selected URL codes
      const internalKeys = new Set();
      for (const code of ageFilters) {
        const opt = AGE_FILTER_OPTIONS.find(o => o.code === code);
        if (opt) opt.internalKeys.forEach(k => internalKeys.add(k));
      }
      result = result.filter(p => {
        const tgs = p.target_groups || [];
        const ag = p.age_group || '';
        return tgs.some(tg => internalKeys.has(tg)) || internalKeys.has(ag);
      });
    }
    
    if (durationFilter && durationFilter !== 'all') {
      result = result.filter(p => {
        const d = p.duration || 0;
        if (durationFilter === 'short') return d < 60;
        if (durationFilter === 'medium') return d >= 60 && d <= 120;
        if (durationFilter === 'long') return d > 120;
        return true;
      });
    }
    
    return result;
  }, [programs, ageFilters, durationFilter]);

  const toggleAgeFilter = (code) => {
    setAgeFilters(prev => 
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const clearFilters = () => {
    setAgeFilters([]);
    setDurationFilter('all');
  };

  const hasActiveFilters = ageFilters.length > 0 || durationFilter !== 'all';

  // Auto-show filters if URL params are present
  useEffect(() => {
    if (searchParams.get('age') || searchParams.get('duration')) {
      setShowFilters(true);
    }
  }, [searchParams]);

  const handleProgramSelect = async (program) => {
    setSelectedProgram(program);
    setFormData({ ...formData, program_id: program.id });
    // Fetch calendar for selected program
    await fetchCalendar(currentYear, currentMonth, program.id);
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
    
    if (!formData.terms_accepted) {
      toast.error('Musíte souhlasit s podmínkami rezervace');
      return;
    }

    setSubmitting(true);

    try {
      const response = await axios.post(`${API}/bookings/public/${institutionId}`, formData);
      setCreatedReservationId(response.data?.id || null);
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

    const monthNames = ['Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen', 'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec'];
    const dayNames = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];
    const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();
    const adjustedFirstDay = firstDay === 0 ? 6 : firstDay - 1;

    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => {
              const newMonth = currentMonth === 1 ? 12 : currentMonth - 1;
              const newYear = currentMonth === 1 ? currentYear - 1 : currentYear;
              setCurrentMonth(newMonth);
              setCurrentYear(newYear);
              fetchCalendar(newYear, newMonth, formData.program_id);
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-600" />
          </button>
          <h3 className="text-xl font-semibold text-[#2B3E50]">{monthNames[currentMonth - 1]} {currentYear}</h3>
          <button
            onClick={() => {
              const newMonth = currentMonth === 12 ? 1 : currentMonth + 1;
              const newYear = currentMonth === 12 ? currentYear + 1 : currentYear;
              setCurrentMonth(newMonth);
              setCurrentYear(newYear);
              fetchCalendar(newYear, newMonth, formData.program_id);
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        <div className="grid grid-cols-7 gap-2 mb-2">
          {dayNames.map((day) => (
            <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-2">
          {Array(adjustedFirstDay).fill(null).map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square" />
          ))}
          {Array.isArray(calendarData?.dates) && calendarData.dates.map((dateInfo, i) => {
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
                    ? 'bg-white border border-gray-300 cursor-pointer'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
                style={hasAvailability ? {
                  '--tw-border-opacity': 1,
                } : {}}
                onMouseEnter={(e) => {
                  if (hasAvailability) {
                    e.currentTarget.style.borderColor = institutionData.primaryColor;
                    e.currentTarget.style.backgroundColor = `${institutionData.primaryColor}10`;
                  }
                }}
                onMouseLeave={(e) => {
                  if (hasAvailability) {
                    e.currentTarget.style.borderColor = '#d1d5db';
                    e.currentTarget.style.backgroundColor = '#ffffff';
                  }
                }}
              >
                <span className="font-medium">{day}</span>
                {hasAvailability && (
                  <div className="flex gap-1 mt-1">
                    {[...Array(Math.min(dateInfo.available_blocks, 3))].map((_, i) => (
                      <div 
                        key={i} 
                        className="w-1 h-1 rounded-full" 
                        style={{ backgroundColor: institutionData.primaryColor }}
                      />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-gray-50 rounded-md border border-gray-200">
          <p className="text-sm font-medium mb-2 text-[#2B3E50]">Legenda</p>
          <div className="flex items-center gap-2 text-sm">
            <div className="flex gap-1">
              <div className="w-1 h-1 rounded-full" style={{ backgroundColor: institutionData.primaryColor }} />
              <div className="w-1 h-1 rounded-full" style={{ backgroundColor: institutionData.primaryColor }} />
              <div className="w-1 h-1 rounded-full" style={{ backgroundColor: institutionData.primaryColor }} />
            </div>
            <span className="text-gray-600">Volné bloky</span>
          </div>
        </div>
      </div>
    );
  };

  if (success) {
    return (
      <div className="min-h-screen bg-[#F8F9FA]">
        <BookingHeader 
          logoUrl={institutionData.logoUrl}
          institutionName={institutionData.name}
          primaryColor={institutionData.primaryColor}
          secondaryColor={institutionData.secondaryColor}
          accentColor={institutionData.accentColor}
          headerStyle={institutionData.headerStyle}
          plan={institutionData.plan}
          institutionId={institutionId}
        />
        <div className="max-w-2xl mx-auto px-4 py-16">
          <Card className="p-12 text-center border border-gray-200">
            <div className="mb-6" style={{ color: institutionData.primaryColor }}>
              <CheckCircle className="w-24 h-24 mx-auto" />
            </div>
            <h1 className="text-3xl font-bold text-[#2B3E50] mb-4">Rezervace byla odeslána</h1>
            <p className="text-lg text-gray-600 mb-8">
              Vaši rezervaci jsme přijali. Brzy vás budeme kontaktovat s potvrzením.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {createdReservationId && (
                <Button
                  variant="outline"
                  onClick={async () => {
                    try {
                      const res = await axios.get(`${API}/calendar/public-feed-token/reservation/${createdReservationId}`);
                      window.open(`${API}/calendar/reservation/${createdReservationId}.ics?token=${res.data.token}`, '_blank');
                    } catch { /* ignore */ }
                  }}
                  className="rounded-lg"
                  data-testid="success-add-to-outlook-btn"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Přidat do Outlooku
                </Button>
              )}
              <Button
                onClick={() => window.location.reload()}
                style={{ backgroundColor: institutionData.accentColor }}
                className="text-white hover:opacity-90 rounded-lg"
              >
                Vytvořit další rezervaci
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <BookingHeader 
        logoUrl={institutionData.logoUrl}
        institutionName={institutionData.name}
        primaryColor={institutionData.primaryColor}
        secondaryColor={institutionData.secondaryColor}
        accentColor={institutionData.accentColor}
        headerStyle={institutionData.headerStyle}
        plan={institutionData.plan}
        institutionId={institutionId}
      />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center mb-8">
          {[1, 2, 3, 4].map((s) => (
            <React.Fragment key={s}>
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm"
                style={{
                  backgroundColor: s === step 
                    ? institutionData.primaryColor 
                    : s < step 
                    ? institutionData.accentColor 
                    : '#e5e7eb',
                  color: s <= step ? '#ffffff' : '#6b7280'
                }}
              >
                {s}
              </div>
              {s < 4 && <div className="w-12 h-1 bg-gray-200 mx-2" />}
            </React.Fragment>
          ))}
        </div>

        <p className="text-center text-sm text-gray-500 mb-8">krok {step} ze 4</p>

        {step === 1 && (
          <div>
            {/* Filter bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
                  data-testid="toggle-filters-btn"
                >
                  <SlidersHorizontal className="w-4 h-4" />
                  Filtrovat programy
                  {hasActiveFilters && (
                    <span 
                      className="ml-1 w-5 h-5 rounded-full text-xs text-white flex items-center justify-center"
                      style={{ backgroundColor: institutionData.primaryColor }}
                    >
                      {ageFilters.length + (durationFilter !== 'all' ? 1 : 0)}
                    </span>
                  )}
                </button>
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                    data-testid="clear-filters-btn"
                  >
                    <X className="w-3 h-3" />
                    Zrušit filtry
                  </button>
                )}
              </div>

              {showFilters && (
                <Card className="p-4 border border-gray-200 space-y-4" data-testid="filter-panel">
                  {/* Age category checkboxes */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Věková skupina</p>
                    <div className="flex flex-wrap gap-2">
                      {AGE_FILTER_OPTIONS.map(opt => {
                        const isActive = ageFilters.includes(opt.code);
                        return (
                          <button
                            key={opt.code}
                            onClick={() => toggleAgeFilter(opt.code)}
                            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                              isActive 
                                ? 'text-white border-transparent' 
                                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                            }`}
                            style={isActive ? { backgroundColor: institutionData.primaryColor } : {}}
                            data-testid={`filter-age-${opt.code}`}
                          >
                            {opt.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Duration select */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Doba trvání</p>
                    <Select value={durationFilter} onValueChange={setDurationFilter}>
                      <SelectTrigger className="w-full sm:w-56" data-testid="filter-duration">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {DURATION_FILTER_OPTIONS.map(opt => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </Card>
              )}
            </div>

            {loading ? (
              <div className="text-center py-12">
                <div 
                  className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto"
                  style={{ borderColor: institutionData.primaryColor }}
                ></div>
              </div>
            ) : filteredPrograms.length === 0 ? (
              <Card className="p-8 text-center border border-gray-200">
                <p className="text-gray-500 mb-2">
                  {hasActiveFilters 
                    ? 'Žádné programy neodpovídají vybraným filtrům.'
                    : 'Momentálně nejsou k dispozici žádné programy.'
                  }
                </p>
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="text-sm font-medium hover:underline"
                    style={{ color: institutionData.primaryColor }}
                  >
                    Zobrazit všechny programy
                  </button>
                )}
              </Card>
            ) : (
              <div className="space-y-4">
                {filteredPrograms.map((program) => {
                  // Format validity dates
                  const formatDate = (dateStr) => {
                    if (!dateStr) return null;
                    try {
                      return new Date(dateStr).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' });
                    } catch {
                      return null;
                    }
                  };
                  const startDate = formatDate(program.start_date);
                  const endDate = formatDate(program.end_date);
                  const hasValidity = startDate || endDate;
                  
                  return (
                  <Card
                    key={program.id}
                    className="p-6 cursor-pointer hover:shadow-sm transition-all border border-gray-200 rounded-lg"
                    style={{ 
                      '--hover-border-color': institutionData.primaryColor 
                    }}
                    onClick={() => handleProgramSelect(program)}
                    data-testid={`program-card-${program.id}`}
                  >
                    {program.image_url && (
                      <div className="-mx-6 -mt-6 mb-4 rounded-t-lg overflow-hidden">
                        <img
                          src={`${process.env.REACT_APP_BACKEND_URL}${program.image_url}`}
                          alt={program.name_cs}
                          className="w-full h-48 object-cover"
                          data-testid={`program-image-${program.id}`}
                        />
                      </div>
                    )}
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-xl font-semibold text-[#2B3E50] mb-1">{program.name_cs}</h3>
                        <p className="text-sm text-gray-500">Doprovodný program</p>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">{program.description_cs}</p>
                    <div className="flex flex-wrap gap-3 mb-3">
                      {(() => {
                        const ageLabel = AGE_GROUPS[program.age_group] || AGE_GROUPS[(program.target_groups || [])[0]];
                        if (!ageLabel) return null;
                        return (
                          <span 
                            className="px-3 py-1 rounded-md text-sm font-medium"
                            style={{ 
                              backgroundColor: `${institutionData.primaryColor}15`,
                              color: institutionData.primaryColor 
                            }}
                          >
                            {ageLabel}
                          </span>
                        );
                      })()}
                      <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm font-medium">
                        {program.duration} min.
                      </span>
                      {program.pricing_info && (
                        <span
                          className="px-3 py-1 rounded-md text-sm font-medium bg-amber-50 text-amber-800 border border-amber-200"
                          data-testid={`program-pricing-${program.id}`}
                          title="Informativní cena"
                        >
                          {program.pricing_info}
                        </span>
                      )}
                    </div>
                    {hasValidity && (
                      <div className="pt-3 border-t border-gray-100">
                        <p className="text-sm text-gray-500">
                          {startDate && endDate ? (
                            <>Platnost: {startDate} – {endDate}</>
                          ) : startDate ? (
                            <>Od: {startDate}</>
                          ) : (
                            <>Do: {endDate}</>
                          )}
                        </p>
                      </div>
                    )}
                  </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="text-2xl font-bold text-[#2B3E50] mb-2">Přehled dostupnosti</h2>
            <p className="text-gray-600 mb-6">Vyberte datum pro váš program</p>
            {renderCalendar()}
            <Button
              variant="outline"
              className="w-full mt-4 border-2 border-gray-300 rounded-lg"
              onClick={() => setStep(1)}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Zpět na výběr programu
            </Button>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 className="text-2xl font-bold text-[#2B3E50] mb-2">Vyberte časový blok</h2>
            <p className="text-gray-600 mb-6">
              {new Date(formData.date).toLocaleDateString('cs-CZ', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            <div className="space-y-3">
              {Array.isArray(timeBlocks) && timeBlocks.map((block) => {
                const isSelected = formData.time_block === block.time;
                const isAvailable = block.status === 'available';
                
                return (
                <button
                  key={block.time}
                  onClick={() => isAvailable && handleTimeBlockSelect(block.time)}
                  disabled={!isAvailable}
                  className={`w-full p-4 rounded-lg text-left transition-all border ${
                    !isAvailable ? 'bg-gray-100 border-gray-200 cursor-not-allowed' : 'bg-white'
                  }`}
                  style={isAvailable ? {
                    borderWidth: isSelected ? '2px' : '1px',
                    borderColor: isSelected ? institutionData.primaryColor : '#e5e7eb',
                    backgroundColor: isSelected ? `${institutionData.primaryColor}10` : '#ffffff'
                  } : {}}
                  onMouseEnter={(e) => {
                    if (isAvailable && !isSelected) {
                      e.currentTarget.style.borderColor = institutionData.primaryColor;
                      e.currentTarget.style.backgroundColor = `${institutionData.primaryColor}08`;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (isAvailable && !isSelected) {
                      e.currentTarget.style.borderColor = '#e5e7eb';
                      e.currentTarget.style.backgroundColor = '#ffffff';
                    }
                  }}
                  data-testid={`time-block-${block.time}`}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-lg font-semibold text-[#2B3E50]">{block.time}</p>
                      <p className="text-sm text-gray-500">
                        {block.status === 'available' ? 'Volný' : block.status === 'unavailable' ? 'Lektor nedostupný' : 'Obsazeno'}
                      </p>
                    </div>
                  </div>
                </button>
                );
              })}
            </div>
            
            {/* Waitlist CTA - when no available slots or all booked */}
            {timeBlocks.length > 0 && timeBlocks.every(b => b.status !== 'available') && (
              <button
                onClick={() => { setWaitlistDate(formData.date); setShowWaitlist(true); }}
                className="w-full mt-4 p-3 border-2 border-dashed rounded-lg text-sm text-center transition-colors hover:bg-gray-50"
                style={{ borderColor: `${institutionData.primaryColor}40`, color: institutionData.primaryColor }}
                data-testid="waitlist-no-slots-btn"
              >
                <Bell className="w-4 h-4 inline mr-2" />
                Nenašli jste vhodný termín? <strong>Hlídat volný termín</strong>
              </button>
            )}
            
            <div 
              className="mt-6 p-4 rounded-md border"
              style={{ 
                backgroundColor: `${institutionData.primaryColor}10`,
                borderColor: `${institutionData.primaryColor}30`
              }}
            >
              <p className="text-sm" style={{ color: institutionData.primaryColor }}>
                Všechny časové bloky jsou 90 min. dlouhé. Prosím přiďte o 10 minut dříve, aby bylo dost času na organizační prvky.
              </p>
            </div>
            <div className="flex gap-3 mt-6">
              <Button
                variant="outline"
                className="flex-1 border-2 border-gray-300 rounded-lg"
                onClick={() => setStep(2)}
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                Zpět
              </Button>
              <Button
                className="flex-1 text-white hover:opacity-90 rounded-lg"
                style={{ backgroundColor: institutionData.accentColor }}
                onClick={() => {
                  if (!formData.time_block) {
                    toast.error('Vyberte prosím časový blok');
                    return;
                  }
                  setStep(4);
                }}
              >
                Pokračovat
              </Button>
            </div>
          </div>
        )}

        {step === 4 && (
          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-[#2B3E50] mb-2">Informace o skupině</h2>
                <p className="text-gray-600 mb-4">Řekněte nám o sobě více</p>

                <div className="space-y-4">
                  <div>
                    <Label className="text-[#2B3E50]">Škola / Název organizace *</Label>
                    <Input
                      value={formData.school_name}
                      onChange={(e) => setFormData({ ...formData, school_name: e.target.value })}
                      placeholder="Základní škola Komenského"
                      required
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-school-name"
                    />
                  </div>

                  <div>
                    <Label className="text-[#2B3E50]">Typ skupiny *</Label>
                    <Select
                      value={formData.group_type}
                      onValueChange={(value) => setFormData({ ...formData, group_type: value })}
                    >
                      <SelectTrigger className="mt-2 h-12 rounded-lg" data-testid="booking-group-type">
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
                    <Label className="text-[#2B3E50]">Věk / Třída *</Label>
                    <Input
                      value={formData.age_or_class}
                      onChange={(e) => setFormData({ ...formData, age_or_class: e.target.value })}
                      placeholder="3-4 roky"
                      required
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-age-class"
                    />
                  </div>

                  <div>
                    <Label className="text-[#2B3E50]">Počet studentů *</Label>
                    <Input
                      type="number"
                      value={formData.num_students}
                      onChange={(e) => setFormData({ ...formData, num_students: parseInt(e.target.value) })}
                      required
                      min={selectedProgram?.min_capacity || 5}
                      max={selectedProgram?.max_capacity || 30}
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-num-students"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Min. {selectedProgram?.min_capacity || 5}, Max {selectedProgram?.max_capacity || 30} osob.
                    </p>
                  </div>

                  <div>
                    <Label className="text-[#2B3E50]">Počet pedagogů *</Label>
                    <Input
                      type="number"
                      value={formData.num_teachers}
                      onChange={(e) => setFormData({ ...formData, num_teachers: parseInt(e.target.value) || 1 })}
                      required
                      min={1}
                      max={10}
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-num-teachers"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Minimálně 1 doprovázející pedagog.
                    </p>
                  </div>

                  <div>
                    <Label className="text-[#2B3E50]">Speciální požadavky</Label>
                    <Textarea
                      value={formData.special_requirements}
                      onChange={(e) => setFormData({ ...formData, special_requirements: e.target.value })}
                      placeholder="Zde můžete napsat poznámku pro lektora, pokud máte speciální požadavky, rádi Vám vyjdeme vstříc."
                      className="mt-2 rounded-lg border-gray-300"
                      rows={3}
                      data-testid="booking-special-requirements"
                    />
                  </div>
                </div>
              </div>

              <div>
                <h2 className="text-2xl font-bold text-[#2B3E50] mb-2">Kontaktní informace</h2>
                <p className="text-gray-600 mb-4">Hlavní kontakt pro vytvoření rezervace</p>

                <div className="space-y-4">
                  <div>
                    <Label className="text-[#2B3E50]">Jméno zodpovědné osoby *</Label>
                    <Input
                      value={formData.contact_name}
                      onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                      placeholder="Jméno Příjmení"
                      required
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-contact-name"
                    />
                  </div>

                  <div>
                    <Label className="text-[#2B3E50]">Emailová adresa *</Label>
                    <Input
                      type="email"
                      value={formData.contact_email}
                      onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                      placeholder="zakladni@skola.cz"
                      required
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-contact-email"
                    />
                  </div>

                  <div>
                    <Label className="text-[#2B3E50]">Telefonní číslo *</Label>
                    <Input
                      type="tel"
                      value={formData.contact_phone}
                      onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                      placeholder="+ 420 722 960 890"
                      required
                      className="mt-2 h-12 rounded-lg border-gray-300"
                      data-testid="booking-contact-phone"
                    />
                  </div>

                  <div className="flex items-start space-x-2 pt-2">
                    <Checkbox
                      id="gdpr"
                      checked={formData.gdpr_consent}
                      onCheckedChange={(checked) => setFormData({ ...formData, gdpr_consent: checked })}
                      data-testid="booking-gdpr"
                    />
                    <label htmlFor="gdpr" className="text-sm text-gray-700 leading-relaxed cursor-pointer">
                      Souhlasím se zpracováním osobních údajů v souladu s GDPR
                    </label>
                  </div>
                  
                  <div className="flex items-start space-x-2 pt-2">
                    <Checkbox
                      id="terms"
                      checked={formData.terms_accepted}
                      onCheckedChange={(checked) => setFormData({ ...formData, terms_accepted: checked })}
                      data-testid="booking-terms"
                    />
                    <label htmlFor="terms" className="text-sm text-gray-700 leading-relaxed cursor-pointer">
                      Odesláním rezervace beru na vědomí, že Budezivo.cz je pouze zprostředkovatelem rezervace a nenese odpovědnost za její realizaci.{' '}
                      <a 
                        href="/terms" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-[#5a7aae] hover:underline"
                      >
                        Více informací
                      </a>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1 border-2 border-gray-300 rounded-lg h-12"
                  onClick={() => setStep(3)}
                >
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Zpět
                </Button>
                <Button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 text-white hover:opacity-90 rounded-lg h-12"
                  style={{ backgroundColor: institutionData.accentColor }}
                  data-testid="booking-submit"
                >
                  {submitting ? 'Odesílání...' : 'Odeslat rezervaci'}
                </Button>
              </div>
            </div>
          </form>
        )}
      </div>

      {/* Waitlist Modal */}
      <WaitlistModal
        open={showWaitlist}
        onOpenChange={setShowWaitlist}
        institutionId={institutionId}
        programId={selectedProgram?.id}
        programName={selectedProgram?.name_cs || selectedProgram?.name_en}
        prefilledDate={waitlistDate}
      />
    </div>
  );
};
