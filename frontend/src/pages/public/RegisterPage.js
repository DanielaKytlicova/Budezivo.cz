import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AuthContext } from '../../context/AuthContext';
import { Header } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card } from '../../components/ui/card';
import { Checkbox } from '../../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import { Plus, Trash2, Upload } from 'lucide-react';

const STEPS = ['account', 'info', 'schedule', 'programs'];

const CZECH_CITIES = [
  'Praha', 'Brno', 'Ostrava', 'Plzeň', 'Liberec', 'Olomouc', 'České Budějovice',
  'Hradec Králové', 'Ústí nad Labem', 'Pardubice', 'Zlín', 'Havířov', 'Kladno',
  'Most', 'Opava', 'Frýdek-Místek', 'Karviná', 'Jihlava', 'Teplice', 'Děčín'
];

const DAYS = [
  { key: 'monday', label: 'Po' },
  { key: 'tuesday', label: 'Út' },
  { key: 'wednesday', label: 'St' },
  { key: 'thursday', label: 'Čt' },
  { key: 'friday', label: 'Pá' },
  { key: 'saturday', label: 'So' },
  { key: 'sunday', label: 'Ne' },
];

const TARGET_GROUPS = [
  { value: 'ms_3_6', label: 'MŠ (3-6 let)' },
  { value: 'zs1_7_12', label: 'I. stupeň ZŠ (7-12 let)' },
  { value: 'zs2_12_15', label: 'II. stupeň ZŠ (12-15 let)' },
  { value: 'ss_14_18', label: 'SŠ (14-18 let)' },
  { value: 'schools', label: 'Školy a veřejnost' },
];

export const RegisterPage = () => {
  const { t } = useTranslation();
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  
  const [formData, setFormData] = useState({
    // Step 1 - Account
    institution_name: '',
    institution_type: '',
    country: 'Česká republika',
    email: '',
    password: '',
    gdpr_consent: false,
    // Step 2 - Institution Info
    address: '',
    city: '',
    ico_dic: '',
    logo_url: '',
    primary_color: '#1E293B',
    secondary_color: '#84A98C',
    // Step 3 - Schedule
    default_available_days: [],
    default_time_blocks: [{ start: '09:00', end: '10:00' }],
    operating_start_date: '',
    operating_end_date: '',
    // Step 4 - Programs
    default_program_description: '',
    default_program_duration: 60,
    default_program_capacity: 30,
    default_target_group: 'zs1_7_12',
  });

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const toggleDay = (day) => {
    setFormData(prev => ({
      ...prev,
      default_available_days: prev.default_available_days.includes(day)
        ? prev.default_available_days.filter(d => d !== day)
        : [...prev.default_available_days, day]
    }));
  };

  const addTimeBlock = () => {
    setFormData(prev => ({
      ...prev,
      default_time_blocks: [...prev.default_time_blocks, { start: '09:00', end: '10:00' }]
    }));
  };

  const removeTimeBlock = (index) => {
    setFormData(prev => ({
      ...prev,
      default_time_blocks: prev.default_time_blocks.filter((_, i) => i !== index)
    }));
  };

  const updateTimeBlock = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      default_time_blocks: prev.default_time_blocks.map((block, i) =>
        i === index ? { ...block, [field]: value } : block
      )
    }));
  };

  const validateStep = (step) => {
    switch (step) {
      case 0:
        if (!formData.institution_name || !formData.institution_type || !formData.email || !formData.password) {
          toast.error('Vyplňte prosím všechna povinná pole');
          return false;
        }
        if (!formData.gdpr_consent) {
          toast.error('Pro pokračování musíte souhlasit se zpracováním osobních údajů');
          return false;
        }
        return true;
      case 1:
      case 2:
      case 3:
        return true; // Optional steps
      default:
        return true;
    }
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const skipStep = () => {
    setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await register(formData);
      toast.success('Účet instituce byl úspěšně vytvořen!');
      navigate('/admin');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Při registraci došlo k chybě');
    } finally {
      setLoading(false);
    }
  };

  const renderProgressBar = () => (
    <div className="w-full mb-8">
      <div className="h-1 bg-gray-200 rounded-full">
        <div 
          className="h-1 bg-slate-800 rounded-full transition-all duration-300"
          style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
        />
      </div>
    </div>
  );

  const renderStep1 = () => (
    <div className="space-y-6" data-testid="register-step-1">
      {/* Logo placeholder */}
      <div className="flex justify-center mb-6">
        <div className="w-32 h-16 bg-gray-100 rounded flex items-center justify-center text-gray-400 text-sm">
          Logo
        </div>
      </div>

      <div>
        <Label htmlFor="institution_name">Název instituce</Label>
        <Input
          id="institution_name"
          data-testid="register-institution-name"
          value={formData.institution_name}
          onChange={(e) => updateField('institution_name', e.target.value)}
          placeholder="Oblastní galerie"
          required
          className="mt-2"
        />
      </div>

      <div>
        <Label htmlFor="institution_type">Typ instituce</Label>
        <Select
          value={formData.institution_type}
          onValueChange={(value) => updateField('institution_type', value)}
        >
          <SelectTrigger className="mt-2" data-testid="register-institution-type">
            <SelectValue placeholder="vyber typ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="museum">Muzeum</SelectItem>
            <SelectItem value="gallery">Galerie</SelectItem>
            <SelectItem value="library">Knihovna</SelectItem>
            <SelectItem value="botanical_garden">Botanická zahrada</SelectItem>
            <SelectItem value="theater">Divadlo</SelectItem>
            <SelectItem value="other">Jiné</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="country">Země</Label>
        <Select
          value={formData.country}
          onValueChange={(value) => updateField('country', value)}
        >
          <SelectTrigger className="mt-2" data-testid="register-country">
            <SelectValue placeholder="vyber zemi" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Česká republika">Česká republika</SelectItem>
            <SelectItem value="Slovensko">Slovensko</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="email">Admin email</Label>
        <Input
          id="email"
          type="email"
          data-testid="register-email"
          value={formData.email}
          onChange={(e) => updateField('email', e.target.value)}
          placeholder="admin@galerie.cz"
          required
          className="mt-2"
        />
      </div>

      <div>
        <Label htmlFor="password">Heslo</Label>
        <Input
          id="password"
          type="password"
          data-testid="register-password"
          value={formData.password}
          onChange={(e) => updateField('password', e.target.value)}
          placeholder="••••••"
          required
          className="mt-2"
        />
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="gdpr_consent"
          data-testid="register-gdpr-consent"
          checked={formData.gdpr_consent}
          onCheckedChange={(checked) => updateField('gdpr_consent', checked)}
        />
        <label htmlFor="gdpr_consent" className="text-sm text-gray-600 cursor-pointer">
          <Link to="/gdpr" className="underline hover:text-slate-800">
            Souhlasím se zpracováním osobních údajů
          </Link>
        </label>
      </div>

      <Button
        type="button"
        data-testid="register-submit-step1"
        className="w-full bg-slate-800 text-white hover:bg-slate-700"
        onClick={nextStep}
      >
        Vytvořit účet
      </Button>

      <div className="text-center text-sm">
        <span className="text-gray-500">Už máš uživatelský účet? </span>
        <Link to="/login" className="text-slate-800 font-medium hover:underline">
          Přihlásit se
        </Link>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6" data-testid="register-step-2">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Základní informace</h2>
      </div>

      <div>
        <Label htmlFor="address">Adresa instituce</Label>
        <Input
          id="address"
          data-testid="register-address"
          value={formData.address}
          onChange={(e) => updateField('address', e.target.value)}
          placeholder="Zahradní 101"
          className="mt-2"
        />
      </div>

      <div>
        <Label htmlFor="city">Město</Label>
        <Select
          value={formData.city}
          onValueChange={(value) => updateField('city', value)}
        >
          <SelectTrigger className="mt-2" data-testid="register-city">
            <SelectValue placeholder="vyber typ" />
          </SelectTrigger>
          <SelectContent>
            {CZECH_CITIES.map(city => (
              <SelectItem key={city} value={city}>{city}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="ico_dic">IČ/DIČ</Label>
        <Input
          id="ico_dic"
          data-testid="register-ico"
          value={formData.ico_dic}
          onChange={(e) => updateField('ico_dic', e.target.value)}
          placeholder="CZ123456"
          className="mt-2"
        />
      </div>

      <div>
        <Label>Logo instituce</Label>
        <div className="mt-2 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Vyberte monochromatické logo</p>
          <p className="text-xs text-gray-400">max. 150x60 px</p>
          <Input
            type="text"
            data-testid="register-logo-url"
            value={formData.logo_url}
            onChange={(e) => updateField('logo_url', e.target.value)}
            placeholder="URL loga (např. https://...)"
            className="mt-3 text-sm"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="primary_color">Hlavní barevnost</Label>
          <div className="flex items-center gap-2 mt-2">
            <input
              type="color"
              id="primary_color"
              data-testid="register-primary-color"
              value={formData.primary_color}
              onChange={(e) => updateField('primary_color', e.target.value)}
              className="w-10 h-10 rounded border cursor-pointer"
            />
            <Input
              value={formData.primary_color}
              onChange={(e) => updateField('primary_color', e.target.value)}
              className="flex-1"
            />
          </div>
        </div>
        <div>
          <Label htmlFor="secondary_color">Sekundární barevnost</Label>
          <div className="flex items-center gap-2 mt-2">
            <input
              type="color"
              id="secondary_color"
              data-testid="register-secondary-color"
              value={formData.secondary_color}
              onChange={(e) => updateField('secondary_color', e.target.value)}
              className="w-10 h-10 rounded border cursor-pointer"
            />
            <Input
              value={formData.secondary_color}
              onChange={(e) => updateField('secondary_color', e.target.value)}
              className="flex-1"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="ghost" onClick={skipStep} data-testid="register-skip-step2">
          Přeskočit
        </Button>
        <Button onClick={nextStep} className="bg-slate-800 text-white hover:bg-slate-700" data-testid="register-next-step2">
          Další
        </Button>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6" data-testid="register-step-3">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Nabídka návštěvní doby</h2>
      </div>

      <div>
        <Label>Dny v týdnu</Label>
        <div className="flex flex-wrap gap-2 mt-2">
          {DAYS.map(day => (
            <button
              key={day.key}
              type="button"
              data-testid={`register-day-${day.key}`}
              onClick={() => toggleDay(day.key)}
              className={`w-10 h-10 rounded-lg border text-sm font-medium transition-colors ${
                formData.default_available_days.includes(day.key)
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
              }`}
            >
              {day.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <Label>Časový blok</Label>
        <div className="space-y-3 mt-2">
          {formData.default_time_blocks.map((block, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                type="time"
                data-testid={`register-time-start-${index}`}
                value={block.start}
                onChange={(e) => updateTimeBlock(index, 'start', e.target.value)}
                className="flex-1"
              />
              <span className="text-gray-400">—</span>
              <Input
                type="time"
                data-testid={`register-time-end-${index}`}
                value={block.end}
                onChange={(e) => updateTimeBlock(index, 'end', e.target.value)}
                className="flex-1"
              />
              {formData.default_time_blocks.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeTimeBlock(index)}
                  className="text-red-500 hover:text-red-600"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addTimeBlock}
            data-testid="register-add-time-block"
            className="text-sm text-slate-600 hover:text-slate-800 flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            Přidat další blok
          </button>
        </div>
      </div>

      <div>
        <Label>Termín</Label>
        <div className="grid grid-cols-2 gap-4 mt-2">
          <div>
            <Input
              type="date"
              data-testid="register-start-date"
              value={formData.operating_start_date}
              onChange={(e) => updateField('operating_start_date', e.target.value)}
              placeholder="dd.mm.rrrr"
            />
          </div>
          <div>
            <Input
              type="date"
              data-testid="register-end-date"
              value={formData.operating_end_date}
              onChange={(e) => updateField('operating_end_date', e.target.value)}
              placeholder="dd.mm.rrrr"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="ghost" onClick={prevStep} data-testid="register-back-step3">
          Zpět
        </Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={skipStep} data-testid="register-skip-step3">
            Přeskočit
          </Button>
          <Button onClick={nextStep} className="bg-slate-800 text-white hover:bg-slate-700" data-testid="register-next-step3">
            Další
          </Button>
        </div>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="space-y-6" data-testid="register-step-4">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Hlavní nastavení doprovodných programů</h2>
        <p className="text-sm text-gray-500 mt-1">Lze editovat u jednotlivých programů samostatně</p>
      </div>

      <div>
        <Label htmlFor="default_program_description">Popis</Label>
        <Textarea
          id="default_program_description"
          data-testid="register-program-description"
          value={formData.default_program_description}
          onChange={(e) => updateField('default_program_description', e.target.value)}
          placeholder="Uveďte bližší informace pro pedagogy"
          className="mt-2"
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="default_program_duration">Délka (min)</Label>
          <Input
            id="default_program_duration"
            type="number"
            data-testid="register-program-duration"
            value={formData.default_program_duration}
            onChange={(e) => updateField('default_program_duration', parseInt(e.target.value) || 60)}
            className="mt-2"
          />
        </div>
        <div>
          <Label htmlFor="default_program_capacity">Kapacita</Label>
          <Input
            id="default_program_capacity"
            type="number"
            data-testid="register-program-capacity"
            value={formData.default_program_capacity}
            onChange={(e) => updateField('default_program_capacity', parseInt(e.target.value) || 30)}
            className="mt-2"
          />
        </div>
      </div>

      <div>
        <Label htmlFor="default_target_group">Cílová skupina</Label>
        <Select
          value={formData.default_target_group}
          onValueChange={(value) => updateField('default_target_group', value)}
        >
          <SelectTrigger className="mt-2" data-testid="register-target-group">
            <SelectValue placeholder="Vyberte cílovou skupinu" />
          </SelectTrigger>
          <SelectContent>
            {TARGET_GROUPS.map(group => (
              <SelectItem key={group.value} value={group.value}>{group.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="ghost" onClick={prevStep} data-testid="register-back-step4">
          Zpět
        </Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={skipStep} data-testid="register-skip-step4">
            Přeskočit
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={loading}
            className="bg-slate-800 text-white hover:bg-slate-700" 
            data-testid="register-finish"
          >
            {loading ? 'Vytváření...' : 'Dokončit'}
          </Button>
        </div>
      </div>
    </div>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 0: return renderStep1();
      case 1: return renderStep2();
      case 2: return renderStep3();
      case 3: return renderStep4();
      default: return renderStep1();
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      <Header />
      <div className="max-w-md mx-auto px-4 py-8 md:py-16">
        <Card className="p-6 md:p-8">
          {currentStep > 0 && renderProgressBar()}
          {renderCurrentStep()}
        </Card>
      </div>
    </div>
  );
};
