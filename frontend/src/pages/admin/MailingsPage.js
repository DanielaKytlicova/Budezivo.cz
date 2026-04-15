import React, { useEffect, useState, useContext, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Mail, Plus, Send, Save, Eye, Trash2, ChevronRight, ChevronLeft,
  AlertTriangle, Check, X, Search, School, FileText, Users, Clock,
  ArrowLeft, Loader2, CheckCircle, XCircle, Info
} from 'lucide-react';
import { API } from '../../config/api';

const STATUS_MAP = {
  draft: { label: 'Koncept', color: 'bg-yellow-100 text-yellow-800' },
  sending: { label: 'Odesílá se...', color: 'bg-blue-100 text-blue-800' },
  sent: { label: 'Odesláno', color: 'bg-green-100 text-green-800' },
  partial: { label: 'Částečně', color: 'bg-orange-100 text-orange-800' },
  failed: { label: 'Chyba', color: 'bg-red-100 text-red-800' },
};

const MODE_LABELS = {
  relevant_only: 'Pouze relevantní školy',
  all: 'Všechny školy',
  manual: 'Ruční výběr',
  relevant_plus_manual: 'Relevantní + ruční výběr',
};

const TG_LABELS = {
  ms_3_6: 'MŠ', zs1_7_12: '1. st. ZŠ', zs2_12_15: '2. st. ZŠ',
  ss_14_18: 'SŠ', gym_14_18: 'Gymnázium', adults: 'Dospělí', all: 'Všechny',
};

export const MailingsPage = () => {
  const { user } = useContext(AuthContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [preselectedProgram, setPreselectedProgram] = useState(null);

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/mailings`, { withCredentials: true });
      setCampaigns(res.data.campaigns || []);
    } catch { toast.error('Nepodařilo se načíst kampaně'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchCampaigns(); }, [fetchCampaigns]);

  // Handle URL param ?program=ID&name=Name
  useEffect(() => {
    const programId = searchParams.get('program');
    const programName = searchParams.get('name');
    if (programId) {
      setPreselectedProgram({ id: programId, name: programName || '' });
      setShowWizard(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const openDetail = async (id) => {
    setDetailLoading(true);
    try {
      const res = await axios.get(`${API}/mailings/${id}`, { withCredentials: true });
      setSelectedCampaign(res.data);
    } catch { toast.error('Nepodařilo se načíst detail'); }
    finally { setDetailLoading(false); }
  };

  const deleteCampaign = async (id) => {
    if (!window.confirm('Opravdu smazat koncept?')) return;
    try {
      await axios.delete(`${API}/mailings/${id}`, { withCredentials: true });
      toast.success('Koncept smazán');
      setCampaigns(prev => prev.filter(c => c.id !== id));
      if (selectedCampaign?.id === id) setSelectedCampaign(null);
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při mazání'); }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900" data-testid="mailings-title">
            Propagační mailingy
          </h1>
          <Button onClick={() => { setShowWizard(true); setSelectedCampaign(null); }} data-testid="create-campaign-btn">
            <Plus className="w-4 h-4 mr-1.5" /> Nová kampaň
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
          </div>
        ) : campaigns.length === 0 ? (
          <Card className="p-12 text-center">
            <Mail className="w-12 h-12 mx-auto mb-4 text-slate-300" />
            <h3 className="text-lg font-medium text-slate-700 mb-2">Zatím žádné kampaně</h3>
            <p className="text-slate-500 mb-4">Vytvořte první propagační mailing pro vaše školy.</p>
            <Button onClick={() => setShowWizard(true)} data-testid="empty-create-btn">
              <Plus className="w-4 h-4 mr-1.5" /> Vytvořit kampaň
            </Button>
          </Card>
        ) : (
          <div className="space-y-3">
            {campaigns.map(c => {
              const st = STATUS_MAP[c.status] || STATUS_MAP.draft;
              return (
                <Card key={c.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => openDetail(c.id)} data-testid={`campaign-card-${c.id}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-slate-900 truncate">{c.name}</h3>
                        <Badge className={st.color}>{st.label}</Badge>
                        <Badge variant="outline">{c.programs_count} {c.programs_count === 1 ? 'program' : 'programů'}</Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-slate-500">
                        <span>{c.subject}</span>
                        <span>{c.total_recipients} příjemců</span>
                        {c.sent_at && <span>{new Date(c.sent_at).toLocaleDateString('cs-CZ')}</span>}
                        {!c.sent_at && c.created_at && <span>Vytvořeno: {new Date(c.created_at).toLocaleDateString('cs-CZ')}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {c.status === 'draft' && (
                        <Button variant="ghost" size="sm" onClick={e => { e.stopPropagation(); deleteCampaign(c.id); }} data-testid={`delete-campaign-${c.id}`}>
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      )}
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Campaign detail dialog */}
        {selectedCampaign && (
          <CampaignDetail
            campaign={selectedCampaign}
            onClose={() => setSelectedCampaign(null)}
            onRefresh={fetchCampaigns}
            onEdit={() => { setShowWizard(true); }}
          />
        )}

        {/* Campaign wizard */}
        {showWizard && (
          <CampaignWizard
            editCampaign={selectedCampaign?.status === 'draft' ? selectedCampaign : null}
            preselectedProgram={preselectedProgram}
            onClose={() => { setShowWizard(false); setPreselectedProgram(null); }}
            onComplete={() => { setShowWizard(false); setSelectedCampaign(null); setPreselectedProgram(null); fetchCampaigns(); }}
          />
        )}
      </div>
    </AdminLayout>
  );
};

/* ==================== CAMPAIGN DETAIL ==================== */
const CampaignDetail = ({ campaign, onClose, onRefresh, onEdit }) => {
  const c = campaign;
  const st = STATUS_MAP[c.status] || STATUS_MAP.draft;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85dvh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>{c.name}</span>
            <Badge className={st.color}>{st.label}</Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <Card className="p-3 text-center">
              <div className="text-2xl font-bold text-slate-900">{c.total_recipients}</div>
              <div className="text-xs text-slate-500">Příjemců</div>
            </Card>
            <Card className="p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{c.sent_count}</div>
              <div className="text-xs text-slate-500">Odesláno</div>
            </Card>
            <Card className="p-3 text-center">
              <div className="text-2xl font-bold text-red-600">{c.failed_count}</div>
              <div className="text-xs text-slate-500">Neúspěšné</div>
            </Card>
          </div>

          {/* Info */}
          <div className="bg-slate-50 rounded-lg p-4 space-y-2 text-sm">
            <div><strong>Režim výběru:</strong> {MODE_LABELS[c.recipient_mode] || c.recipient_mode}</div>
            <div><strong>Předmět:</strong> {c.subject}</div>
            {c.sent_at && <div><strong>Odesláno:</strong> {new Date(c.sent_at).toLocaleString('cs-CZ')}</div>}
            <div><strong>Vytvořeno:</strong> {new Date(c.created_at).toLocaleString('cs-CZ')}</div>
          </div>

          {/* Email content snapshot */}
          {c.content_snapshot && (
            <details className="border rounded-lg">
              <summary className="px-4 py-2 cursor-pointer font-medium text-slate-700 bg-slate-50 rounded-t-lg">
                Obsah emailu (snapshot)
              </summary>
              <div className="p-4 space-y-2 text-sm">
                <div><strong>Oslovení:</strong> {c.content_snapshot.greeting}</div>
                <div><strong>Úvod:</strong> {c.content_snapshot.intro_text}</div>
                <div><strong>Závěr:</strong> {c.content_snapshot.closing_text}</div>
                <div><strong>Podpis:</strong> <span className="whitespace-pre-line">{c.content_snapshot.signature}</span></div>
              </div>
            </details>
          )}

          {/* Programs */}
          <details open className="border rounded-lg">
            <summary className="px-4 py-2 cursor-pointer font-medium text-slate-700 bg-slate-50 rounded-t-lg">
              Programy ({c.programs?.length || 0})
            </summary>
            <div className="p-4 space-y-2">
              {(c.programs || []).map(p => (
                <div key={p.id} className="flex items-center justify-between py-1.5 border-b last:border-0">
                  <span className="font-medium text-slate-800">{p.name}</span>
                  <div className="flex gap-1">
                    {(p.target_groups || []).map(tg => (
                      <Badge key={tg} variant="outline" className="text-xs">{TG_LABELS[tg] || tg}</Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </details>

          {/* Recipients */}
          <details className="border rounded-lg">
            <summary className="px-4 py-2 cursor-pointer font-medium text-slate-700 bg-slate-50 rounded-t-lg">
              Příjemci ({c.recipients?.length || 0})
            </summary>
            <div className="p-4 max-h-[300px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="pb-2">Škola</th>
                    <th className="pb-2">Email</th>
                    <th className="pb-2">Stav</th>
                    <th className="pb-2">Programy</th>
                  </tr>
                </thead>
                <tbody>
                  {(c.recipients || []).map(r => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-1.5 font-medium">{r.school_name}</td>
                      <td className="py-1.5 text-slate-600">{r.email}</td>
                      <td className="py-1.5">
                        {r.status === 'sent' && <CheckCircle className="w-4 h-4 text-green-500" />}
                        {r.status === 'failed' && <XCircle className="w-4 h-4 text-red-500" title={r.failure_reason} />}
                        {r.status === 'pending' && <Clock className="w-4 h-4 text-slate-400" />}
                      </td>
                      <td className="py-1.5 text-xs text-slate-500">
                        {(r.programs || []).map(p => p.program_name).join(', ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </div>

        <DialogFooter>
          {c.status === 'draft' && (
            <Button variant="outline" onClick={onEdit} data-testid="edit-campaign-btn">
              <FileText className="w-4 h-4 mr-1.5" /> Upravit
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>Zavřít</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

/* ==================== CAMPAIGN WIZARD ==================== */
const CampaignWizard = ({ editCampaign, preselectedProgram, onClose, onComplete }) => {
  const [step, setStep] = useState(1);
  const [programs, setPrograms] = useState([]);
  const [allPrograms, setAllPrograms] = useState([]);
  const [campaignId, setCampaignId] = useState(editCampaign?.id || null);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);

  // Step 1: Type & Programs
  const [campaignName, setCampaignName] = useState(editCampaign?.name || (preselectedProgram?.name ? `Nabídka: ${preselectedProgram.name}` : ''));
  const [campaignType, setCampaignType] = useState(editCampaign?.type || (preselectedProgram ? 'single_program' : 'seasonal'));
  const [selectedProgramIds, setSelectedProgramIds] = useState(
    editCampaign?.programs?.map(p => p.id) || (preselectedProgram?.id ? [preselectedProgram.id] : [])
  );

  // Step 2: Recipients
  const [recipientMode, setRecipientMode] = useState(editCampaign?.recipient_mode || 'relevant_only');
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [manualSchoolIds, setManualSchoolIds] = useState([]);
  const [excludedVisible, setExcludedVisible] = useState(false);

  // Step 3: Email content
  const [subject, setSubject] = useState(editCampaign?.subject || '');
  const [greeting, setGreeting] = useState(editCampaign?.greeting || '');
  const [introText, setIntroText] = useState(editCampaign?.intro_text || '');
  const [closingText, setClosingText] = useState(editCampaign?.closing_text || '');
  const [signature, setSignature] = useState(editCampaign?.signature || '');

  // Fetch programs
  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API}/programs`, { withCredentials: true });
        const active = (res.data || []).filter(p => p.status === 'active' && p.is_published);
        setAllPrograms(active);
      } catch {}
    };
    load();
  }, []);

  // Load default texts
  const loadDefaults = async (audience = 'general') => {
    try {
      const res = await axios.post(`${API}/mailings/default-texts?audience=${audience}`, {}, { withCredentials: true });
      setSubject(res.data.subject);
      setGreeting(res.data.greeting);
      setIntroText(res.data.intro_text);
      setClosingText(res.data.closing_text);
      setSignature(res.data.signature);
    } catch {}
  };

  // Preview recipients
  const loadPreview = async () => {
    if (selectedProgramIds.length === 0) return;
    setPreviewLoading(true);
    try {
      const res = await axios.post(`${API}/mailings/preview-recipients`, {
        program_ids: selectedProgramIds,
        recipient_mode: recipientMode,
        manual_school_ids: manualSchoolIds,
      }, { withCredentials: true });
      setPreview(res.data);
    } catch { toast.error('Nepodařilo se načíst náhled příjemců'); }
    finally { setPreviewLoading(false); }
  };

  useEffect(() => {
    if (step === 2 && selectedProgramIds.length > 0) {
      loadPreview();
    }
  }, [step, recipientMode, manualSchoolIds.length]);

  // Toggle manual school from excluded list
  const toggleManualSchool = (schoolId) => {
    setManualSchoolIds(prev =>
      prev.includes(schoolId) ? prev.filter(id => id !== schoolId) : [...prev, schoolId]
    );
  };

  // Save draft
  const saveDraft = async () => {
    if (!campaignName.trim()) { toast.error('Zadejte název kampaně'); return; }
    if (selectedProgramIds.length === 0) { toast.error('Vyberte alespoň jeden program'); return; }
    setSaving(true);
    try {
      const payload = {
        name: campaignName,
        type: campaignType,
        recipient_mode: recipientMode,
        program_ids: selectedProgramIds,
        subject, greeting, intro_text: introText, closing_text: closingText, signature,
      };
      if (campaignId) {
        await axios.put(`${API}/mailings/${campaignId}`, payload, { withCredentials: true });
        toast.success('Koncept uložen');
      } else {
        const res = await axios.post(`${API}/mailings`, payload, { withCredentials: true });
        setCampaignId(res.data.id);
        toast.success('Kampaň vytvořena jako koncept');
      }
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při ukládání'); }
    finally { setSaving(false); }
  };

  // Send campaign
  const sendCampaign = async () => {
    if (!campaignId) {
      // Create first
      if (!campaignName.trim() || selectedProgramIds.length === 0) {
        toast.error('Vyplňte název a vyberte programy');
        return;
      }
      setSaving(true);
      try {
        const payload = {
          name: campaignName, type: campaignType, recipient_mode: recipientMode,
          program_ids: selectedProgramIds,
          subject, greeting, intro_text: introText, closing_text: closingText, signature,
        };
        const res = await axios.post(`${API}/mailings`, payload, { withCredentials: true });
        setCampaignId(res.data.id);
        // Now send
        await axios.post(`${API}/mailings/${res.data.id}/send`, {
          manual_school_ids: recipientMode === 'relevant_plus_manual' || recipientMode === 'manual' ? manualSchoolIds : null,
        }, { withCredentials: true });
        toast.success('Kampaň odeslána!');
        onComplete();
      } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při odesílání'); }
      finally { setSaving(false); }
      return;
    }

    setSending(true);
    try {
      // Save latest changes first
      await axios.put(`${API}/mailings/${campaignId}`, {
        name: campaignName, recipient_mode: recipientMode,
        program_ids: selectedProgramIds,
        subject, greeting, intro_text: introText, closing_text: closingText, signature,
      }, { withCredentials: true });

      await axios.post(`${API}/mailings/${campaignId}/send`, {
        manual_school_ids: recipientMode === 'relevant_plus_manual' || recipientMode === 'manual' ? manualSchoolIds : null,
      }, { withCredentials: true });
      toast.success('Kampaň odeslána!');
      onComplete();
    } catch (e) { toast.error(e.response?.data?.detail || 'Chyba při odesílání'); }
    finally { setSending(false); }
  };

  const selectedPrograms = allPrograms.filter(p => selectedProgramIds.includes(p.id));

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90dvh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {editCampaign ? 'Upravit kampaň' : 'Nová propagační kampaň'}
          </DialogTitle>
        </DialogHeader>

        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-4">
          {[1, 2, 3, 4].map(s => (
            <div key={s} className="flex items-center gap-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === s ? 'bg-slate-800 text-white' : step > s ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400'
              }`}>
                {step > s ? <Check className="w-4 h-4" /> : s}
              </div>
              <span className={`text-xs hidden sm:inline ${step === s ? 'text-slate-800 font-medium' : 'text-slate-400'}`}>
                {s === 1 ? 'Programy' : s === 2 ? 'Příjemci' : s === 3 ? 'Text emailu' : 'Odeslání'}
              </span>
              {s < 4 && <ChevronRight className="w-4 h-4 text-slate-300" />}
            </div>
          ))}
        </div>

        {/* STEP 1: Type & Programs */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <Label>Název kampaně *</Label>
              <Input value={campaignName} onChange={e => setCampaignName(e.target.value)} placeholder="např. Nabídka programů na jaro 2026" data-testid="campaign-name-input" />
            </div>
            <div>
              <Label>Typ kampaně</Label>
              <Select value={campaignType} onValueChange={setCampaignType}>
                <SelectTrigger data-testid="campaign-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="single_program">Jednotlivý program</SelectItem>
                  <SelectItem value="seasonal">Sezónní nabídka</SelectItem>
                  <SelectItem value="custom">Vlastní mailing</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Vyberte programy ({selectedProgramIds.length})</Label>
              <div className="max-h-[300px] overflow-y-auto border rounded-lg mt-1">
                {allPrograms.length === 0 ? (
                  <p className="p-4 text-sm text-slate-500">Žádné aktivní programy</p>
                ) : allPrograms.map(p => {
                  const checked = selectedProgramIds.includes(p.id);
                  return (
                    <label key={p.id} className={`flex items-center gap-3 px-4 py-2.5 border-b last:border-0 cursor-pointer hover:bg-slate-50 ${checked ? 'bg-blue-50' : ''}`}>
                      <input type="checkbox" checked={checked} onChange={() => {
                        setSelectedProgramIds(prev => checked ? prev.filter(id => id !== p.id) : [...prev, p.id]);
                      }} className="rounded" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-slate-800 truncate">{p.name_cs || p.name}</div>
                        <div className="flex gap-1 mt-0.5">
                          {(p.target_groups || []).map(tg => (
                            <Badge key={tg} variant="outline" className="text-xs">{TG_LABELS[tg] || tg}</Badge>
                          ))}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Recipients */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <Label>Režim výběru příjemců</Label>
              <Select value={recipientMode} onValueChange={v => { setRecipientMode(v); setManualSchoolIds([]); }}>
                <SelectTrigger data-testid="recipient-mode-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="relevant_only">Pouze relevantní školy (chytrý výběr)</SelectItem>
                  <SelectItem value="relevant_plus_manual">Relevantní + ruční přidání</SelectItem>
                  <SelectItem value="all">Všechny školy</SelectItem>
                  <SelectItem value="manual">Ruční výběr</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500 mt-1">
                {recipientMode === 'relevant_only' && 'Každá škola obdrží pouze relevantní programy podle svých kategorií.'}
                {recipientMode === 'relevant_plus_manual' && 'Automaticky vybrané relevantní školy + možnost ručně přidat další.'}
                {recipientMode === 'all' && 'Všem školám odejde kompletní přehled všech vybraných programů.'}
                {recipientMode === 'manual' && 'Ručně vyberte školy ze seznamu níže.'}
              </p>
            </div>

            {previewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-slate-400 mr-2" /> Načítání...
              </div>
            ) : preview && (
              <>
                {/* Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <Card className="p-3 text-center">
                    <div className="text-xl font-bold">{preview.stats.total_schools}</div>
                    <div className="text-xs text-slate-500">Škol celkem</div>
                  </Card>
                  <Card className="p-3 text-center">
                    <div className="text-xl font-bold text-green-600">{preview.stats.total_contacts}</div>
                    <div className="text-xs text-slate-500">Příjemců</div>
                  </Card>
                  <Card className="p-3 text-center">
                    <div className="text-xl font-bold text-slate-400">{preview.stats.excluded_count}</div>
                    <div className="text-xs text-slate-500">Vyloučeno</div>
                  </Card>
                  <Card className="p-3 text-center">
                    <div className="text-xl font-bold text-yellow-600">{preview.stats.schools_no_tags}</div>
                    <div className="text-xs text-slate-500">Bez kategorií</div>
                  </Card>
                </div>

                {/* Warnings */}
                {preview.warnings.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    {preview.warnings.map((w, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm text-amber-800">
                        <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{w}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Recipients list */}
                <details open className="border rounded-lg">
                  <summary className="px-4 py-2 cursor-pointer font-medium text-slate-700 bg-slate-50 rounded-t-lg">
                    Příjemci ({preview.recipients.length})
                  </summary>
                  <div className="max-h-[200px] overflow-y-auto">
                    {preview.recipients.map((r, i) => (
                      <div key={i} className="flex items-center justify-between px-4 py-1.5 border-b last:border-0 text-sm">
                        <div>
                          <span className="font-medium">{r.school_name}</span>
                          <span className="text-slate-500 ml-2">{r.email}</span>
                        </div>
                        <div className="flex gap-1">
                          {r.matched_segments.map(s => (
                            <Badge key={s} variant="outline" className="text-xs">{s}</Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                    {preview.recipients.length === 0 && (
                      <p className="p-4 text-sm text-slate-500">Žádní příjemci</p>
                    )}
                  </div>
                </details>

                {/* Excluded - for manual add */}
                {(recipientMode === 'relevant_plus_manual' || recipientMode === 'manual') && preview.excluded.length > 0 && (
                  <details className="border rounded-lg">
                    <summary className="px-4 py-2 cursor-pointer font-medium text-slate-700 bg-slate-50 rounded-t-lg">
                      Vyloučené školy — kliknutím přidáte ({preview.excluded.length})
                    </summary>
                    <div className="max-h-[200px] overflow-y-auto">
                      {preview.excluded.map((r, i) => {
                        const added = manualSchoolIds.includes(r.school_id);
                        return (
                          <div key={i} className={`flex items-center justify-between px-4 py-1.5 border-b last:border-0 text-sm cursor-pointer hover:bg-slate-50 ${added ? 'bg-green-50' : ''}`}
                               onClick={() => toggleManualSchool(r.school_id)}>
                            <div>
                              <span className="font-medium">{r.school_name}</span>
                              <span className="text-slate-500 ml-2">{r.email}</span>
                            </div>
                            {added ? (
                              <Badge className="bg-green-100 text-green-700">Přidáno</Badge>
                            ) : (
                              <Button variant="ghost" size="sm"><Plus className="w-3 h-3" /></Button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </details>
                )}
              </>
            )}
          </div>
        )}

        {/* STEP 3: Email content */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Label className="text-base font-medium">Šablona:</Label>
              {['general', 'ms', 'zs', 'ss'].map(k => (
                <Button key={k} variant="outline" size="sm" onClick={() => loadDefaults(k)}>
                  {k === 'general' ? 'Obecná' : k.toUpperCase()}
                </Button>
              ))}
            </div>
            <div>
              <Label>Předmět emailu *</Label>
              <Input value={subject} onChange={e => setSubject(e.target.value)} placeholder="Předmět..." data-testid="email-subject-input" />
            </div>
            <div>
              <Label>Oslovení</Label>
              <Input value={greeting} onChange={e => setGreeting(e.target.value)} placeholder="Dobrý den," />
            </div>
            <div>
              <Label>Úvodní text</Label>
              <Textarea value={introText} onChange={e => setIntroText(e.target.value)} rows={3} placeholder="Rádi bychom Vám představili..." />
            </div>
            <div className="bg-slate-50 rounded-lg p-3 border">
              <div className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                <Info className="w-3 h-3" /> Systémem generovaný blok — seznam programů
              </div>
              {selectedPrograms.map(p => (
                <div key={p.id} className="bg-white rounded border p-2 mb-1.5 text-sm">
                  <strong>{p.name_cs || p.name}</strong>
                  <span className="text-slate-500 ml-2">{p.duration} min</span>
                  <div className="flex gap-1 mt-0.5">
                    {(p.target_groups || []).map(tg => (
                      <Badge key={tg} variant="outline" className="text-xs">{TG_LABELS[tg] || tg}</Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div>
              <Label>Závěrečný text</Label>
              <Textarea value={closingText} onChange={e => setClosingText(e.target.value)} rows={2} placeholder="Budeme rádi za Váš zájem..." />
            </div>
            <div>
              <Label>Podpis</Label>
              <Textarea value={signature} onChange={e => setSignature(e.target.value)} rows={2} placeholder="S pozdravem..." />
            </div>
          </div>
        )}

        {/* STEP 4: Summary & Send */}
        {step === 4 && (
          <div className="space-y-4">
            <div className="bg-slate-50 rounded-lg p-4 space-y-3">
              <h3 className="font-semibold text-slate-800">Souhrn kampaně</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><strong>Název:</strong> {campaignName}</div>
                <div><strong>Typ:</strong> {campaignType === 'single_program' ? 'Jednotlivý program' : campaignType === 'seasonal' ? 'Sezónní nabídka' : 'Vlastní'}</div>
                <div><strong>Programů:</strong> {selectedProgramIds.length}</div>
                <div><strong>Příjemců:</strong> {preview?.stats?.total_contacts || '—'}</div>
                <div><strong>Režim:</strong> {MODE_LABELS[recipientMode]}</div>
                <div><strong>Předmět:</strong> {subject}</div>
              </div>
            </div>

            {preview?.warnings?.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                <AlertTriangle className="w-4 h-4 inline mr-1" />
                {preview.warnings.join(' ')}
              </div>
            )}

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
              <Info className="w-4 h-4 inline mr-1" />
              Po odeslání se kampaň zpracuje na pozadí. Emaily budou odeslány postupně.
              Stav odesílání uvidíte v archivu kampaní.
            </div>
          </div>
        )}

        {/* Footer navigation */}
        <DialogFooter className="flex justify-between gap-2 pt-4 border-t">
          <div className="flex gap-2">
            {step > 1 && (
              <Button variant="outline" onClick={() => setStep(step - 1)} data-testid="wizard-back-btn">
                <ChevronLeft className="w-4 h-4 mr-1" /> Zpět
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={saveDraft} disabled={saving} data-testid="save-draft-btn">
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Save className="w-4 h-4 mr-1" />}
              Uložit koncept
            </Button>
            {step < 4 ? (
              <Button onClick={() => {
                if (step === 1 && (selectedProgramIds.length === 0 || !campaignName.trim())) {
                  toast.error('Vyplňte název a vyberte programy');
                  return;
                }
                if (step === 2 && preview && preview.recipients.length === 0) {
                  toast.error('Žádní příjemci k odeslání');
                  return;
                }
                if (step === 3 && !subject.trim()) {
                  toast.error('Vyplňte předmět emailu');
                  return;
                }
                setStep(step + 1);
              }} data-testid="wizard-next-btn">
                Další <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            ) : (
              <Button onClick={sendCampaign} disabled={sending} className="bg-green-600 hover:bg-green-700" data-testid="send-campaign-btn">
                {sending ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Send className="w-4 h-4 mr-1" />}
                Odeslat kampaň
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default MailingsPage;
