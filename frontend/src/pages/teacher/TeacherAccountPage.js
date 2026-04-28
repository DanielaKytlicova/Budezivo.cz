import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Header } from '../../components/layout/Header';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Heart, BookOpen, User, LogOut, Loader2, Calendar,
  School, ExternalLink, Building2, Trash2,
} from 'lucide-react';
import { useTeacherAuth } from '../../context/TeacherAuthContext';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { id: 'favorites', label: 'Oblíbené', icon: Heart },
  { id: 'history',   label: 'Historie',  icon: BookOpen },
  { id: 'profile',   label: 'Profil',    icon: User },
];

const STATUS_LABEL = {
  pending:   { label: 'Čeká na potvrzení', color: 'text-amber-700 bg-amber-50 border-amber-200' },
  confirmed: { label: 'Potvrzeno',         color: 'text-green-700 bg-green-50 border-green-200' },
  cancelled: { label: 'Zrušeno',           color: 'text-red-700 bg-red-50 border-red-200' },
  completed: { label: 'Proběhlo',          color: 'text-slate-700 bg-slate-50 border-slate-200' },
  no_show:   { label: 'Nedostavili se',    color: 'text-slate-700 bg-slate-50 border-slate-200' },
};

export const TeacherAccountPage = () => {
  const navigate = useNavigate();
  const { teacher, isAuthenticated, isLoading, logout, updateProfile, authConfig } = useTeacherAuth();
  const [tab, setTab] = useState('favorites');
  const [favorites, setFavorites] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loadingData, setLoadingData] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      navigate('/ucitel/prihlaseni', { state: { from: '/ucitel/ucet' } });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const loadData = async () => {
    setLoadingData(true);
    try {
      const [favRes, bRes] = await Promise.all([
        axios.get(`${API_URL}/api/teacher/favorites`, authConfig()),
        axios.get(`${API_URL}/api/teacher/bookings`,  authConfig()),
      ]);
      setFavorites(favRes.data || []);
      setBookings(bRes.data || []);
    } catch (_e) {
      toast.error('Nepodařilo se načíst data.');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => { if (isAuthenticated) loadData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const handleRemoveFavorite = async (programId) => {
    try {
      await axios.delete(`${API_URL}/api/teacher/favorites/${programId}`, authConfig());
      setFavorites(prev => prev.filter(f => f.program_id !== programId));
      toast.success('Odebráno z oblíbených');
    } catch (_e) {
      toast.error('Operace se nezdařila');
    }
  };

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#4A6FA5]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Header />
      <div className="max-w-4xl mx-auto px-4 py-10" data-testid="teacher-account-page">
        {/* Header card */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[#2B3E50]" data-testid="teacher-account-name">
              {teacher.name}
            </h1>
            <p className="text-sm text-gray-500">{teacher.email}{teacher.school_name ? ` · ${teacher.school_name}` : ''}</p>
          </div>
          <Button variant="outline" onClick={() => { logout(); navigate('/'); }} data-testid="teacher-logout-btn">
            <LogOut className="w-4 h-4 mr-2" /> Odhlásit
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-white rounded-xl p-1 border border-gray-200" role="tablist">
          {TABS.map(t => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                role="tab"
                onClick={() => setTab(t.id)}
                data-testid={`teacher-tab-${t.id}`}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors ${active ? 'bg-[#4A6FA5] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50'}`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        {tab === 'favorites' && (
          <FavoritesTab
            loading={loadingData}
            favorites={favorites}
            onRemove={handleRemoveFavorite}
          />
        )}
        {tab === 'history' && (
          <HistoryTab loading={loadingData} bookings={bookings} />
        )}
        {tab === 'profile' && (
          <ProfileTab teacher={teacher} onUpdate={updateProfile} />
        )}
      </div>
    </div>
  );
};

// ─── Favorites tab ────────────────────────────────────────────────────────────
const FavoritesTab = ({ loading, favorites, onRemove }) => {
  if (loading) return <div className="py-10 text-center"><Loader2 className="w-6 h-6 mx-auto animate-spin text-[#4A6FA5]" /></div>;
  if (favorites.length === 0) {
    return (
      <Card className="p-8 text-center" data-testid="teacher-favorites-empty">
        <Heart className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-600 mb-4">Zatím nemáte žádné oblíbené programy.</p>
        <Link to="/programy-pro-skoly" className="inline-block">
          <Button className="bg-[#4A6FA5] hover:bg-[#3a5f95]">Procházet katalog programů</Button>
        </Link>
      </Card>
    );
  }
  return (
    <div className="space-y-3" data-testid="teacher-favorites-list">
      {favorites.map(f => (
        <Card key={f.favorite_id} className="p-4" data-testid={`teacher-favorite-${f.program_id}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-[#2B3E50] mb-1 truncate">{f.name}</h3>
              <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {f.institution_name}{f.institution_city ? ` · ${f.institution_city}` : ''}
              </p>
              {f.description && <p className="text-sm text-gray-600 line-clamp-2 mb-2">{f.description}</p>}
              <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                {f.duration ? <span>{f.duration} min.</span> : null}
                {f.pricing_info && <span>· {f.pricing_info}</span>}
              </div>
            </div>
            <div className="flex flex-col gap-2 shrink-0">
              <Link to={`/programy-pro-skoly/${f.program_id}`}>
                <Button size="sm" variant="outline" data-testid={`teacher-favorite-detail-${f.program_id}`}>
                  Detail <ExternalLink className="w-3.5 h-3.5 ml-1" />
                </Button>
              </Link>
              <Button
                size="sm"
                variant="ghost"
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                onClick={() => onRemove(f.program_id)}
                data-testid={`teacher-favorite-remove-${f.program_id}`}
              >
                <Trash2 className="w-3.5 h-3.5 mr-1" /> Odebrat
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};

// ─── History tab ──────────────────────────────────────────────────────────────
const HistoryTab = ({ loading, bookings }) => {
  if (loading) return <div className="py-10 text-center"><Loader2 className="w-6 h-6 mx-auto animate-spin text-[#4A6FA5]" /></div>;
  if (bookings.length === 0) {
    return (
      <Card className="p-8 text-center" data-testid="teacher-history-empty">
        <BookOpen className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-600">Zatím nemáte žádné rezervace.</p>
        <p className="text-xs text-gray-400 mt-2">Historie se naplní při příští rezervaci pod stejným e-mailem.</p>
      </Card>
    );
  }
  return (
    <div className="space-y-3" data-testid="teacher-history-list">
      {bookings.map(b => {
        const status = STATUS_LABEL[b.status] || { label: b.status, color: 'text-slate-700 bg-slate-50 border-slate-200' };
        return (
          <Card key={b.id} className="p-4" data-testid={`teacher-booking-${b.id}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-[#2B3E50] truncate">{b.program_name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${status.color}`}>{status.label}</span>
                </div>
                <p className="text-xs text-gray-500 flex items-center gap-1 mb-1">
                  <Calendar className="w-3 h-3" />
                  {new Date(b.date).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })}{' '}· {b.time_block}
                </p>
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <School className="w-3 h-3" />
                  {b.institution_name}{b.school_name ? ` · ${b.school_name}` : ''}
                </p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
};

// ─── Profile tab ──────────────────────────────────────────────────────────────
const ProfileTab = ({ teacher, onUpdate }) => {
  const [name, setName] = useState(teacher.name || '');
  const [school, setSchool] = useState(teacher.school_name || '');
  const [phone, setPhone] = useState(teacher.phone || '');
  const [saving, setSaving] = useState(false);

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    const r = await onUpdate({ name, school_name: school, phone });
    setSaving(false);
    if (r.ok) toast.success('Profil uložen.');
    else toast.error(r.error);
  };

  return (
    <Card className="p-6" data-testid="teacher-profile-tab">
      <h2 className="font-semibold text-[#2B3E50] mb-4">Vaše údaje</h2>
      <form onSubmit={onSave} className="space-y-4 max-w-md">
        <div>
          <Label htmlFor="p-email">E-mail</Label>
          <Input id="p-email" value={teacher.email} disabled />
          <p className="text-xs text-gray-500 mt-1">E-mail je hlavní identifikátor a nelze ho měnit.</p>
        </div>
        <div>
          <Label htmlFor="p-name">Jméno a příjmení</Label>
          <Input id="p-name" value={name} onChange={e => setName(e.target.value)} required data-testid="teacher-profile-name" />
        </div>
        <div>
          <Label htmlFor="p-school">Škola</Label>
          <Input id="p-school" value={school} onChange={e => setSchool(e.target.value)} placeholder="Slouží pro předvyplnění rezervací" data-testid="teacher-profile-school" />
        </div>
        <div>
          <Label htmlFor="p-phone">Telefon</Label>
          <Input id="p-phone" value={phone} onChange={e => setPhone(e.target.value)} data-testid="teacher-profile-phone" />
        </div>
        <Button type="submit" disabled={saving} className="bg-[#4A6FA5] hover:bg-[#3a5f95]" data-testid="teacher-profile-save">
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          Uložit změny
        </Button>
      </form>
    </Card>
  );
};

export default TeacherAccountPage;
