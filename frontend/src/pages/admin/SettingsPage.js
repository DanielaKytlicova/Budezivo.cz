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
  Upload,
  Trash2,
  AlertTriangle,
  Crown,
  Loader2,
  CheckCircle,
  Lock,
  FileText,
  ClipboardList,
  CreditCard,
  LayoutDashboard,
  Calendar,
  BookOpen,
  School,
  MessageSquare,
  Mail,
  GraduationCap,
  BarChart3,
  CalendarDays,
  RefreshCw
} from 'lucide-react';
import { Checkbox } from '../../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import ComgatePortalUrls from '../../components/settings/ComgatePortalUrls';
import { API, resolveAssetUrl } from '../../config/api';

// Menu položky nastavení — group key drives visual section in the hub.
const SETTINGS_MENU = [
  {
    id: 'institution',
    icon: Building2,
    title: 'Správa instituce',
    description: 'Název, adresa, kontaktní údaje, logo',
    group: 'general',
  },
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifikace',
    description: 'Nastavení mailingu a sms upozornění',
    group: 'general',
  },
  {
    id: 'locale',
    icon: Globe,
    title: 'Jazyk a místo',
    description: 'Správa jazyku, časového a datového formátování',
    group: 'general',
  },
  {
    id: 'users',
    icon: Users,
    title: 'Uživatelé a role',
    description: 'Správa uživatelů a oprávnění',
    link: '/admin/team',
    group: 'access',
  },
  {
    id: 'password',
    icon: Lock,
    title: 'Změna hesla',
    description: 'Změňte si přihlašovací heslo k účtu',
    group: 'access',
  },
  {
    id: 'pro',
    icon: Shield,
    title: 'PRO funkce',
    description: 'CSV export, hromadná propagace, email šablony',
    isPro: true,
    group: 'billing',
  },
  {
    id: 'payment',
    icon: CreditCard,
    title: 'Platební nastavení',
    description: 'Bankovní účet pro příjem plateb za události',
    isPro: true,
    group: 'billing',
  },
  {
    id: 'gdpr',
    icon: Shield,
    title: 'GDPR a správa dat',
    description: 'Export dat, anonymizace, nastavení soukromí',
    group: 'legal',
  },
  {
    id: 'vop',
    icon: FileText,
    title: 'Obchodní podmínky (VOP)',
    description: 'Všeobecné obchodní podmínky platformy',
    group: 'legal',
  },
  {
    id: 'audit',
    icon: ClipboardList,
    title: 'Audit log',
    description: 'Historie všech změn a akcí v systému',
    link: '/admin/audit-log',
    group: 'system',
  },
];

// Grouped sections rendered in the hub (order matters).
const SETTINGS_GROUPS = [
  { key: 'general',  label: 'Obecné' },
  { key: 'access',   label: 'Uživatelé a přístup' },
  { key: 'billing',  label: 'Platby a PRO' },
  { key: 'legal',    label: 'Data a legislativa' },
  { key: 'system',   label: 'Systém' },
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
  const [logoUploading, setLogoUploading] = useState(false);
  
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

  // Notification settings (normalized nested structure)
  const [notifications, setNotifications] = useState(null); // null = not loaded yet
  const [notifTeam, setNotifTeam] = useState([]);            // eligible recipients

  const CUSTOMER_NOTIF_META = [
    { key: 'reservation_created', title: 'Přijetí rezervace', desc: 'Po vytvoření rezervace odešle objednávajícímu potvrzení, že systém rezervaci přijal.' },
    { key: 'reservation_confirmed', title: 'Potvrzení rezervace', desc: 'Po schválení rezervace odešle objednávajícímu definitivní potvrzení.' },
    { key: 'reservation_cancelled', title: 'Zrušení rezervace', desc: 'Po zrušení rezervace odešle objednávajícímu informační e-mail.' },
    { key: 'visit_reminder', title: 'Připomínka před návštěvou', desc: 'Odešle objednávajícímu připomínku dva pracovní dny před návštěvou.' },
    { key: 'event_registration_received', title: 'Přijetí registrace na akci', desc: 'Po přihlášení na jednorázovou akci odešle účastníkovi potvrzení o přijetí registrace.' },
    { key: 'event_registration_confirmed', title: 'Potvrzení místa na akci', desc: 'Po schválení přihlášky nebo přesunu z čekací listiny odešle účastníkovi potvrzení místa.' },
    { key: 'event_registration_cancelled', title: 'Zrušení účasti na akci', desc: 'Po zrušení přihlášky odešle účastníkovi informační e-mail.' },
  ];
  const ADMIN_NOTIF_META = [
    { key: 'new_reservation', title: 'Nová rezervace', desc: 'Po vytvoření rezervace upozorní vybrané příjemce instituce.' },
    { key: 'reservation_cancelled', title: 'Zrušená rezervace', desc: 'Po zrušení rezervace upozorní vybrané příjemce (program, termín, uvolněná kapacita, čekací listina).' },
    { key: 'event_capacity_reached', title: 'Naplnění kapacity akce', desc: 'Upozorní při prvním přechodu konkrétního termínu na plnou kapacitu.' },
    { key: 'new_event_registration', title: 'Nová přihláška na akci', desc: 'Upozorní na novou přihlášku, její stav, platební metodu a případnou čekací listinu.' },
    { key: 'integration_error', title: 'Chyba synchronizace kalendáře', desc: 'Upozorní až po několika po sobě jdoucích selháních Google nebo Outlook synchronizace.' },
  ];
  const UPCOMING_NOTIF_META = [
    { title: 'Pravidelná sumarizace obsazenosti programů', desc: 'Souhrnný přehled naplněnosti programů v pravidelném intervalu.' },
    { title: 'Pravidelný přehled plateb', desc: 'Přehled přijatých a čekajících plateb.' },
    { title: 'Provozní přehled rezervací, místností a lektorů', desc: 'Denní/týdenní provozní souhrn.' },
  ];

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
  const [exportLoading, setExportLoading] = useState(false);
  const [bulkExportLoading, setBulkExportLoading] = useState(false);
  const [anonymizeDialog, setAnonymizeDialog] = useState(false);
  const [anonymizeConfirm, setAnonymizeConfirm] = useState('');
  const [anonymizeLoading, setAnonymizeLoading] = useState(false);

  // Password change
  const [pwdCurrent, setPwdCurrent] = useState('');
  const [pwdNew, setPwdNew] = useState('');
  const [pwdConfirm, setPwdConfirm] = useState('');
  const [changingPwd, setChangingPwd] = useState(false);
  // VOP state
  const [vopData, setVopData] = useState(null);
  const [vopLoading, setVopLoading] = useState(false);

  // PRO settings
  const [proSettings, setProSettings] = useState({
    csv_export_enabled: true,
    mass_propagation_enabled: true,
    email_subject_template: 'Nový program: {program_name}',
    email_body_template: 'Dobrý den,\n\nrádi bychom Vás informovali o novém programu {program_name}.\n\n{program_description}\n\nRezervovat můžete zde: {reservation_url}\n\nS pozdravem,\n{institution_name}',
  });
  const [isPro, setIsPro] = useState(false);

  // Delete account state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  
  // Plan upgrade state
  const [planData, setPlanData] = useState({ plan: 'free', is_pro: false, plan_updated_at: null });
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgrading, setUpgrading] = useState(false);

  // Payment settings state
  const [paymentSettings, setPaymentSettings] = useState({
    payment_mode: 'qr', account_number: '', bank_code: '', account_name: '', iban: '',
    provider: null, gateway_api_key: '', gateway_secret: '',
  });
  const [eventsEnabled, setEventsEnabled] = useState(false);
  const [disableConfirm, setDisableConfirm] = useState(null);

  const togglePaymentMethod = (m) => {
    setPaymentSettings(p => {
      const cur = p.allowed_methods || [];
      return { ...p, allowed_methods: cur.includes(m) ? cur.filter(x => x !== m) : [...cur, m] };
    });
  };

  useEffect(() => {
    if (activeSection === 'institution') {
      fetchInstitutionData();
    } else if (activeSection === 'pro') {
      fetchProSettings();
      fetchPlanStatus();
    } else if (activeSection === 'payment') {
      fetchPaymentSettings();
      fetchEventsFlag();
    } else if (activeSection === 'vop' && !vopData) {
      const fetchVop = async () => {
        setVopLoading(true);
        try {
          const response = await axios.get(`${API}/legal/vop`);
          setVopData(response.data);
        } catch (error) {
          toast.error('Nepodařilo se načíst obchodní podmínky');
        } finally {
          setVopLoading(false);
        }
      };
      fetchVop();
    }
  }, [activeSection]);

  const fetchPlanStatus = async () => {
    try {
      const response = await axios.get(`${API}/plan/status`);
      setPlanData(response.data);
      setIsPro(response.data.is_pro);
    } catch (error) {
      console.error('Error fetching plan status:', error);
    }
  };

  const fetchPaymentSettings = async () => {
    try {
      const res = await axios.get(`${API}/events/settings/payment`);
      setPaymentSettings(prev => ({ ...prev, ...res.data }));
    } catch { /* events module might not be enabled */ }
  };

  const fetchEventsFlag = async () => {
    try {
      const res = await axios.get(`${API}/events/check-access`);
      setEventsEnabled(res.data?.enabled || false);
    } catch { setEventsEnabled(false); }
  };

  const savePaymentSettings = async (confirmDisable = false) => {
    try {
      const payload = {
        ...paymentSettings,
        allowed_methods: paymentSettings.allowed_methods || [],
        confirm_disable: confirmDisable,
      };
      const res = await axios.put(`${API}/events/settings/payment`, payload);
      setPaymentSettings(prev => ({
        ...prev,
        ...res.data,
        gateway_api_key: '',
        gateway_secret: '',
      }));
      setDisableConfirm(null);
      toast.success('Platební nastavení uloženo');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409 && detail?.code === 'needs_confirm') {
        setDisableConfirm(detail);
        return;
      }
      if (err.response?.status === 409 && detail?.code === 'would_empty') {
        setDisableConfirm(null);
        toast.error(`${detail.message} Dotčené akce: ${(detail.events || []).map(e => e.name).join(', ')}`);
        return;
      }
      toast.error(typeof detail === 'string' ? detail : 'Chyba při ukládání platebního nastavení');
    }
  };

  const handleUpgradePlan = async () => {
    setUpgrading(true);
    try {
      await axios.put(`${API}/plan/upgrade`, { confirm: true });
      toast.success('PRO verze byla aktivována!');
      setShowUpgradeModal(false);
      fetchPlanStatus();
      fetchProSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se aktivovat PRO verzi');
    } finally {
      setUpgrading(false);
    }
  };

  const handleDowngradePlan = async () => {
    if (!window.confirm('Opravdu chcete přejít na FREE verzi? Ztratíte přístup k PRO funkcím.')) return;
    try {
      await axios.put(`${API}/plan/downgrade`, { confirm: true });
      toast.success('Plán byl změněn na FREE');
      fetchPlanStatus();
      fetchProSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se změnit plán');
    }
  };

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

  const fetchProSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings/pro`);
      if (response.data) {
        setIsPro(response.data.is_pro);
        setProSettings(prev => ({
          ...prev,
          csv_export_enabled: response.data.csv_export_enabled ?? true,
          mass_propagation_enabled: response.data.mass_propagation_enabled ?? true,
          email_subject_template: response.data.email_subject_template || prev.email_subject_template,
          email_body_template: response.data.email_body_template || prev.email_body_template,
        }));
      }
    } catch (error) {
      console.error('Error fetching PRO settings');
    }
  };

  const handleSaveProSettings = async () => {
    setLoading(true);
    try {
      await axios.put(`${API}/settings/pro`, proSettings);
      toast.success('PRO nastavení bylo uloženo');
    } catch (error) {
      toast.error('Nepodařilo se uložit nastavení');
    } finally {
      setLoading(false);
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

  const handleLogoUpload = async (file) => {
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml', 'image/webp', 'image/gif'];
    const fileName = (file?.name || '').toLowerCase();
    const allowedExt = ['.png', '.jpg', '.jpeg', '.jpe', '.svg', '.webp', '.gif'];
    const extOk = allowedExt.some(ext => fileName.endsWith(ext));
    if (!allowedTypes.includes(file.type) && !extOk) {
      toast.error('Nepodporovaný formát. Povoleno: PNG, JPG/JPEG, SVG, WebP, GIF');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Soubor je příliš velký (max 2 MB)');
      return;
    }
    setLogoUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await axios.post(`${API}/settings/logo/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setInstitutionData(prev => ({ ...prev, logo_url: res.data.logo_url }));
      toast.success('Logo úspěšně nahráno');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nahrání loga selhalo');
    } finally {
      setLogoUploading(false);
    }
  };

  const canEditNotif = ['admin', 'spravce'].includes(user?.role);

  const loadNotifications = async () => {
    try {
      const [nres, tres] = await Promise.all([
        axios.get(`${API}/settings/notifications`),
        axios.get(`${API}/team`).catch(() => ({ data: [] })),
      ]);
      setNotifications(nres.data);
      const eligible = (tres.data || []).filter(
        (m) => ['admin', 'spravce', 'edukator'].includes(m.role) && m.status === 'active'
      );
      setNotifTeam(eligible);
    } catch (error) {
      toast.error('Nepodařilo se načíst nastavení notifikací');
      setNotifications({ customer: {}, admin: { recipient_user_ids: [] } });
    }
  };

  useEffect(() => {
    if (activeSection === 'notifications' && notifications === null) {
      loadNotifications();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSection]);

  const setCustomerNotif = (key, value) =>
    setNotifications((n) => ({ ...n, customer: { ...n.customer, [key]: value } }));
  const setAdminNotif = (key, value) =>
    setNotifications((n) => ({ ...n, admin: { ...n.admin, [key]: value } }));
  const toggleRecipient = (uid) =>
    setNotifications((n) => {
      const cur = n.admin?.recipient_user_ids || [];
      const next = cur.includes(uid) ? cur.filter((x) => x !== uid) : [...cur, uid];
      return { ...n, admin: { ...n.admin, recipient_user_ids: next } };
    });

  const handleSaveNotifications = async () => {
    if (!canEditNotif) {
      toast.error('Nastavení mohou měnit pouze správci a administrátoři');
      return;
    }
    setLoading(true);
    try {
      const res = await axios.put(`${API}/settings/notifications`, {
        customer: notifications.customer,
        admin: notifications.admin,
      });
      setNotifications(res.data);
      toast.success('Nastavení notifikací bylo uloženo');
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Nepodařilo se uložit nastavení');
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
  // Check events flag on mount for menu visibility
  useEffect(() => {
    const checkFlag = async () => {
      try {
        const res = await axios.get(`${API}/events/check-access`);
        setEventsEnabled(res.data?.enabled || false);
      } catch { setEventsEnabled(false); }
    };
    checkFlag();
  }, []);

  const renderMainMenu = () => {
    const visibleMenu = SETTINGS_MENU.filter(item => {
      if (item.id === 'payment') return eventsEnabled;
      return true;
    });

    // Mobile-only "Rychlý přístup" — items hidden from mobile bottom nav.
    // The bottom nav only shows the first 4 flat nav items + "Více" (which leads
    // here). All remaining admin pages are surfaced here on mobile only.
    const role = user?.role || 'viewer';
    const isPlatformOwner = user?.email === 'demo@budezivo.cz' || user?.email === 'admin@budezivo.cz';
    const allMobileQuickItems = [
      { path: '/admin', icon: LayoutDashboard, label: 'Přehled', roles: ['admin','spravce','edukator','lektor','pokladni','staff','viewer'] },
      { path: '/admin/programs', icon: Calendar, label: 'Programy', roles: ['admin','spravce','edukator','staff','viewer'] },
      { path: '/admin/bookings', icon: BookOpen, label: 'Rezervace', roles: ['admin','spravce','edukator','lektor','pokladni','staff','viewer'] },
      { path: '/admin/events', icon: CalendarDays, label: 'Akce', roles: ['admin','spravce','edukator','staff'], requiresEvents: true },
      { path: '/admin/mailings', icon: Mail, label: 'Propagace', roles: ['admin','spravce','edukator','staff'] },
      { path: '/admin/schools', icon: School, label: 'Školy', roles: ['admin','spravce','edukator','staff'] },
      { path: '/admin/feedback', icon: MessageSquare, label: 'Zpětná vazba', roles: ['admin','spravce','edukator','staff'] },
      { path: '/admin/lecturer-profile', icon: GraduationCap, label: 'Lektorský profil', roles: ['admin','spravce','edukator','lektor','pokladni','staff','viewer'] },
      { path: '/admin/statistics', icon: BarChart3, label: 'Statistiky', roles: ['admin','spravce','edukator','staff'] },
      { path: '/admin/superadmin', icon: Shield, label: 'Superadmin', roles: ['admin','spravce'], superadminOnly: true },
    ];
    const mobileQuickItems = allMobileQuickItems.filter(it => {
      if (it.requiresEvents && !eventsEnabled) return false;
      if (it.superadminOnly && !isPlatformOwner) return false;
      return it.roles.includes(role);
    });

    return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/admin')} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Nastavení</h1>
      </div>

      {/* Mobile-only quick access (matches "Více" entry from bottom nav) */}
      <div className="md:hidden space-y-2" data-testid="settings-mobile-quick-access">
        <h2 className="text-xs font-semibold tracking-[0.18em] uppercase text-slate-500 px-1 pt-1">
          Rychlý přístup
        </h2>
        <div className="grid grid-cols-3 gap-2">
          {mobileQuickItems.map((it) => {
            const Icon = it.icon;
            return (
              <button
                key={it.path}
                onClick={() => navigate(it.path)}
                data-testid={`mobile-quick-${it.path.replace(/\//g, '-')}`}
                className="flex flex-col items-center justify-center gap-1.5 py-3 px-2 bg-white border border-gray-200 rounded-xl hover:border-[#5a7aae] hover:shadow-sm transition-all text-center"
              >
                <Icon className="w-5 h-5 text-[#5a7aae]" />
                <span className="text-[11px] font-medium text-slate-700 leading-tight">{it.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-3">
        {SETTINGS_GROUPS.map((group) => {
          const itemsInGroup = visibleMenu.filter(it => (it.group || 'general') === group.key);
          if (itemsInGroup.length === 0) return null;
          return (
            <div key={group.key} className="space-y-2" data-testid={`settings-group-${group.key}`}>
              <h2 className="text-xs font-semibold tracking-[0.18em] uppercase text-slate-500 px-1 pt-3">
                {group.label}
              </h2>
              {itemsInGroup.map((item) => {
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
            </div>
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

        {/* Smazat účet - méně výrazné */}
        <div className="pt-6 mt-6 border-t border-gray-100">
          <button
            onClick={() => setActiveSection('delete-account')}
            className="text-sm text-gray-400 hover:text-red-500 transition-colors"
            data-testid="settings-delete-account"
          >
            Smazat účet
          </button>
        </div>
      </div>
    </div>
    );
  };

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
          <div
            className="mt-2 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer relative"
            data-testid="logo-upload-dropzone"
            onClick={() => document.getElementById('logo-file-input').click()}
            onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-blue-400', 'bg-blue-50'); }}
            onDragLeave={(e) => { e.currentTarget.classList.remove('border-blue-400', 'bg-blue-50'); }}
            onDrop={async (e) => {
              e.preventDefault();
              e.currentTarget.classList.remove('border-blue-400', 'bg-blue-50');
              const file = e.dataTransfer.files[0];
              if (file) await handleLogoUpload(file);
            }}
          >
            {institutionData.logo_url ? (
              <div className="space-y-2">
                <img
                  src={resolveAssetUrl(institutionData.logo_url)}
                  alt="Logo"
                  className="max-h-16 mx-auto object-contain"
                  data-testid="logo-preview"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
                <p className="text-xs text-gray-400">Klikněte nebo přetáhněte nové logo pro nahrazení</p>
              </div>
            ) : (
              <>
                <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Klikněte nebo přetáhněte soubor s logem</p>
                <p className="text-xs text-gray-400">PNG, JPG, SVG, WebP — max. 2 MB</p>
              </>
            )}
            {logoUploading && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-lg">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                <span className="ml-2 text-sm text-blue-600">Nahrávání...</span>
              </div>
            )}
          </div>
          <input
            id="logo-file-input"
            type="file"
            accept="image/png,image/jpeg,image/svg+xml,image/webp"
            className="hidden"
            data-testid="logo-file-input"
            onChange={async (e) => {
              const file = e.target.files[0];
              if (file) await handleLogoUpload(file);
              e.target.value = '';
            }}
          />
          {institutionData.logo_url && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 text-red-500 hover:text-red-700"
              data-testid="logo-remove-btn"
              onClick={() => setInstitutionData({ ...institutionData, logo_url: '' })}
            >
              <Trash2 className="w-4 h-4 mr-1" /> Odstranit logo
            </Button>
          )}

          {/* URL option */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-gray-400">nebo</span>
              <span className="flex-1 h-px bg-gray-100" />
            </div>
            <Label className="text-gray-600 text-xs">Zadat URL loga</Label>
            <div className="flex gap-2 mt-1">
              <Input
                value={institutionData.logo_url?.startsWith('/api') ? '' : (institutionData.logo_url || '')}
                onChange={(e) => setInstitutionData({ ...institutionData, logo_url: e.target.value })}
                placeholder="https://example.com/logo.png"
                className="flex-1 text-sm"
                data-testid="logo-url-input"
              />
            </div>
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
  const renderNotificationSettings = () => {
    if (notifications === null) {
      return (
        <div className="space-y-6">
          <div className="flex items-center gap-4 mb-6">
            <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-semibold text-slate-900">Notifikace a upozornění</h1>
          </div>
          <div className="flex items-center justify-center py-16 text-gray-400" data-testid="notifications-loading">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Načítání nastavení…
          </div>
        </div>
      );
    }

    const cust = notifications.customer || {};
    const adm = notifications.admin || {};
    const recipients = adm.recipient_user_ids || [];
    const disabled = !canEditNotif;

    const Row = ({ meta, checked, onChange, testid }) => (
      <div className={`flex items-start justify-between gap-3 ${disabled ? 'opacity-70' : ''}`}>
        <div>
          <p className="font-medium text-slate-900">{meta.title}</p>
          <p className="text-sm text-gray-500">{meta.desc}</p>
        </div>
        <Switch checked={!!checked} onCheckedChange={onChange} disabled={disabled} data-testid={testid} />
      </div>
    );

    return (
      <div className="space-y-6" data-testid="notifications-section">
        <div className="flex items-center gap-4 mb-2">
          <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold text-slate-900">Notifikace a upozornění</h1>
        </div>
        {!canEditNotif && (
          <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2" data-testid="notif-readonly-notice">
            Nastavení mohou měnit pouze administrátoři a správci. Zobrazení je pouze pro čtení.
          </div>
        )}

        {/* A — E-maily rezervujícím a účastníkům */}
        <Card className="p-4 space-y-4">
          <div>
            <h2 className="font-semibold text-slate-900">E-maily rezervujícím a účastníkům</h2>
            <p className="text-sm text-gray-500">Zprávy odeslané objednávajícím a účastníkům akcí.</p>
          </div>
          {CUSTOMER_NOTIF_META.map((m) => (
            <Row key={m.key} meta={m} checked={cust[m.key]} onChange={(v) => setCustomerNotif(m.key, v)} testid={`notif-customer-${m.key}`} />
          ))}
        </Card>

        {/* B — Provozní upozornění instituci */}
        <Card className="p-4 space-y-4">
          <div>
            <h2 className="font-semibold text-slate-900">Provozní upozornění instituci</h2>
            <p className="text-sm text-gray-500">Interní upozornění pro vybrané členy týmu.</p>
          </div>
          {ADMIN_NOTIF_META.map((m) => (
            <Row key={m.key} meta={m} checked={adm[m.key]} onChange={(v) => setAdminNotif(m.key, v)} testid={`notif-admin-${m.key}`} />
          ))}

          {/* Recipients */}
          <div className="pt-3 border-t">
            <p className="font-medium text-slate-900 mb-1">Příjemci provozních upozornění</p>
            <p className="text-sm text-gray-500 mb-3">Vyberte členy týmu (admin, správce, edukátor). Bez výběru se použije kontaktní e-mail instituce.</p>
            <div className="space-y-2" data-testid="notif-recipients">
              {notifTeam.length === 0 && <p className="text-sm text-gray-400">Žádní vhodní členové týmu.</p>}
              {notifTeam.map((m) => (
                <label key={m.id} className={`flex items-center gap-2.5 text-sm ${disabled ? 'opacity-70' : 'cursor-pointer'}`}>
                  <Checkbox
                    checked={recipients.includes(m.id)}
                    onCheckedChange={() => toggleRecipient(m.id)}
                    disabled={disabled}
                    data-testid={`notif-recipient-${m.id}`}
                  />
                  <span className="text-slate-800">{m.name || m.email}</span>
                  <span className="text-xs text-gray-400">{m.email} · {m.role}</span>
                </label>
              ))}
            </div>
          </div>
        </Card>

        {/* C — Připravované přehledy */}
        <Card className="p-4 space-y-4">
          <h2 className="font-semibold text-slate-900">Připravované přehledy</h2>
          {UPCOMING_NOTIF_META.map((m, i) => (
            <div key={i} className="flex items-start justify-between gap-3 opacity-60">
              <div>
                <p className="font-medium text-slate-900">{m.title}</p>
                <p className="text-sm text-gray-500">{m.desc}</p>
              </div>
              <span className="px-2 py-0.5 text-xs font-medium bg-slate-200 text-slate-600 rounded whitespace-nowrap" data-testid={`notif-upcoming-${i}`}>
                Připravujeme
              </span>
            </div>
          ))}
        </Card>

        {canEditNotif && (
          <Button
            onClick={handleSaveNotifications}
            disabled={loading}
            className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
            data-testid="save-notifications"
          >
            {loading ? 'Ukládání...' : 'Uložit'}
          </Button>
        )}
      </div>
    );
  };

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

  // Render PRO funkce
  const renderProSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">PRO funkce</h1>
      </div>

      {/* Plan Status Card */}
      <Card className="p-6 border-2 border-[#2B3E50]/20" data-testid="plan-status-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-xl ${planData.is_pro ? 'bg-gradient-to-br from-yellow-400 to-amber-500' : 'bg-gray-100'}`}>
              <Crown className={`w-6 h-6 ${planData.is_pro ? 'text-white' : 'text-gray-400'}`} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Nastavení tarifu</h2>
              <p className="text-sm text-gray-500">Váš aktuální plán a dostupné funkce</p>
            </div>
          </div>
          <span className={`px-4 py-2 rounded-full text-sm font-bold ${
            planData.is_pro 
              ? 'bg-gradient-to-r from-yellow-400 to-amber-500 text-white' 
              : 'bg-gray-100 text-gray-600'
          }`} data-testid="plan-badge">
            {planData.plan_label || (planData.is_pro ? 'PRO' : 'FREE')}
          </span>
        </div>
        
        {planData.plan_updated_at && (
          <p className="text-xs text-gray-400 mb-4">
            Aktivováno: {new Date(planData.plan_updated_at).toLocaleDateString('cs-CZ')}
          </p>
        )}

        {!planData.is_pro ? (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-800 font-medium">Odemkněte plný potenciál</p>
              <p className="text-blue-700 text-sm mt-1">
                Vyšší plány zahrnují CSV export, hromadné emaily, pokročilé statistiky a neomezený počet programů.
              </p>
            </div>
            <Button
              onClick={() => window.location.href = '/admin/plan'}
              className="w-full bg-gradient-to-r from-yellow-400 to-amber-500 hover:from-yellow-500 hover:to-amber-600 text-white h-12 font-semibold"
              data-testid="upgrade-button"
            >
              <Crown className="w-5 h-5 mr-2" />
              Zobrazit plány
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">{planData.plan === 'pro_plus' ? 'PRO+ verze je aktivní' : 'PRO verze je aktivní'}</span>
            </div>
            <p className="text-sm text-gray-500">
              Máte přístup ke všem funkcím vašeho plánu.
              {planData.plan_status === 'pending' && ' (Čeká na potvrzení platby)'}
            </p>
            <Button variant="outline" size="sm" onClick={() => window.location.href = '/admin/plan'}>
              Spravovat plán
            </Button>
          </div>
        )}
      </Card>

      {!isPro && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800 font-medium">Tyto funkce jsou dostupné pouze v PRO verzi</p>
          <p className="text-yellow-700 text-sm mt-1">Aktivujte PRO plán výše pro přístup k PRO funkcím.</p>
        </div>
      )}

      {/* Funkce */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Dostupné funkce</h2>
        
        <div className="flex items-start gap-3">
          <Switch
            checked={proSettings.csv_export_enabled}
            onCheckedChange={(checked) => setProSettings({ ...proSettings, csv_export_enabled: checked })}
            disabled={!isPro}
            data-testid="pro-csv-export"
          />
          <div>
            <p className="font-medium text-slate-900">CSV export škol</p>
            <p className="text-sm text-gray-500">Umožní export seznamu škol do CSV souboru.</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Switch
            checked={proSettings.mass_propagation_enabled}
            onCheckedChange={(checked) => setProSettings({ ...proSettings, mass_propagation_enabled: checked })}
            disabled={!isPro}
            data-testid="pro-propagation"
          />
          <div>
            <p className="font-medium text-slate-900">Hromadná propagace programů</p>
            <p className="text-sm text-gray-500">Rozesílání informací o nových programech školám.</p>
          </div>
        </div>
      </Card>

      {/* Email šablona */}
      <Card className="p-4 space-y-4">
        <h2 className="font-semibold text-slate-900">Email šablona propagace</h2>
        <p className="text-sm text-gray-500">Můžete použít proměnné: {'{program_name}'}, {'{program_description}'}, {'{reservation_url}'}, {'{institution_name}'}</p>
        
        <div>
          <Label className="text-gray-600 text-sm">Předmět emailu</Label>
          <Input
            value={proSettings.email_subject_template}
            onChange={(e) => setProSettings({ ...proSettings, email_subject_template: e.target.value })}
            disabled={!isPro}
            className="mt-1"
            data-testid="pro-email-subject"
          />
        </div>

        <div>
          <Label className="text-gray-600 text-sm">Tělo emailu</Label>
          <textarea
            value={proSettings.email_body_template}
            onChange={(e) => setProSettings({ ...proSettings, email_body_template: e.target.value })}
            disabled={!isPro}
            rows={8}
            className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-slate-800 disabled:bg-gray-100"
            data-testid="pro-email-body"
          />
        </div>
      </Card>

      {/* Save button */}
      <Button
        onClick={handleSaveProSettings}
        disabled={loading || !isPro}
        className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
        data-testid="save-pro"
      >
        {loading ? 'Ukládání...' : 'Uložit'}
      </Button>

      {/* Upgrade Modal */}
      {/* Upgrade modal → redirect to plans page */}
      <Dialog open={showUpgradeModal} onOpenChange={setShowUpgradeModal}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Crown className="w-5 h-5 text-amber-500" />
              Vyšší plán potřeba
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600 py-2">
            Tato funkce vyžaduje vyšší plán. Podívejte se na dostupné plány a vyberte ten správný.
          </p>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowUpgradeModal(false)}>Zavřít</Button>
            <Button onClick={() => { setShowUpgradeModal(false); window.location.href = '/admin/plan'; }}
              className="bg-gradient-to-r from-yellow-400 to-amber-500 text-white" data-testid="confirm-upgrade-button">
              <Crown className="w-4 h-4 mr-1" /> Zobrazit plány
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );

  // Render GDPR a export dat
  const renderGdprSettings = () => {
    const handleExportData = async () => {
      setExportLoading(true);
      try {
        const response = await axios.get(`${API}/gdpr/export`, { responseType: 'blob' });
        const blob = new Blob([response.data], { type: 'application/zip' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `budezivo_gdpr_export_${new Date().toISOString().slice(0, 10)}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        toast.success('GDPR export stažen (obsahuje JSON i PDF)');
      } catch (error) {
        toast.error('Chyba při exportu dat');
      } finally {
        setExportLoading(false);
      }
    };

    const handleBulkExportZip = async () => {
      setBulkExportLoading(true);
      try {
        const response = await axios.get(`${API}/exports/download-bundle`, { responseType: 'blob' });
        const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }));
        const link = document.createElement('a');
        link.href = blobUrl;
        const cd = response.headers?.['content-disposition'] || '';
        const match = cd.match(/filename="([^"]+)"/);
        link.setAttribute('download', match?.[1] || `budezivo_export_${Date.now()}.zip`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(blobUrl);
        toast.success('ZIP s exporty byl stažen');
      } catch (error) {
        const msg = error.response?.data?.detail || 'Chyba při hromadném exportu';
        toast.error(typeof msg === 'string' ? msg : 'Chyba při hromadném exportu');
      } finally {
        setBulkExportLoading(false);
      }
    };

    const handleAnonymize = async () => {
      if (anonymizeConfirm !== 'SMAZAT') {
        toast.error('Pro anonymizaci napište SMAZAT');
        return;
      }
      setAnonymizeLoading(true);
      try {
        await axios.post(`${API}/gdpr/anonymize`, { confirmation: 'SMAZAT' });
        toast.success('Vaše osobní údaje byly anonymizovány');
        setAnonymizeDialog(false);
        logout();
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Chyba při anonymizaci');
      } finally {
        setAnonymizeLoading(false);
      }
    };

    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold text-slate-900">GDPR a export dat</h1>
        </div>

        {/* Export osobních dat (GDPR čl. 20) */}
        <Card className="p-4 space-y-4">
          <h2 className="font-semibold text-slate-900">Export osobních dat</h2>
          <p className="text-sm text-gray-500">
            Stáhněte si všechna svá osobní data jako ZIP obsahující <strong>JSON</strong>
            {' '}(strojově čitelný formát pro přenositelnost) a <strong>PDF</strong>
            {' '}(lidsky čitelný přehled). Zahrnuje údaje o uživateli, instituci, rezervacích a školách.
          </p>
          <p className="text-xs text-gray-400">
            Na základě článku 20 GDPR — právo na přenositelnost údajů (autoritativní formát je JSON).
          </p>
          <Button
            variant="outline"
            className="w-full border-gray-300"
            onClick={handleExportData}
            disabled={exportLoading}
            data-testid="export-data-button"
          >
            {exportLoading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Exportuji...</>
            ) : (
              'Exportovat moje data (ZIP — JSON + PDF)'
            )}
          </Button>
        </Card>

        {/* Hromadný export všech dat inštituce (PRO) */}
        <Card className="p-4 space-y-4" data-testid="bulk-export-card">
          <h2 className="font-semibold text-slate-900">Hromadný export (ZIP)</h2>
          <p className="text-sm text-gray-500">
            Stáhněte jedním kliknutím kompletní balík všech generovaných souborů za vaši instituci —
            školy a kontakty (CSV), zpětnou vazbu, statistiky, GDPR data (JSON), iCal feedy a
            archive reporty programů.
          </p>
          <p className="text-xs text-gray-400">
            Dostupné pro plány PRO a PRO+. Export obsahuje citlivá data — přístup mají pouze
            administrátoři instituce.
          </p>
          <Button
            variant="outline"
            className="w-full border-gray-300"
            onClick={handleBulkExportZip}
            disabled={bulkExportLoading}
            data-testid="bulk-export-button"
          >
            {bulkExportLoading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Připravuji ZIP...</>
            ) : (
              'Stáhnout všechno jako ZIP'
            )}
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
              <p className="font-medium text-slate-900">Automatická anonymizace</p>
              <p className="text-sm text-gray-500">Automaticky anonymizovat osobní údaje v rezervacích po skončení doby uchování.</p>
            </div>
          </div>
        </Card>

        {/* Anonymizace účtu */}
        <Card className="p-4 space-y-4 border-red-200">
          <h2 className="font-semibold text-red-700">Anonymizace osobních údajů</h2>
          <p className="text-sm text-gray-500">
            Tato akce odstraní všechny vaše osobní údaje (jméno, email) a nahradí je anonymní hodnotou.
            Záznamy o rezervacích zůstanou zachovány pro auditní účely. Tato akce je nevratná.
          </p>
          <p className="text-xs text-gray-400">
            Na základě článku 17 GDPR — právo na výmaz ("právo být zapomenut").
          </p>
          <Button
            variant="outline"
            className="w-full border-red-300 text-red-600 hover:bg-red-50"
            onClick={() => setAnonymizeDialog(true)}
            data-testid="anonymize-account-button"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Anonymizovat mé údaje
          </Button>
        </Card>

        {/* Save button for retention settings */}
        <Button
          onClick={handleSaveGdpr}
          disabled={loading}
          className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a] h-12"
          data-testid="save-gdpr"
        >
          {loading ? 'Ukládání...' : 'Uložit nastavení'}
        </Button>

        {/* Anonymize confirmation dialog */}
        <Dialog open={anonymizeDialog} onOpenChange={setAnonymizeDialog}>
          <DialogContent aria-describedby="anonymize-desc">
            <DialogHeader>
              <DialogTitle className="text-red-700">Anonymizace osobních údajů</DialogTitle>
            </DialogHeader>
            <p id="anonymize-desc" className="text-sm text-gray-600 mb-4">
              Tato akce je nevratná. Pro potvrzení napište <strong>SMAZAT</strong>.
            </p>
            <Input
              value={anonymizeConfirm}
              onChange={(e) => setAnonymizeConfirm(e.target.value)}
              placeholder="Napište SMAZAT"
              className="border-red-200"
              data-testid="anonymize-confirm-input"
            />
            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={() => setAnonymizeDialog(false)}>Zrušit</Button>
              <Button
                onClick={handleAnonymize}
                disabled={anonymizeConfirm !== 'SMAZAT' || anonymizeLoading}
                className="bg-red-600 hover:bg-red-700 text-white"
                data-testid="anonymize-confirm-button"
              >
                {anonymizeLoading ? 'Anonymizuji...' : 'Potvrdit anonymizaci'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  };

  // Handle account deletion
  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== 'DELETE') {
      toast.error('Pro smazání účtu napište DELETE');
      return;
    }

    setDeleteLoading(true);
    try {
      await axios.delete(`${API}/account/delete`, {
        data: { confirmation: 'DELETE' }
      });
      toast.success('Účet byl úspěšně deaktivován');
      logout();
      navigate('/login');
    } catch (error) {
      const message = error.response?.data?.detail || 'Nepodařilo se smazat účet';
      toast.error(message);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Render Delete Account section
  const renderDeleteAccountSection = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Smazání účtu</h1>
      </div>

      <Card className="p-6 border-red-100 bg-red-50/30">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-red-100 rounded-full">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-red-800 mb-2">Opravdu chcete smazat svůj účet?</h2>
            <p className="text-sm text-red-700 mb-4">
              Tato akce je nevratná. Smazáním účtu:
            </p>
            <ul className="text-sm text-red-700 list-disc list-inside space-y-1 mb-4">
              <li>Ztratíte přístup ke svému účtu</li>
              <li>Vaše osobní údaje budou deaktivovány</li>
              <li>Nebudete se moci přihlásit</li>
            </ul>
            <p className="text-xs text-gray-500 mb-6">
              Poznámka: Některé údaje mohou být uchovány pro účely auditních záznamů a právních požadavků.
            </p>

            <div className="space-y-4">
              <div>
                <Label className="text-sm text-gray-600">
                  Pro potvrzení napište <span className="font-mono font-bold">DELETE</span>
                </Label>
                <Input
                  value={deleteConfirmation}
                  onChange={(e) => setDeleteConfirmation(e.target.value)}
                  placeholder="DELETE"
                  className="mt-2 max-w-xs"
                  data-testid="delete-confirmation-input"
                />
              </div>

              <Button
                onClick={handleDeleteAccount}
                disabled={deleteLoading || deleteConfirmation !== 'DELETE'}
                variant="destructive"
                className="bg-red-600 hover:bg-red-700 disabled:bg-gray-300"
                data-testid="confirm-delete-account"
              >
                {deleteLoading ? 'Mazání...' : 'Trvale smazat účet'}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <Button
        variant="outline"
        onClick={() => setActiveSection(null)}
        className="w-full"
      >
        Zrušit a vrátit se zpět
      </Button>
    </div>
  );

  // Render based on active section
  // Render VOP (Obchodní podmínky)
  const renderVopSection = () => {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold text-slate-900">Obchodní podmínky (VOP)</h1>
        </div>

        {vopLoading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-slate-400" />
          </div>
        ) : vopData ? (
          <Card className="p-6 space-y-6" data-testid="vop-admin-section">
            <h2 className="text-lg font-bold text-slate-900">{vopData.title}</h2>
            <p className="text-xs text-gray-400">Verze: {vopData.version}</p>
            <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
              {vopData.sections?.map((section) => (
                <div key={section.number} className="space-y-2">
                  <h3 className="text-sm font-semibold text-slate-800">
                    {section.number}. {section.title}
                  </h3>
                  {section.content.map((paragraph, idx) => (
                    <p key={idx} className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
                      {paragraph}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          </Card>
        ) : (
          <Card className="p-6 text-center text-gray-500">
            Obchodní podmínky nebyly nalezeny.
          </Card>
        )}
      </div>
    );
  };

  const renderContent = () => {
    switch (activeSection) {
      case 'institution':
        return renderInstitutionSettings();
      case 'notifications':
        return renderNotificationSettings();
      case 'locale':
        return renderLocaleSettings();
      case 'pro':
        return renderProSettings();
      case 'gdpr':
        return renderGdprSettings();
      case 'vop':
        return renderVopSection();
      case 'payment':
        return renderPaymentSettings();
      case 'password':
        return renderPasswordSettings();
      case 'delete-account':
        return renderDeleteAccountSection();
      default:
        return renderMainMenu();
    }
  };

  const handleChangePassword = async (e) => {
    e?.preventDefault();
    if (!pwdCurrent || !pwdNew || !pwdConfirm) {
      toast.error('Vyplňte všechna pole');
      return;
    }
    if (pwdNew !== pwdConfirm) {
      toast.error('Nové heslo a jeho potvrzení se neshodují');
      return;
    }
    if (pwdNew.length < 8 || !/[A-Z]/.test(pwdNew) || !/[a-z]/.test(pwdNew) || !/[0-9]/.test(pwdNew)) {
      toast.error('Heslo musí mít alespoň 8 znaků, velké i malé písmeno a číslici');
      return;
    }
    setChangingPwd(true);
    try {
      await axios.post(`${API}/auth/change-password`, {
        current_password: pwdCurrent,
        new_password: pwdNew,
      }, { withCredentials: true });
      toast.success('Heslo bylo úspěšně změněno');
      setPwdCurrent('');
      setPwdNew('');
      setPwdConfirm('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Změna hesla selhala');
    } finally {
      setChangingPwd(false);
    }
  };

  const renderPasswordSettings = () => (
    <div className="space-y-6" data-testid="settings-password-section">
      <div className="flex items-center gap-4 mb-4">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg" data-testid="password-back-button">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Změna hesla</h2>
          <p className="text-sm text-gray-500">Změňte si přihlašovací heslo k účtu</p>
        </div>
      </div>

      <Card className="p-5 space-y-4">
        <form onSubmit={handleChangePassword} className="space-y-3 max-w-md">
          <div>
            <Label htmlFor="pwd-current">Současné heslo</Label>
            <Input
              id="pwd-current"
              type="password"
              autoComplete="current-password"
              data-testid="password-current-input"
              value={pwdCurrent}
              onChange={(e) => setPwdCurrent(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div>
            <Label htmlFor="pwd-new">Nové heslo</Label>
            <Input
              id="pwd-new"
              type="password"
              autoComplete="new-password"
              data-testid="password-new-input"
              value={pwdNew}
              onChange={(e) => setPwdNew(e.target.value)}
              placeholder="••••••••"
            />
            <p className="text-xs text-gray-500 mt-1">Min. 8 znaků, velké i malé písmeno a číslice.</p>
          </div>
          <div>
            <Label htmlFor="pwd-confirm">Potvrzení nového hesla</Label>
            <Input
              id="pwd-confirm"
              type="password"
              autoComplete="new-password"
              data-testid="password-confirm-input"
              value={pwdConfirm}
              onChange={(e) => setPwdConfirm(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <Button
            type="submit"
            disabled={changingPwd}
            className="bg-slate-800 hover:bg-slate-700 text-white"
            data-testid="change-password-button"
          >
            {changingPwd ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Měním heslo…</>
            ) : (
              <><Lock className="w-4 h-4 mr-2" /> Změnit heslo</>
            )}
          </Button>
        </form>
      </Card>
    </div>
  );

  const renderPaymentSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-4">
        <button onClick={() => setActiveSection(null)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Platební nastavení</h2>
          <p className="text-sm text-gray-500">Bankovní účet pro příjem plateb za události a akce</p>
        </div>
      </div>

      {!eventsEnabled ? (
        <Card className="p-6 text-center">
          <Lock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <h3 className="font-semibold text-slate-900 mb-1">Platební nastavení vyžaduje PRO balíček</h3>
          <p className="text-sm text-gray-500 mb-4">Platební funkce jsou součástí modulu Události, který je dostupný v nejvyšším PRO balíčku.</p>
          <Button onClick={() => setActiveSection('pro')} variant="outline">
            <Crown className="w-4 h-4 mr-2" /> Zobrazit PRO funkce
          </Button>
        </Card>
      ) : (
        <>
          <Card className="p-4 md:p-6 space-y-4">
            <h3 className="font-semibold text-slate-900">Bankovní účet</h3>
            <p className="text-sm text-gray-500">Údaje pro generování QR plateb a variabilních symbolů.</p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-gray-500 text-sm">Číslo účtu</Label>
                <Input
                  value={paymentSettings.account_number || ''}
                  onChange={e => setPaymentSettings(p => ({ ...p, account_number: e.target.value }))}
                  placeholder="1234567890"
                  className="mt-1"
                  data-testid="settings-payment-account"
                />
              </div>
              <div>
                <Label className="text-gray-500 text-sm">Kód banky</Label>
                <Input
                  value={paymentSettings.bank_code || ''}
                  onChange={e => setPaymentSettings(p => ({ ...p, bank_code: e.target.value }))}
                  placeholder="0100"
                  className="mt-1"
                  data-testid="settings-payment-bank-code"
                />
              </div>
            </div>

            <div>
              <Label className="text-gray-500 text-sm">Název účtu / příjemce</Label>
              <Input
                value={paymentSettings.account_name || ''}
                onChange={e => setPaymentSettings(p => ({ ...p, account_name: e.target.value }))}
                placeholder="Název vaší organizace"
                className="mt-1"
                data-testid="settings-payment-account-name"
              />
            </div>

            <div>
              <Label className="text-gray-500 text-sm">IBAN (volitelné)</Label>
              <Input
                value={paymentSettings.iban || ''}
                onChange={e => setPaymentSettings(p => ({ ...p, iban: e.target.value }))}
                placeholder="CZ6508000000192000145399"
                className="mt-1"
                data-testid="settings-payment-iban"
              />
            </div>
          </Card>

          <Card className="p-4 md:p-6 space-y-4">
            <h3 className="font-semibold text-slate-900">Povolené způsoby platby</h3>
            <p className="text-sm text-gray-500">Vyberte, které způsoby platby vaše instituce technicky podporuje. Tuto nabídku pak lze u jednotlivých akcí dále zúžit.</p>

            <label className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50" data-testid="method-qr">
              <input type="checkbox" className="mt-1 w-4 h-4" checked={(paymentSettings.allowed_methods || []).includes('qr')} onChange={() => togglePaymentMethod('qr')} data-testid="method-qr-checkbox" />
              <div>
                <p className="text-sm font-medium text-slate-800">QR platba / bankovní převod</p>
                <p className="text-xs text-gray-500">Vyžaduje vyplněné číslo účtu.</p>
                {!paymentSettings.account_number && (paymentSettings.allowed_methods || []).includes('qr') && (
                  <p className="text-xs text-amber-600 mt-0.5">Nejprve vyplňte číslo účtu výše.</p>
                )}
              </div>
            </label>

            <label className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50" data-testid="method-gateway">
              <input type="checkbox" className="mt-1 w-4 h-4" checked={(paymentSettings.allowed_methods || []).includes('gateway')} onChange={() => togglePaymentMethod('gateway')} data-testid="method-gateway-checkbox" />
              <div>
                <p className="text-sm font-medium text-slate-800">Platební brána Comgate</p>
                <p className="text-xs text-gray-500">Vyžaduje platnou konfiguraci brány (poskytovatel + přihlašovací údaje).</p>
              </div>
            </label>

            <label className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50" data-testid="method-cash">
              <input type="checkbox" className="mt-1 w-4 h-4" checked={(paymentSettings.allowed_methods || []).includes('cash')} onChange={() => togglePaymentMethod('cash')} data-testid="method-cash-checkbox" />
              <div>
                <p className="text-sm font-medium text-slate-800">Platba na místě</p>
                <p className="text-xs text-gray-500">Nevyžaduje bankovní účet ani platební bránu. Platbu později ručně potvrdí oprávněná osoba.</p>
              </div>
            </label>

            {(paymentSettings.allowed_methods || []).includes('gateway') && (
              <Card className="p-4 bg-blue-50 border-blue-200 space-y-3">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <p className="text-sm font-medium text-blue-800">Platební brána</p>
                  {/* Live status badge — server-authoritative via gateway_mode */}
                  {(() => {
                    const serverMode = (paymentSettings.gateway_mode || '').toUpperCase();
                    // Optimistic local override: while user types new keys before saving,
                    // reflect what the next save will produce.
                    const merchant = (paymentSettings.gateway_api_key || '').trim();
                    const secret = (paymentSettings.gateway_secret || '').trim();
                    const provider = (paymentSettings.provider || '').toLowerCase();
                    let mode = serverMode || 'MOCK';
                    if (provider === 'comgate' && merchant && secret) {
                      mode = merchant.toUpperCase().startsWith('TEST_') ? 'TEST' : 'LIVE';
                    }
                    const labels = {
                      LIVE: 'Produkce (LIVE)',
                      TEST: 'Sandbox (TEST)',
                      MOCK: 'Simulační (MOCK)',
                    };
                    const classes = {
                      LIVE: 'bg-green-100 text-green-800 border-green-300',
                      TEST: 'bg-blue-100 text-blue-800 border-blue-300',
                      MOCK: 'bg-amber-100 text-amber-800 border-amber-300',
                    };
                    const dots = {
                      LIVE: 'bg-green-600',
                      TEST: 'bg-blue-600',
                      MOCK: 'bg-amber-600',
                    };
                    const tips = {
                      LIVE: 'Reálné platby od zákazníků',
                      TEST: 'Sandbox Comgate — žádné reálné peníze',
                      MOCK: 'Žádné reálné volání brány — pouze interní simulátor',
                    };
                    return (
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-full border ${classes[mode]}`}
                        data-testid={`gateway-mode-badge-${mode.toLowerCase()}`}
                        title={tips[mode]}
                      >
                        <span className={`inline-block w-1.5 h-1.5 rounded-full ${dots[mode]}`} />
                        {labels[mode]}
                      </span>
                    );
                  })()}
                </div>
                <p className="text-xs text-blue-600">
                  {(() => {
                    const m = (paymentSettings.gateway_mode || 'MOCK').toUpperCase();
                    if (m === 'LIVE') return 'Brána je v produkčním režimu — všechny platby zákazníků jsou reálné a směřují přímo na váš Comgate účet.';
                    if (m === 'TEST') return 'Brána je v sandbox režimu Comgate (Merchant ID začíná TEST_) — žádné reálné peníze, ideální pro testování end-to-end flow.';
                    return 'Bez klíčů aplikace funguje v simulačním režimu (mock) — zákazník vidí testovací stránku a vy můžete odzkoušet celý flow. Po dodání reálných klíčů Comgate se brána automaticky přepne do produkčního / testovacího režimu.';
                  })()}
                </p>
                <div>
                  <Label className="text-gray-500 text-sm">Poskytovatel</Label>
                  <Select
                    value={paymentSettings.provider || 'none'}
                    onValueChange={v => setPaymentSettings(p => ({ ...p, provider: v === 'none' ? null : v }))}
                  >
                    <SelectTrigger className="mt-1" data-testid="gateway-provider"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Nevybráno</SelectItem>
                      <SelectItem value="comgate">Comgate</SelectItem>
                      <SelectItem value="gopay" disabled>GoPay (brzy)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {paymentSettings.provider === 'comgate' && (
                  <>
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <Label className="text-gray-500 text-sm">Comgate Merchant ID</Label>
                        {paymentSettings.gateway_api_key_masked && (
                          <span className="text-[11px] text-slate-500" data-testid="gateway-merchant-stored">
                            Uloženo: <code className="font-mono">{paymentSettings.gateway_api_key_masked}</code>
                          </span>
                        )}
                      </div>
                      <Input
                        value={paymentSettings.gateway_api_key || ''}
                        onChange={e => setPaymentSettings(p => ({ ...p, gateway_api_key: e.target.value }))}
                        placeholder={paymentSettings.gateway_api_key_masked
                          ? 'Ponechte prázdné pro zachování — vyplňte pouze pro změnu'
                          : 'např. 123456 (pro test začněte TEST_)'}
                        className="mt-1 font-mono"
                        data-testid="gateway-merchant"
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <Label className="text-gray-500 text-sm">Comgate Secret</Label>
                        {paymentSettings.gateway_secret_set && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700" data-testid="gateway-secret-stored">
                            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-600" />
                            Tajný klíč uložen
                          </span>
                        )}
                      </div>
                      <Input
                        type="password"
                        value={paymentSettings.gateway_secret || ''}
                        onChange={e => setPaymentSettings(p => ({ ...p, gateway_secret: e.target.value }))}
                        placeholder={paymentSettings.gateway_secret_set
                          ? 'Ponechte prázdné pro zachování — vyplňte pouze pro změnu'
                          : '••••••••'}
                        className="mt-1 font-mono"
                        data-testid="gateway-secret"
                      />
                    </div>
                    {(paymentSettings.gateway_api_key_masked || paymentSettings.gateway_secret_set) && (
                      <button
                        type="button"
                        className="text-xs text-red-600 hover:text-red-700 underline self-start"
                        data-testid="gateway-clear-keys"
                        onClick={() => {
                          if (window.confirm('Opravdu vymazat uložené Comgate klíče? Brána se vrátí do simulačního (MOCK) režimu.')) {
                            setPaymentSettings(p => ({ ...p, gateway_api_key: '__CLEAR__', gateway_secret: '__CLEAR__' }));
                          }
                        }}
                      >
                        Vymazat uložené klíče
                      </button>
                    )}
                    <p className="text-xs text-slate-500">
                      Tip: Merchant ID začínající <code className="font-mono">TEST_</code> přepne bránu do sandbox režimu Comgate.
                      Prázdná pole = simulační (mock) režim pro otestování přihlášek bez odeslání do banky.
                    </p>
                    {(() => {
                      // Compute frontend & API base URLs from the current window.
                      const apiBase = (process.env.REACT_APP_BACKEND_URL || window.location.origin).replace(/\/$/, '');
                      // FE host is the current admin's origin (where they actually use the app).
                      const frontendBase = window.location.origin.replace(/\/$/, '');
                      return <ComgatePortalUrls frontendBase={frontendBase} apiBase={apiBase} />;
                    })()}
                  </>
                )}
              </Card>
            )}
          </Card>

          <Button onClick={() => savePaymentSettings(false)} className="bg-slate-800 text-white w-full" data-testid="settings-save-payment">
            Uložit platební nastavení
          </Button>

          <Dialog open={!!disableConfirm} onOpenChange={(o) => { if (!o) setDisableConfirm(null); }}>
            <DialogContent className="sm:max-w-md" data-testid="disable-method-confirm-dialog">
              <DialogHeader>
                <DialogTitle>Potvrdit změnu platebních metod</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 py-1">
                <p className="text-sm text-gray-600">{disableConfirm?.message}</p>
                {(disableConfirm?.events || []).length > 0 && (
                  <div className="max-h-48 overflow-y-auto rounded-lg border divide-y">
                    {(disableConfirm?.events || []).map(ev => (
                      <div key={ev.id} className="px-3 py-2 text-sm" data-testid={`affected-event-${ev.id}`}>
                        <p className="font-medium text-slate-800">{ev.name}</p>
                        <p className="text-xs text-gray-500">Metody: {(ev.methods || []).join(', ')}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDisableConfirm(null)} data-testid="disable-method-cancel">Zrušit</Button>
                <Button className="bg-slate-800 text-white" onClick={() => savePaymentSettings(true)} data-testid="disable-method-confirm">Potvrdit a odebrat metodu</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </>
      )}
    </div>
  );

  return (
    <AdminLayout>
      {renderContent()}
    </AdminLayout>
  );
};
