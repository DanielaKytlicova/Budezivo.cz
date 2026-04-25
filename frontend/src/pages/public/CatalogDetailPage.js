import React, { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { ArrowLeft, MapPin, Clock, Users, Sparkles, Calendar as CalIcon, MessageSquare } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function CatalogDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showInquiry, setShowInquiry] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: '', email: '', school: '', message: '',
  });

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/public/catalog/${id}`)
      .then(r => setP(r.data))
      .catch(() => setP(null))
      .finally(() => setLoading(false));
  }, [id]);

  const handleInquiry = async (e) => {
    e.preventDefault();
    if (!form.name || !form.email) {
      toast.error('Vyplňte prosím jméno a e-mail.');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/public/contact`, {
        name: form.name,
        email: form.email,
        institution: form.school || '—',
        availability: form.message,
        source: `Katalog programů — poptávka: ${p?.name || ''} (${p?.institution?.name || ''})`,
      });
      toast.success('Děkujeme! Brzy vás kontaktujeme.');
      setShowInquiry(false);
      setForm({ name: '', email: '', school: '', message: '' });
    } catch {
      toast.error('Nepodařilo se odeslat poptávku. Zkuste to prosím znovu.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FA]">
        <Header />
        <div className="max-w-5xl mx-auto px-6 md:px-8 py-12">
          <div className="h-72 bg-slate-100 rounded-2xl animate-pulse mb-6" />
          <div className="h-8 bg-slate-100 rounded w-2/3 animate-pulse mb-3" />
          <div className="h-4 bg-slate-100 rounded w-1/3 animate-pulse" />
        </div>
        <Footer />
      </div>
    );
  }

  if (!p) {
    return (
      <div className="min-h-screen bg-[#F8F9FA]">
        <Header />
        <div className="max-w-3xl mx-auto px-6 md:px-8 py-20 text-center" data-testid="catalog-detail-not-found">
          <Sparkles className="w-12 h-12 text-[#C4AB86] mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-slate-800 mb-2">Program nenalezen</h1>
          <p className="text-slate-500 mb-6">Tento program v katalogu neexistuje nebo byl odstraněn.</p>
          <Button onClick={() => navigate('/programy-pro-skoly')} data-testid="catalog-detail-back-empty">
            Zpět do katalogu
          </Button>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA]" data-testid="catalog-detail-page">
      <Header />

      <div className="max-w-5xl mx-auto px-6 md:px-8 py-8 md:py-12">
        <Link
          to="/programy-pro-skoly"
          className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#4A6FA5] mb-6"
          data-testid="catalog-detail-back"
        >
          <ArrowLeft className="w-4 h-4" /> Zpět do katalogu
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
          {/* Main */}
          <div>
            {/* Cover */}
            <div className="relative h-64 md:h-80 rounded-2xl overflow-hidden bg-gradient-to-br from-[#EEF2F9] to-[#F8F9FA] mb-6">
              {p.image_url ? (
                <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Sparkles className="w-16 h-16 text-[#4A6FA5]/30" />
                </div>
              )}
              {p.age_labels?.length > 0 && (
                <div className="absolute top-4 left-4 flex flex-wrap gap-2">
                  {p.age_labels.map(a => (
                    <Badge key={a} className="bg-white/95 text-[#4A6FA5] hover:bg-white border-0 backdrop-blur-sm">{a}</Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Title */}
            <p className="text-sm text-slate-500 mb-1" data-testid="catalog-detail-institution">
              {p.institution.name}
            </p>
            <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4" data-testid="catalog-detail-title">
              {p.name}
            </h1>

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-500 mb-6">
              {p.institution.city && (
                <span className="inline-flex items-center gap-1.5"><MapPin className="w-4 h-4" />{p.institution.city}</span>
              )}
              <span className="inline-flex items-center gap-1.5"><Clock className="w-4 h-4" />{p.duration} min</span>
              {p.max_capacity && (
                <span className="inline-flex items-center gap-1.5"><Users className="w-4 h-4" />{p.min_capacity || 1}–{p.max_capacity} dětí</span>
              )}
            </div>

            {/* Categories */}
            {p.categories?.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-6">
                {p.categories.map(c => (
                  <span key={c} className="px-3 py-1 text-xs rounded-full bg-[#F1F4FA] text-[#4A6FA5] border border-[#E1E8F2]">
                    {c}
                  </span>
                ))}
              </div>
            )}

            {/* Description */}
            <Card className="p-6 md:p-8 bg-white border-0 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900 mb-3">O programu</h2>
              <p className="text-slate-700 whitespace-pre-line leading-relaxed" data-testid="catalog-detail-description">
                {p.description_full || p.description || 'Popis programu zatím není k dispozici.'}
              </p>

              {p.pricing_info && (
                <div className="mt-6 pt-6 border-t border-slate-100">
                  <h3 className="text-sm font-semibold text-slate-900 mb-2">Cena</h3>
                  <p className="text-sm text-slate-600">{p.pricing_info}</p>
                </div>
              )}
            </Card>
          </div>

          {/* Sidebar — CTA */}
          <aside>
            <Card className="p-6 bg-white border-0 shadow-sm sticky top-24" data-testid="catalog-detail-cta">
              <div className="space-y-3">
                <Button
                  onClick={() => navigate(`/booking/${p.institution.id}?program=${p.id}`)}
                  className="w-full h-12 bg-[#4A6FA5] hover:bg-[#3d5e90] text-white rounded-lg"
                  data-testid="catalog-cta-book"
                >
                  <CalIcon className="w-4 h-4 mr-2" /> Vybrat termín
                </Button>
                <Button
                  onClick={() => setShowInquiry(true)}
                  variant="outline"
                  className="w-full h-12 border-slate-200 text-slate-700 hover:bg-slate-50 rounded-lg"
                  data-testid="catalog-cta-inquiry"
                >
                  <MessageSquare className="w-4 h-4 mr-2" /> Nezávazně poptat
                </Button>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-100 space-y-3 text-sm">
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-400 mb-1">Pořadatel</p>
                  <p className="font-medium text-slate-800">{p.institution.name}</p>
                  {p.institution.address && (
                    <p className="text-slate-500 text-xs mt-0.5">{p.institution.address}</p>
                  )}
                </div>
                {p.reservation_count > 0 && (
                  <div className="text-xs text-slate-500 inline-flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#C4AB86]" />
                    {p.reservation_count} škol už si tento program objednalo
                  </div>
                )}
              </div>
            </Card>
          </aside>
        </div>
      </div>

      {/* Inquiry dialog */}
      <Dialog open={showInquiry} onOpenChange={setShowInquiry}>
        <DialogContent className="max-w-md" data-testid="catalog-inquiry-dialog">
          <DialogHeader>
            <DialogTitle>Nezávazná poptávka</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleInquiry} className="space-y-3">
            <p className="text-sm text-slate-500">
              Pošleme vaše dotazy přímo pořadateli programu „{p.name}".
            </p>
            <div>
              <Label htmlFor="inq-name">Vaše jméno *</Label>
              <Input id="inq-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required data-testid="inquiry-name" />
            </div>
            <div>
              <Label htmlFor="inq-email">E-mail *</Label>
              <Input id="inq-email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required data-testid="inquiry-email" />
            </div>
            <div>
              <Label htmlFor="inq-school">Škola</Label>
              <Input id="inq-school" value={form.school} onChange={e => setForm({ ...form, school: e.target.value })} data-testid="inquiry-school" />
            </div>
            <div>
              <Label htmlFor="inq-msg">Zpráva (preferovaný termín, počet dětí, otázky...)</Label>
              <Textarea id="inq-msg" rows={4} value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} data-testid="inquiry-message" />
            </div>
            <Button type="submit" disabled={submitting} className="w-full bg-[#C4AB86] hover:bg-[#b39975] text-white" data-testid="inquiry-submit">
              {submitting ? 'Odesílám...' : 'Odeslat poptávku'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Footer />
    </div>
  );
}
