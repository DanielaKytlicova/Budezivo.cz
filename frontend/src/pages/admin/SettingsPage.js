import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Switch } from '../../components/ui/switch';
import { AuthContext } from '../../context/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import { 
  ArrowLeft, 
  ChevronRight, 
  Building2, 
  Users, 
  Bell, 
  Globe, 
  Shield, 
  LogOut,
  Upload
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Menu položky nastavení
const SETTINGS_MENU = [
  {
    id: 'institution',
    icon: Building2,
    title: 'Správa instituce',
    description: 'Název, adresa, kontaktní údaje, logo',
  },
  {
    id: 'users',
    icon: Users,
    title: 'Uživatelé a role',
    description: 'Správa uživatelů a oprávnění',
    link: '/admin/team',
  },
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifikace',
    description: 'Nastavení mailingu a sms upozornění',
  },
  {
    id: 'locale',
    icon: Globe,
    title: 'Jazyk a místo',
    description: 'Správa jazyku, časového a datového formátování',
  },
  {
    id: 'gdpr',
    icon: Shield,
    title: 'GDPR a reporting dat',
    description: 'Nastavení soukromí a export dat pro výroční zprávy',
    isPro: true,
  },
];

const INSTITUTION_TYPES = [
  { value: 'museum', label: 'Muzeum' },
  { value: 'gallery', label: 'Galerie' },
  { value: 'library', label: 'Knihovna' },
  { value: 'botanical_garden', label: 'Botanická zahrada' },
  { value: 'theater', label: 'Divadlo' },
  { value: 'other', label: 'Jiné' },
];

const COUNTRIES = [
  { value: 'cz', label: 'Česká Republika' },
  { value: 'sk', label: 'Slovensko' },
];

const LANGUAGES = [
  { value: 'cs', label: 'Čeština' },
  { value: 'en', label: 'English' },
];

const TIMEZONES = [
  { value: 'europe', label: 'Evropa' },
  { value: 'utc', label: 'UTC' },
];

const DATE_FORMATS = [
  { value: 'dd.mm.yyyy', label: 'DD.MM.RRRR' },
  { value: 'yyyy-mm-dd', label: 'RRRR-MM-DD' },
  { value: 'mm/dd/yyyy', label: 'MM/DD/RRRR' },
];

const TIME_FORMATS = [
  { value: '24h', label: '24-hodin' },
  { value: '12h', label: '12-hodin' },
];

const DATA_RETENTION = [
  { value: 'never', label: 'Nikdy' },
  { value: '1year', label: '1 rok' },
  { value: '2years', label: '2 roky' },
  { value: '5years', label: '5 let' },
];

export const SettingsPage = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [activeSection, setActiveSection] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Institution data
  const [institutionData, setInstitutionData] = useState({
    name: '',
    type: 'gallery',
    ico_dic: '',
    address: '',
    city: '',
    psc: '',
    country: 'cz',
    phone: '',
    email: '',
    website: '',
    logo_url: '',
    primary_color: '#123456',
    secondary_color: '#123456',
  });

  // Notification settings
  const [notifications, setNotifications] = useState({
    new_reservation: false,
    confirmation: false,
    cancellation: true,
    sms_enabled: false,
  });

  // Locale settings
  const [locale, setLocale] = useState({
    language: 'cs',
    timezone: 'europe',
    date_format: 'dd.mm.yyyy',
    time_format: '24h',
  });

  // GDPR settings
  const [gdprSettings, setGdprSettings] = useState({
    data_retention: 'never',
    anonymize: false,
  });

  useEffect(() => {
    if (activeSection === 'institution') {
      fetchInstitutionData();
    }
  }, [activeSection]);

  const fetchInstitutionData = async () => {
    try {
      const response = await axios.get(`${API}/institution/settings`);
      if (response.data) {
        setInstitutionData(prev => ({ ...prev, ...response.data }));
      }
    } catch (error) {
      // Use defaults if no data
    }
  };

  const handleSaveInstitution = async () => {
    setLoading(true);
    try {
      await axios.put(`${API}/institution/settings`, institutionData);
      toast.success('Nastavení bylo uloženo');
    } catch (error) {
      toast.error('Nepodařilo se uložit nastavení');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNotifications = async () => {
    setLoading(true);
    try {
      await axios.put(`${API}/settings/notifications`, notifications);
      toast.success('Nastavení notifikací bylo uloženo');
    } catch (error) {
      toast.error('Nepodařilo se uložit nastavení');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveLocale = async () => {
    setLoading(true);
    try {
      await axios.put(`${API}/settings/locale`, locale);
      toast.success('Nastavení bylo uloženo');
    } catch (error) {
      toast.error('Nepodařilo se uložit nastavení');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveGdpr = async () => {
    setLoading(true);
    try {
      await axios.put(`${API}/settings/gdpr`, gdprSettings);
      toast.success('Nastavení bylo uloženo');
    } catch (error) {
      toast.error('Nepodařilo se uložit nastavení');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Render hlavní menu nastavení
  const renderMainMenu = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/admin')} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Nastavení</h1>
      </div>

      <div className="space-y-3">
        {SETTINGS_MENU.map((item) => {
          const Icon = item.icon;
          return (
            <Card
              key={item.id}
              className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => item.link ? navigate(item.link) : setActiveSection(item.id)}
              data-testid={`settings-${item.id}`}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 border border-gray-200 rounded-lg flex items-center justify-center">
                  <Icon className="w-6 h-6 text-gray-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-slate-900">{item.title}</h3>
                    {item.isPro && (
                      <span className="px-2 py-0.5 text-xs font-medium bg-[#2B3E50] text-white rounded">
                        PRO
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500">{item.description}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            </Card>
          );
        })}

        {/* Odhlásit se */}
        <Card
          className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={handleLogout}
          data-testid="settings-logout"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 border border-gray-200 rounded-lg flex items-center justify-center">
              <LogOut className="w-6 h-6 text-gray-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-slate-900">Odhlásit se</h3>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );

  // Render Správa instituce
  const renderInstitutionSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Správa instituce</h1>
      </div>

      {/* Základní informace */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Základní informace</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Název instituce</Label>
          <Input
            value={institutionData.name}
            onChange={(e) => setInstitutionData({ ...institutionData, name: e.target.value })}
            placeholder="Oblastní galerie"
            className="mt-1"
            data-testid="institution-name"
          />
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Typ instituce</Label>
          <Select
            value={institutionData.type}
            onValueChange={(value) => setInstitutionData({ ...institutionData, type: value })}
          >
            <SelectTrigger className="mt-1" data-testid="institution-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {INSTITUTION_TYPES.map(type => (
                <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="text-gray-600 text-sm">IČ/DIČ</Label>
          <Input
            value={institutionData.ico_dic}
            onChange={(e) => setInstitutionData({ ...institutionData, ico_dic: e.target.value })}
            placeholder="CZ123456"
            className="mt-1"
            data-testid="institution-ico"
          />
        </div>
      </Card>

      {/* Fakturační údaje */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Fakturační údaje</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Adresa</Label>
          <Input
            value={institutionData.address}
            onChange={(e) => setInstitutionData({ ...institutionData, address: e.target.value })}
            placeholder="Nová ulice 123"
            className="mt-1"
            data-testid="institution-address"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-gray-600 text-sm">Město</Label>
            <Input
              value={institutionData.city}
              onChange={(e) => setInstitutionData({ ...institutionData, city: e.target.value })}
              placeholder="Praha"
              className="mt-1"
              data-testid="institution-city"
            />
          </div>
          <div>
            <Label className="text-gray-600 text-sm">PSČ</Label>
            <Input
              value={institutionData.psc}
              onChange={(e) => setInstitutionData({ ...institutionData, psc: e.target.value })}
              placeholder="123 45"
              className="mt-1"
              data-testid="institution-psc"
            />
          </div>
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Země</Label>
          <Select
            value={institutionData.country}
            onValueChange={(value) => setInstitutionData({ ...institutionData, country: value })}
          >
            <SelectTrigger className="mt-1" data-testid="institution-country">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {COUNTRIES.map(country => (
                <SelectItem key={country.value} value={country.value}>{country.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Kontaktní informace */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Kontaktní informace</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Mobil</Label>
          <Input
            value={institutionData.phone}
            onChange={(e) => setInstitutionData({ ...institutionData, phone: e.target.value })}
            placeholder="+ 420 123 456 789"
            className="mt-1"
            data-testid="institution-phone"
          />
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Email</Label>
          <Input
            type="email"
            value={institutionData.email}
            onChange={(e) => setInstitutionData({ ...institutionData, email: e.target.value })}
            placeholder="galerie@mesto.cz"
            className="mt-1"
            data-testid="institution-email"
          />
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Webovky</Label>
          <Input
            value={institutionData.website}
            onChange={(e) => setInstitutionData({ ...institutionData, website: e.target.value })}
            placeholder="https://galerie.cz"
            className="mt-1"
            data-testid="institution-website"
          />
        </div>
      </Card>

      {/* Logo a vizuál */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Logo a vizuál</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Logo instituce</Label>
          <div className="mt-2 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
            <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-500">Vyberte monochronní logo</p>
            <p className="text-xs text-gray-400">max. 150×60 px</p>
            <Input
              type="text"
              value={institutionData.logo_url}
              onChange={(e) => setInstitutionData({ ...institutionData, logo_url: e.target.value })}
              placeholder="URL loga"
              className="mt-3 text-sm"
              data-testid="institution-logo"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-gray-600 text-sm">Hlavní barevnost</Label>
            <div className="flex items-center gap-2 mt-1">
              <input
                type="color"
                value={institutionData.primary_color}
                onChange={(e) => setInstitutionData({ ...institutionData, primary_color: e.target.value })}
                className="w-10 h-10 rounded border cursor-pointer"
              />
              <Input
                value={institutionData.primary_color}
                onChange={(e) => setInstitutionData({ ...institutionData, primary_color: e.target.value })}
                className="flex-1"
                data-testid="institution-primary-color"
              />
            </div>
          </div>
          <div>
            <Label className="text-gray-600 text-sm">Sekundární barevnost</Label>
            <div className="flex items-center gap-2 mt-1">
              <input
                type="color"
                value={institutionData.secondary_color}
                onChange={(e) => setInstitutionData({ ...institutionData, secondary_color: e.target.value })}
                className="w-10 h-10 rounded border cursor-pointer"
              />
              <Input
                value={institutionData.secondary_color}
                onChange={(e) => setInstitutionData({ ...institutionData, secondary_color: e.target.value })}
                className="flex-1"
                data-testid="institution-secondary-color"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Save button */}
      <Button
        onClick={handleSaveInstitution}
        disabled={loading}
        className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
        data-testid="save-institution"
      >
        {loading ? 'Ukládání...' : 'Uložit'}
      </Button>
    </div>
  );

  // Render Notifikace
  const renderNotificationSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Notifikace a upozornění</h1>
      </div>

      {/* Mailová upozornění */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Mailová upozornění</h2>
        
        <div className="flex items-start gap-3">
          <Switch
            checked={notifications.new_reservation}
            onCheckedChange={(checked) => setNotifications({ ...notifications, new_reservation: checked })}
            data-testid="notify-new-reservation"
          />
          <div>
            <p className="font-medium text-slate-900">Nově vytvořená rezervace</p>
            <p className="text-sm text-gray-500">Rezervace vyžaduje schválení před finálním potvrzením.</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Switch
            checked={notifications.confirmation}
            onCheckedChange={(checked) => setNotifications({ ...notifications, confirmation: checked })}
            data-testid="notify-confirmation"
          />
          <div>
            <p className="font-medium text-slate-900">Potvrzení rezervace</p>
            <p className="text-sm text-gray-500">Všichni návštěvníci uvidí tento program v online nabídce.</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Switch
            checked={notifications.cancellation}
            onCheckedChange={(checked) => setNotifications({ ...notifications, cancellation: checked })}
            data-testid="notify-cancellation"
          />
          <div>
            <p className="font-medium text-slate-900">Zrušení rezervace</p>
            <p className="text-sm text-gray-500">Automaticky odešle mailem upozornění 2 pracovní dny před návštěvou.</p>
          </div>
        </div>
      </Card>

      {/* SMS upozornění */}
      <Card className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">SMS upozornění</h2>
          <span className="px-2 py-0.5 text-xs font-medium bg-[#2B3E50] text-white rounded">
            PRO
          </span>
        </div>
        
        <div className="flex items-start gap-3 opacity-60">
          <Switch
            checked={notifications.sms_enabled}
            onCheckedChange={(checked) => setNotifications({ ...notifications, sms_enabled: checked })}
            disabled
            data-testid="notify-sms"
          />
          <div>
            <p className="font-medium text-slate-900">Odeslat upozornění mailem</p>
            <p className="text-sm text-gray-500">Automaticky odešle mailem upozornění 2 pracovní dny před návštěvou.</p>
          </div>
        </div>

        <p className="text-sm font-medium text-slate-700">
          Vylepši svůj plán a zapni SMS upozornění
        </p>
      </Card>

      {/* Save button */}
      <Button
        onClick={handleSaveNotifications}
        disabled={loading}
        className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
        data-testid="save-notifications"
      >
        {loading ? 'Ukládání...' : 'Uložit'}
      </Button>
    </div>
  );

  // Render Jazyk a místo
  const renderLocaleSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Jazyk a místo</h1>
      </div>

      {/* Nastavení jazyka */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Nastavení jazyka</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Jazykové rozhraní</Label>
          <Select
            value={locale.language}
            onValueChange={(value) => setLocale({ ...locale, language: value })}
          >
            <SelectTrigger className="mt-1" data-testid="locale-language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGES.map(lang => (
                <SelectItem key={lang.value} value={lang.value}>{lang.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Místní nastavení */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Místní nastavení</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Časové pásmo</Label>
          <Select
            value={locale.timezone}
            onValueChange={(value) => setLocale({ ...locale, timezone: value })}
          >
            <SelectTrigger className="mt-1" data-testid="locale-timezone">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map(tz => (
                <SelectItem key={tz.value} value={tz.value}>{tz.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Datový formát</Label>
          <Select
            value={locale.date_format}
            onValueChange={(value) => setLocale({ ...locale, date_format: value })}
          >
            <SelectTrigger className="mt-1" data-testid="locale-date-format">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DATE_FORMATS.map(fmt => (
                <SelectItem key={fmt.value} value={fmt.value}>{fmt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Časový formát</Label>
          <Select
            value={locale.time_format}
            onValueChange={(value) => setLocale({ ...locale, time_format: value })}
          >
            <SelectTrigger className="mt-1" data-testid="locale-time-format">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIME_FORMATS.map(fmt => (
                <SelectItem key={fmt.value} value={fmt.value}>{fmt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Save button */}
      <Button
        onClick={handleSaveLocale}
        disabled={loading}
        className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
        data-testid="save-locale"
      >
        {loading ? 'Ukládání...' : 'Uložit'}
      </Button>
    </div>
  );

  // Render GDPR a export dat
  const renderGdprSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">GDPR a export dat</h1>
      </div>

      {/* Upgrade banner */}
      <div className="bg-gray-100 rounded-lg p-4 flex items-center gap-3">
        <Shield className="w-6 h-6 text-gray-600" />
        <p className="text-sm">
          <span className="underline font-medium">Vylepši svůj plán</span> a získej více funkcí, které ti ušetří čas.
        </p>
      </div>

      {/* Export dat a report */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Export dat a report</h2>
        <p className="text-sm text-gray-500">
          Nastavení exportu dat například pro výroční zprávy nebo grafy obsazenosti jednotlivých doprovodných programů
        </p>
        
        <Button
          variant="outline"
          className="w-full border-gray-300"
          data-testid="export-data-button"
        >
          Získat funkci exportu dat
        </Button>
      </Card>

      {/* Ukládání dat */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Ukládání dat</h2>
        
        <div>
          <Label className="text-gray-600 text-sm">Smaž rezervace po uplynutí</Label>
          <Select
            value={gdprSettings.data_retention}
            onValueChange={(value) => setGdprSettings({ ...gdprSettings, data_retention: value })}
          >
            <SelectTrigger className="mt-1" data-testid="gdpr-retention">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DATA_RETENTION.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Nastavení soukromí */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Nastavení soukromí</h2>
        
        <div className="flex items-start gap-3">
          <Switch
            checked={gdprSettings.anonymize}
            onCheckedChange={(checked) => setGdprSettings({ ...gdprSettings, anonymize: checked })}
            data-testid="gdpr-anonymize"
          />
          <div>
            <p className="font-medium text-slate-900">Netuším</p>
            <p className="text-sm text-gray-500">Automaticky odešle mailem upozornění 2 pracovní dny před návštěvou.</p>
          </div>
        </div>
      </Card>

      {/* Save button */}
      <Button
        onClick={handleSaveGdpr}
        disabled={loading}
        className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
        data-testid="save-gdpr"
      >
        {loading ? 'Ukládání...' : 'Uložit'}
      </Button>
    </div>
  );

  // Render based on active section
  const renderContent = () => {
    switch (activeSection) {
      case 'institution':
        return renderInstitutionSettings();
      case 'notifications':
        return renderNotificationSettings();
      case 'locale':
        return renderLocaleSettings();
      case 'gdpr':
        return renderGdprSettings();
      default:
        return renderMainMenu();
    }
  };

  return (
    <AdminLayout>
      {renderContent()}
    </AdminLayout>
  );
};
