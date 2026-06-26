import React, { useEffect, useState, useContext } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { UserCircle, Save, Loader2, GraduationCap, BookOpen, Users2, Info, KeyRound } from 'lucide-react';
import { API } from '../../config/api';

const AGE_GROUPS = [
  { value: 'ms_3_6', label: 'MŠ (3–6 let)' },
  { value: 'zs1_7_12', label: '1. stupeň ZŠ (7–12)' },
  { value: 'zs2_12_16', label: '2. stupeň ZŠ (12–16)' },
  { value: 'ss_15_19', label: 'SŠ / Gymnázium (15–19)' },
  { value: 'adults', label: 'Dospělí / veřejnost' },
];

export const MyProfilePage = ({ embedded = false }) => {
  const { user, refreshUser } = useContext(AuthContext);
  const [programs, setPrograms] = useState([]);
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Password change
  const [pwdCurrent, setPwdCurrent] = useState('');
  const [pwdNew, setPwdNew] = useState('');
  const [pwdConfirm, setPwdConfirm] = useState('');
  const [changingPwd, setChangingPwd] = useState(false);

  const [name, setName] = useState('');
  const [preferredAges, setPreferredAges] = useState([]);
  const [supportedIds, setSupportedIds] = useState([]);
  const [learningIds, setLearningIds] = useState([]);

  const isAdmin = user?.role === 'admin' || user?.role === 'spravce';

  const fetchData = async () => {
    try {
      const [teamRes, progRes] = await Promise.all([
        axios.get(`${API}/team`),
        axios.get(`${API}/programs`).catch(() => ({ data: [] })),
      ]);
      const myData = (Array.isArray(teamRes.data) ? teamRes.data : []).find(
        (m) => m.id === user?.id
      ) || null;
      setMe(myData);
      setName(myData?.name || user?.name || '');
      setPreferredAges(myData?.preferred_age_groups || []);
      setSupportedIds(myData?.supported_program_ids || []);
      setLearningIds(myData?.learning_program_ids || []);
      setPrograms(Array.isArray(progRes.data) ? progRes.data : []);
    } catch (err) {
      toast.error('Nepodařilo se načíst profil');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.id) fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const toggleAge = (v) => {
    setPreferredAges((prev) =>
      prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]
    );
  };

  const toggleSupported = (pid) => {
    setSupportedIds((prev) => {
      const next = prev.includes(pid) ? prev.filter((x) => x !== pid) : [...prev, pid];
      return next;
    });
    // mutual exclusion with learning
    setLearningIds((prev) => prev.filter((x) => x !== pid));
  };

  const toggleLearning = (pid) => {
    setLearningIds((prev) => {
      const next = prev.includes(pid) ? prev.filter((x) => x !== pid) : [...prev, pid];
      return next;
    });
    setSupportedIds((prev) => prev.filter((x) => x !== pid));
  };

  const handleSave = async (e) => {
    e?.preventDefault();
    if (!user?.id) return;
    setSaving(true);
    try {
      await axios.patch(`${API}/team/${user.id}/lecturer-profile`, {
        name: name?.trim() || undefined,
        preferred_age_groups: preferredAges,
        supported_program_ids: supportedIds,
        learning_program_ids: learningIds,
      });
      toast.success('Profil uložen');
      if (refreshUser) await refreshUser();
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Uložení selhalo');
    } finally {
      setSaving(false);
    }
  };

  const nameCs = (p) => p.name_cs || p.name_en || p.name || '—';

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

  if (loading) {
    const loader = (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-slate-500" />
      </div>
    );
    return embedded ? loader : <AdminLayout>{loader}</AdminLayout>;
  }

  const renderContent = (innerJSX) => embedded ? innerJSX : <AdminLayout>{innerJSX}</AdminLayout>;

  return renderContent((
      <div className="space-y-6" data-testid="my-profile-page">
        {/* Header */}
        <div className="flex items-center gap-3">
          <UserCircle className="w-7 h-7 text-slate-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-900" data-testid="profile-title">
              Můj profil
            </h1>
            <p className="text-sm text-gray-500">
              Spravujte své jméno a oblasti, ve kterých působíte jako lektor.
            </p>
          </div>
        </div>

        {/* Base info */}
        <Card className="p-5 space-y-4">
          <div>
            <Label htmlFor="profile-name">Jméno</Label>
            <Input
              id="profile-name"
              data-testid="profile-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Vaše jméno"
              maxLength={120}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm text-gray-600">
            <div>
              <span className="text-gray-500">E-mail:</span> {me?.email || user?.email}
            </div>
            <div>
              <span className="text-gray-500">Role:</span>{' '}
              <Badge variant="outline" className="ml-1">
                {me?.role || user?.role}
              </Badge>
            </div>
          </div>
        </Card>

        {/* Preferred age groups */}
        <Card className="p-5 space-y-3" data-testid="section-age-groups">
          <div className="flex items-center gap-2">
            <Users2 className="w-5 h-5 text-slate-600" />
            <h2 className="font-semibold text-slate-900">Preferované věkové skupiny</h2>
          </div>
          <p className="text-sm text-gray-500">
            Vyberte věkové skupiny, se kterými rádi pracujete. Pomůže systému
            preferovat vás při auto-přiřazení k programům.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {AGE_GROUPS.map((g) => (
              <label
                key={g.value}
                className={`flex items-center gap-2 px-3 py-2 border rounded-md cursor-pointer transition ${
                  preferredAges.includes(g.value)
                    ? 'border-emerald-400 bg-emerald-50 text-emerald-900'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                data-testid={`age-${g.value}`}
              >
                <input
                  type="checkbox"
                  checked={preferredAges.includes(g.value)}
                  onChange={() => toggleAge(g.value)}
                  className="accent-emerald-600"
                />
                <span className="text-sm">{g.label}</span>
              </label>
            ))}
          </div>
        </Card>

        {/* Supported programs */}
        <Card className="p-5 space-y-3" data-testid="section-supported">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-emerald-600" />
            <h2 className="font-semibold text-slate-900">Programy, které mohu vést</h2>
            <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
              {supportedIds.length}
            </Badge>
          </div>
          <p className="text-sm text-gray-500">
            U těchto programů vás může systém automaticky přiřadit jako hlavního lektora.
          </p>
          {programs.length === 0 ? (
            <p className="text-sm text-gray-400 italic">V instituci zatím nejsou žádné aktivní programy.</p>
          ) : (
            <div className="space-y-1 max-h-80 overflow-y-auto">
              {programs.map((p) => (
                <label
                  key={p.id}
                  className={`flex items-center justify-between gap-3 px-3 py-2 border rounded-md cursor-pointer text-sm transition ${
                    supportedIds.includes(p.id)
                      ? 'border-emerald-400 bg-emerald-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  data-testid={`supported-${p.id}`}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={supportedIds.includes(p.id)}
                      onChange={() => toggleSupported(p.id)}
                      className="accent-emerald-600"
                    />
                    <span className="truncate">{nameCs(p)}</span>
                    {p.age_group && (
                      <Badge variant="outline" className="text-xs">
                        {p.age_group}
                      </Badge>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </Card>

        {/* Learning programs (Náslech poznámka) */}
        <Card className="p-5 space-y-3" data-testid="section-learning">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-amber-600" />
            <h2 className="font-semibold text-slate-900">
              Programy, které se chci naučit (náslech)
            </h2>
            <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-200">
              {learningIds.length}
            </Badge>
          </div>
          <div className="rounded-md bg-amber-50/60 border border-amber-100 px-3 py-2 text-sm text-amber-800 flex gap-2">
            <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p>
              Označte programy, které chcete absolvovat jako náslech. Systém vás u nich
              <strong> nebude </strong> automaticky přiřazovat jako hlavního lektora.
              Po absolvování program přesuňte do sekce „mohu vést" výše.
            </p>
          </div>
          {programs.length === 0 ? (
            <p className="text-sm text-gray-400 italic">V instituci zatím nejsou žádné aktivní programy.</p>
          ) : (
            <div className="space-y-1 max-h-80 overflow-y-auto">
              {programs.map((p) => (
                <label
                  key={p.id}
                  className={`flex items-center justify-between gap-3 px-3 py-2 border rounded-md cursor-pointer text-sm transition ${
                    learningIds.includes(p.id)
                      ? 'border-amber-400 bg-amber-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  data-testid={`learning-${p.id}`}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={learningIds.includes(p.id)}
                      onChange={() => toggleLearning(p.id)}
                      className="accent-amber-600"
                    />
                    <span className="truncate">{nameCs(p)}</span>
                    {p.age_group && (
                      <Badge variant="outline" className="text-xs">
                        {p.age_group}
                      </Badge>
                    )}
                  </div>
                </label>
              ))}
            </div>
          )}
        </Card>

        {/* Admin note (read-only for non-admins) */}
        {me?.admin_note && !isAdmin && (
          <Card className="p-5 space-y-2 bg-slate-50">
            <h2 className="font-semibold text-slate-900 text-sm">Poznámka od správce</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{me.admin_note}</p>
          </Card>
        )}

        {/* Change password */}
        <Card className="p-5 space-y-4" data-testid="section-change-password">
          <div className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-slate-600" />
            <h2 className="font-semibold text-slate-900">Změna hesla</h2>
          </div>
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
                <><KeyRound className="w-4 h-4 mr-2" /> Změnit heslo</>
              )}
            </Button>
          </form>
        </Card>

        {/* Save button */}
        <div className="flex items-center justify-end gap-3 sticky bottom-4 bg-white/90 backdrop-blur rounded-lg p-3 border border-gray-200 shadow-sm">
          <Button
            onClick={handleSave}
            disabled={saving}
            className="bg-slate-800 hover:bg-slate-700 text-white"
            data-testid="profile-save-button"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Ukládám…
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Uložit změny
              </>
            )}
          </Button>
        </div>
      </div>
  ));
};

export default MyProfilePage;
