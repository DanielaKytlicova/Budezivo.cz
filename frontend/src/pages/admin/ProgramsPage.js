import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Switch } from '../../components/ui/switch';
import { Checkbox } from '../../components/ui/checkbox';
import { Plus, ArrowLeft, Clock, Users, MoreVertical, Copy, Archive, Trash2, Link as LinkIcon, Mail, ShieldAlert, Star, AlertTriangle, FileText } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ProgramMailingTab } from '../../components/admin/ProgramMailingTab.jsx';
import { ProgramCollisionTab } from '../../components/admin/ProgramCollisionTab';
import { ProgramFeedbackTab } from '../../components/admin/ProgramFeedbackTab';
import { ProgramUrlModal } from '../../components/admin/ProgramUrlModal';
import { API } from '../../config/api';

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
  { value: 'gym_14_18', label: 'Gymnázium (14-18 let)' },
  { value: 'adults', label: 'Dospělí' },
  { value: 'all', label: 'Všechny věkové skupiny' },
];

const TARIFFS = [
  { value: 'free', label: 'Zdarma' },
  { value: 'paid', label: 'Placený' },
];

const getDefaultFormData = () => ({
  name_cs: '',
  name_en: '',
  description_cs: '',
  description_en: '',
  target_group: 'schools',
  target_groups: [],  // New: multiple target groups
  duration: 90,
  max_capacity: 20,
  min_capacity: 5,
  price: 0,
  tariff: 'free',
  pricing_info: '',
  image_url: null,
  requires_approval: false,
  is_published: true,
  is_in_catalog: false,
  send_email_notification: true,
  status: 'active',
  available_days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
  time_blocks: ['09:00'],
  start_date: '',
  end_date: '',
  min_days_before_booking: 7,
  max_days_before_booking: 180,
  preparation_time: 10,
  cleanup_time: 30,
  age_group: 'zs1_7_12',
  allow_parallel: false,
  collision_resources: [],
  blocked_program_ids: [],
  room_id: null,
  feedback_enabled: true,
  feedback_questions: [],
  collision_lecturer_ids: [],
});

export const ProgramsPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingProgram, setEditingProgram] = useState(null);
  const [activeTab, setActiveTab] = useState('detail');
  const [formData, setFormData] = useState(getDefaultFormData());
  const [openMenu, setOpenMenu] = useState(null);
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [institutionData, setInstitutionData] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomCapacity, setNewRoomCapacity] = useState('');
  const [isPro, setIsPro] = useState(false);
  const [programPhotosEnabled, setProgramPhotosEnabled] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [showValidationDialog, setShowValidationDialog] = useState(false);
  const [teamMembers, setTeamMembers] = useState([]);

  useEffect(() => {
    fetchPrograms();
    fetchInstitutionData();
    fetchRooms();
    fetchPlanStatus();
    fetchTeamMembers();
    fetchProgramPhotosAccess();
  }, []);

  const fetchPrograms = async () => {
    try {
      const response = await axios.get(`${API}/programs`);
      setPrograms(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      toast.error(t('common.error'));
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchInstitutionData = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setInstitutionData(response.data);
    } catch (error) {
      console.error('Failed to fetch institution data');
    }
  };

  const fetchRooms = async () => {
    try {
      const response = await axios.get(`${API}/rooms`);
      setRooms(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to fetch rooms');
    }
  };

  const fetchPlanStatus = async () => {
    try {
      const response = await axios.get(`${API}/plan/status`);
      setIsPro(response.data?.is_pro || false);
    } catch (error) {
      console.error('Failed to fetch plan status');
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API}/team`);
      setTeamMembers(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to fetch team members');
    }
  };

  const fetchProgramPhotosAccess = async () => {
    try {
      const response = await axios.get(`${API}/programs/features/check-access`);
      setProgramPhotosEnabled(!!response.data?.program_photos);
    } catch (error) {
      setProgramPhotosEnabled(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!editingProgram?.id) {
      toast.error('Nejdříve uložte program, pak můžete nahrát fotografii.');
      return;
    }
    const formDataFile = new FormData();
    formDataFile.append('file', file);
    try {
      setUploadingImage(true);
      const res = await axios.post(
        `${API}/programs/${editingProgram.id}/image/upload`,
        formDataFile,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      const newUrl = res.data?.image_url;
      setFormData((prev) => ({ ...prev, image_url: newUrl }));
      setEditingProgram((prev) => (prev ? { ...prev, image_url: newUrl } : prev));
      fetchPrograms();
      toast.success('Fotografie nahrána');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nahrání selhalo');
    } finally {
      setUploadingImage(false);
      e.target.value = '';
    }
  };

  const handleImageDelete = async () => {
    if (!editingProgram?.id) return;
    if (!window.confirm('Odstranit fotografii z programu?')) return;
    try {
      await axios.delete(`${API}/programs/${editingProgram.id}/image`);
      setFormData((prev) => ({ ...prev, image_url: null }));
      setEditingProgram((prev) => (prev ? { ...prev, image_url: null } : prev));
      fetchPrograms();
      toast.success('Fotografie odstraněna');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Odstranění selhalo');
    }
  };


  const createRoom = async () => {
    if (!newRoomName.trim()) return;
    try {
      await axios.post(`${API}/rooms`, { 
        name: newRoomName.trim(),
        capacity: newRoomCapacity ? parseInt(newRoomCapacity) : null 
      });
      setNewRoomName('');
      setNewRoomCapacity('');
      await fetchRooms();
      toast.success('Místnost vytvořena');
    } catch (error) {
      toast.error('Chyba při vytváření místnosti');
    }
  };

  const deleteRoom = async (roomId) => {
    try {
      await axios.delete(`${API}/rooms/${roomId}`);
      await fetchRooms();
      toast.success('Místnost smazána');
    } catch (error) {
      toast.error('Chyba při mazání místnosti');
    }
  };

  const openUrlGenerator = () => {
    setShowUrlModal(true);
  };

  // --- Time Block Validation ---
  const timeToMin = (t) => {
    const [h, m] = t.split(':').map(Number);
    return h * 60 + m;
  };

  const minToTime = (m) => {
    return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
  };

  const validateTimeBlocks = () => {
    const warnings = [];
    const duration = parseInt(formData.duration) || 60;
    const cleanupTime = parseInt(formData.cleanup_time) || 0;
    const prepTime = parseInt(formData.preparation_time) || 0;
    const blocks = (formData.time_blocks || []).filter(b => b && b.trim());

    // Parse blocks into [start, end] ranges
    const ranges = blocks.map(block => {
      const trimmed = block.trim();
      if (trimmed.includes('-')) {
        const parts = trimmed.split('-');
        return { start: timeToMin(parts[0].trim()), end: timeToMin(parts[1].trim()), raw: trimmed };
      } else {
        const start = timeToMin(trimmed);
        return { start, end: start + duration, raw: trimmed };
      }
    }).filter(r => !isNaN(r.start) && !isNaN(r.end));

    // Sort by start time
    ranges.sort((a, b) => a.start - b.start);

    // Check overlaps between consecutive slots
    for (let i = 0; i < ranges.length - 1; i++) {
      const current = ranges[i];
      const next = ranges[i + 1];

      // Direct overlap: current end > next start
      if (current.end > next.start) {
        warnings.push({
          type: 'overlap',
          severity: 'warning',
          message: `Blok ${current.raw} (končí ${minToTime(current.end)}) se překrývá s blokem ${next.raw} (začíná ${minToTime(next.start)}). Při plné kapacitě by si rezervace vzájemně ubíraly místo.`
        });
      }

      // Cleanup time collision: current end + cleanup > next start
      if (cleanupTime > 0 && current.end + cleanupTime > next.start && current.end <= next.start) {
        const gap = next.start - current.end;
        warnings.push({
          type: 'cleanup',
          severity: 'warning',
          message: `Mezi bloky ${current.raw} a ${next.raw} je mezera jen ${gap} min, ale úklid trvá ${cleanupTime} min. Další blok by mohl začít nejdříve v ${minToTime(current.end + cleanupTime)}.`,
          suggestion: `Snížit dobu úklidu na ${gap} min nebo posunout další blok na ${minToTime(current.end + cleanupTime)}.`
        });
      }

      // Preparation time collision: next start - prep < current end
      if (prepTime > 0 && next.start - prepTime < current.end && current.end <= next.start) {
        warnings.push({
          type: 'preparation',
          severity: 'info',
          message: `Příprava dalšího bloku (${prepTime} min před ${next.raw}) by začala v ${minToTime(next.start - prepTime)}, kdy ještě probíhá předchozí blok nebo úklid.`
        });
      }
    }

    return warnings;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Run validation
    const warnings = validateTimeBlocks();
    if (warnings.length > 0) {
      setValidationWarnings(warnings);
      setShowValidationDialog(true);
      return;
    }
    
    await doSubmit();
  };

  const doSubmit = async () => {
    try {
      const submitData = {
        ...formData,
        age_group: formData.target_group,
      };
      if (editingProgram) {
        await axios.put(`${API}/programs/${editingProgram.id}`, submitData);
        toast.success('Program byl úspěšně aktualizován');
      } else {
        await axios.post(`${API}/programs`, submitData);
        toast.success('Program byl úspěšně vytvořen');
      }
      setShowDialog(false);
      resetForm();
      fetchPrograms();
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Opravdu chcete smazat tento program?')) return;
    try {
      await axios.delete(`${API}/programs/${id}`);
      toast.success('Program byl smazán');
      fetchPrograms();
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const handleDownloadPdfReport = async (program) => {
    try {
      const response = await axios.get(`${API}/programs/${program.id}/archive-report`, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const safe = (program.name_cs || 'report').replace(/[^\p{L}\p{N}_-]+/gu, '_').slice(0, 50);
      link.setAttribute('download', `archive_report_${safe}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('PDF report stažen');
    } catch (error) {
      const d = error.response?.data;
      toast.error(typeof d === 'string' ? d : (d?.detail?.message_cs || d?.detail || 'Chyba při stahování PDF'));
    }
  };

  const handleArchive = async (program) => {
    try {
      await axios.post(`${API}/programs/${program.id}/archive`, {
        reason: 'Ruční archivace'
      });
      toast.success('Program byl archivován');
      fetchPrograms();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    }
    setOpenMenu(null);
  };

  const handleDuplicate = async (program) => {
    try {
      const newProgram = { ...program };
      delete newProgram.id;
      delete newProgram.created_at;
      newProgram.name_cs = `${program.name_cs} (kopie)`;
      newProgram.name_en = `${program.name_en} (copy)`;
      await axios.post(`${API}/programs`, newProgram);
      toast.success('Program byl zduplikován');
      fetchPrograms();
    } catch (error) {
      toast.error(t('common.error'));
    }
    setOpenMenu(null);
  };

  const resetForm = () => {
    setFormData(getDefaultFormData());
    setEditingProgram(null);
    setActiveTab('detail');
  };

  const handleEdit = (program) => {
    setEditingProgram(program);
    // Convert legacy single target_group to target_groups array
    let targetGroups = program.target_groups || [];
    if (targetGroups.length === 0 && program.target_group) {
      targetGroups = [program.target_group];
    }
    if (targetGroups.length === 0 && program.age_group) {
      targetGroups = [program.age_group];
    }
    // Convert ISO datetime strings to YYYY-MM-DD format for date inputs
    const formatDateForInput = (dateStr) => {
      if (!dateStr) return '';
      try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return '';
        return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
      } catch {
        return '';
      }
    };
    setFormData({
      ...getDefaultFormData(),
      ...program,
      target_groups: targetGroups,
      target_group: program.target_group || program.age_group || 'schools',
      start_date: formatDateForInput(program.start_date),
      end_date: formatDateForInput(program.end_date),
      allow_parallel: program.allow_parallel || false,
      collision_resources: program.collision_resources || [],
      blocked_program_ids: program.blocked_program_ids || [],
      room_id: program.room_id || null,
      feedback_enabled: program.feedback_enabled !== false,
      feedback_questions: program.feedback_questions || [],
      collision_lecturer_ids: program.collision_lecturer_ids || [],
    });
    setActiveTab('detail');
    setShowDialog(true);
  };

  const handleCreate = () => {
    resetForm();
    setShowDialog(true);
  };

  const toggleDay = (day) => {
    setFormData(prev => ({
      ...prev,
      available_days: prev.available_days.includes(day)
        ? prev.available_days.filter(d => d !== day)
        : [...prev.available_days, day]
    }));
  };

  const addTimeBlock = () => {
    setFormData(prev => ({
      ...prev,
      time_blocks: [...prev.time_blocks, '09:00']
    }));
  };

  const removeTimeBlock = (index) => {
    setFormData(prev => ({
      ...prev,
      time_blocks: prev.time_blocks.filter((_, i) => i !== index)
    }));
  };

  const updateTimeBlock = (index, value) => {
    setFormData(prev => ({
      ...prev,
      time_blocks: prev.time_blocks.map((block, i) => i === index ? value : block)
    }));
  };

  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'active': return 'bg-slate-800 text-white';
      case 'concept': return 'bg-gray-200 text-gray-700';
      case 'archived': return 'bg-gray-400 text-white';
      default: return 'bg-gray-200 text-gray-700';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'active': return 'aktivní';
      case 'concept': return 'koncept';
      case 'archived': return 'archivováno';
      default: return status;
    }
  };

  const getTargetGroupLabel = (group) => {
    const found = TARGET_GROUPS.find(g => g.value === group);
    return found ? found.label : 'Školy a veřejnost';
  };

  const getTargetGroupsLabel = (groups, fallbackGroup) => {
    // Use target_groups if available, otherwise fall back to single target_group/age_group
    const effectiveGroups = (groups && groups.length > 0) ? groups : (fallbackGroup ? [fallbackGroup] : []);
    
    if (effectiveGroups.length === 0) return 'Neurčeno';
    if (effectiveGroups.length === 1) return getTargetGroupLabel(effectiveGroups[0]);
    if (effectiveGroups.includes('all')) return 'Všechny věkové skupiny';
    
    // Show first 2 groups + count of remaining
    const labels = effectiveGroups.slice(0, 2).map(g => {
      const found = TARGET_GROUPS.find(tg => tg.value === g);
      // Shorter labels for list view
      const shortLabels = {
        'ms_3_6': 'MŠ',
        'zs1_7_12': 'ZŠ I.',
        'zs2_12_15': 'ZŠ II.',
        'ss_14_18': 'SŠ',
        'gym_14_18': 'Gym.',
        'adults': 'Dospělí',
      };
      return shortLabels[g] || (found ? found.label : g);
    });
    if (effectiveGroups.length > 2) {
      return `${labels.join(', ')} +${effectiveGroups.length - 2}`;
    }
    return labels.join(', ');
  };

  const programsCount = programs.filter(p => p.status !== 'archived').length;
  const freeLimit = 3;

  const renderProgramList = () => (
    <div className="space-y-6">
      {/* Header with limit info */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl md:text-3xl font-bold text-slate-900">Programy</h1>
        <Button 
          data-testid="create-program-button" 
          onClick={handleCreate}
          className="bg-slate-800 text-white hover:bg-slate-700 rounded-full w-12 h-12 p-0 fixed bottom-24 md:bottom-8 right-4 md:relative md:w-auto md:h-auto md:px-4 md:py-2 md:rounded-md shadow-lg md:shadow-none"
        >
          <Plus className="w-5 h-5 md:mr-2" />
          <span className="hidden md:inline">Nový program</span>
        </Button>
      </div>

      {/* Plan limit banner with URL generator */}
      <Card className="p-4 bg-gray-50 border-gray-200">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <p className="text-sm text-gray-600">
              Máte ještě <span className="font-semibold">{Math.max(0, freeLimit - programsCount)}</span> volné místo pro bezúplatný tarif.
            </p>
            <button className="text-sm font-medium text-slate-800 hover:underline">
              Navýšit tarif
            </button>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => navigate('/admin/archive')}
              className="shrink-0"
              data-testid="archive-link-btn"
            >
              <Archive className="w-4 h-4 mr-2" />
              Archiv
            </Button>
            <Button
              variant="outline"
              onClick={openUrlGenerator}
              className="shrink-0"
              data-testid="generate-url-btn"
            >
              <LinkIcon className="w-4 h-4 mr-2" />
              Generovat URL pro web
            </Button>
          </div>
        </div>
      </Card>

      {/* Programs grid */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto"></div>
        </div>
      ) : programs.filter(p => p.status !== 'archived').length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-gray-500">Zatím nemáte žádné programy</p>
          <Button onClick={handleCreate} className="mt-4 bg-slate-800 text-white">
            <Plus className="w-4 h-4 mr-2" />
            Vytvořit první program
          </Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {Array.isArray(programs) && programs.filter(p => p.status !== 'archived').map((program) => (
            <Card 
              key={program.id} 
              className="p-4 md:p-6 relative" 
              data-testid={`program-card-${program.id}`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1 cursor-pointer" onClick={() => handleEdit(program)}>
                  <h3 className="text-lg font-semibold text-slate-900 mb-1">{program.name_cs}</h3>
                  <p className="text-sm text-gray-500 mb-3 line-clamp-1">{program.description_cs}</p>
                  
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                      {getTargetGroupsLabel(program.target_groups, program.target_group || program.age_group)}
                    </span>
                    <span className={`px-2 py-1 text-xs rounded ${getStatusBadgeColor(program.status)}`}>
                      {getStatusLabel(program.status)}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {program.duration} min.
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      Max {program.max_capacity || program.capacity || 30}
                    </span>
                  </div>
                </div>

                {/* Menu button */}
                <div className="relative">
                  <button
                    onClick={() => setOpenMenu(openMenu === program.id ? null : program.id)}
                    className="p-2 hover:bg-gray-100 rounded-full"
                    data-testid={`program-menu-${program.id}`}
                  >
                    <MoreVertical className="w-5 h-5 text-gray-500" />
                  </button>
                  
                  {openMenu === program.id && (
                    <div className="absolute right-0 top-10 bg-white shadow-lg rounded-lg border z-10 min-w-[160px]">
                      <button
                        onClick={() => { handleEdit(program); setOpenMenu(null); }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                      >
                        Upravit
                      </button>
                      <button
                        onClick={() => handleDuplicate(program)}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                        data-testid={`duplicate-program-${program.id}`}
                      >
                        <Copy className="w-4 h-4" />
                        Duplikovat
                      </button>
                      <button
                        onClick={() => { handleDownloadPdfReport(program); setOpenMenu(null); }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                        data-testid={`pdf-report-${program.id}`}
                      >
                        <FileText className="w-4 h-4" />
                        Stáhnout PDF report
                      </button>
                      <button
                        onClick={() => handleArchive(program)}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                        data-testid={`archive-program-${program.id}`}
                      >
                        <Archive className="w-4 h-4" />
                        Archivovat
                      </button>
                      <button
                        onClick={() => { handleDelete(program.id); setOpenMenu(null); }}
                        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                        data-testid={`delete-program-${program.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                        Smazat
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 mt-4 pt-4 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/admin/mailings?program=${program.id}&name=${encodeURIComponent(program.name_cs)}`)}
                  className="flex-1"
                  data-testid={`send-offer-${program.id}`}
                >
                  <Mail className="w-4 h-4 mr-1" />
                  Rozeslat nabídku
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDuplicate(program)}
                  className="flex-1"
                >
                  Duplikovat
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );

  const renderDetailTab = () => (
    <div className="space-y-6">
      {/* Základní informace */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Základní informace</h3>
        
        <div>
          <Label className="text-gray-500 text-sm">Název programu</Label>
          <Input
            data-testid="program-name-cs"
            value={formData.name_cs}
            onChange={(e) => setFormData({ ...formData, name_cs: e.target.value })}
            placeholder="Seznam se s galerií"
            className="mt-1"
          />
        </div>

        <div>
          <Label className="text-gray-500 text-sm">Popis</Label>
          <Textarea
            data-testid="program-description-cs"
            value={formData.description_cs}
            onChange={(e) => setFormData({ ...formData, description_cs: e.target.value })}
            placeholder="Doprovodný program provádí malé návštěvníky..."
            className="mt-1"
            rows={3}
          />
        </div>

        <div>
          <Label className="text-gray-500 text-sm mb-2 block">Cílové skupiny</Label>
          <div className="space-y-2 mt-1">
            {TARGET_GROUPS.map(group => (
              <div key={group.value} className="flex items-center space-x-2">
                <Checkbox
                  id={`target-${group.value}`}
                  checked={(formData.target_groups || []).includes(group.value)}
                  onCheckedChange={(checked) => {
                    const currentGroups = formData.target_groups || [];
                    let newGroups;
                    if (checked) {
                      // If selecting "all", clear others
                      if (group.value === 'all') {
                        newGroups = ['all'];
                      } else {
                        // Remove "all" if present and add the new group
                        newGroups = [...currentGroups.filter(g => g !== 'all'), group.value];
                      }
                    } else {
                      newGroups = currentGroups.filter(g => g !== group.value);
                    }
                    setFormData({ 
                      ...formData, 
                      target_groups: newGroups,
                      // Legacy compatibility
                      target_group: newGroups[0] || 'schools',
                      age_group: newGroups[0] || 'zs1_7_12'
                    });
                  }}
                  data-testid={`target-group-${group.value}`}
                />
                <label
                  htmlFor={`target-${group.value}`}
                  className="text-sm cursor-pointer select-none"
                >
                  {group.label}
                </label>
              </div>
            ))}
          </div>
          {(formData.target_groups || []).length === 0 && (
            <p className="text-xs text-amber-600 mt-2">Vyberte alespoň jednu cílovou skupinu</p>
          )}
        </div>
      </Card>

      {/* Kapacita a trvání */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Kapacita a trvání</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-gray-500 text-sm">Doba trvání (min)</Label>
            <Input
              type="number"
              data-testid="program-duration"
              value={formData.duration}
              onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) || 60 })}
              className="mt-1"
            />
          </div>
          <div>
            <Label className="text-gray-500 text-sm">Maximální kapacita</Label>
            <Input
              type="number"
              data-testid="program-max-capacity"
              value={formData.max_capacity}
              onChange={(e) => setFormData({ ...formData, max_capacity: parseInt(e.target.value) || 30 })}
              className="mt-1"
            />
          </div>
        </div>

        <div>
          <Label className="text-gray-500 text-sm">Minimum účastníků</Label>
          <Input
            type="number"
            data-testid="program-min-capacity"
            value={formData.min_capacity}
            onChange={(e) => setFormData({ ...formData, min_capacity: parseInt(e.target.value) || 5 })}
            placeholder="min. 5 osob"
            className="mt-1"
          />
        </div>
      </Card>

      {/* Cena (informativní) */}
      <Card className="p-4 md:p-6 space-y-3">
        <div>
          <h3 className="font-semibold text-slate-900">Cena pro účastníky</h3>
          <p className="text-xs text-slate-500 mt-1">
            Informativní text pro školy / rodiče. Peníze <strong>nevybíráme online</strong> — slouží pouze
            k zobrazení v nabídce a k propsání do potvrzovacího e-mailu rezervace.
          </p>
        </div>
        <div>
          <Label className="text-gray-500 text-sm">Text o ceně</Label>
          <Input
            data-testid="program-pricing-info"
            value={formData.pricing_info || ''}
            onChange={(e) => setFormData({ ...formData, pricing_info: e.target.value })}
            placeholder="např. 30,-/dítě – pedagog zdarma"
            className="mt-1"
            maxLength={200}
          />
          <p className="text-xs text-slate-400 mt-1">
            Pokud ponecháte prázdné, v nabídce ani v mailu se žádná informace o ceně nezobrazí.
          </p>
        </div>
      </Card>

      {/* Fotografie programu (feature-flagged: program_photos) */}
      {programPhotosEnabled && (
        <Card className="p-4 md:p-6 space-y-3" data-testid="program-photo-card">
          <div>
            <h3 className="font-semibold text-slate-900">Fotografie programu</h3>
            <p className="text-xs text-slate-500 mt-1">
              Hlavní obrázek programu zobrazený na veřejné rezervační stránce. Doporučený formát:
              {' '}<strong>1200×800 px</strong>, PNG / JPG / WebP, max 5&nbsp;MB.
            </p>
          </div>

          {formData.image_url ? (
            <div className="flex flex-col md:flex-row gap-4 items-start">
              <img
                src={`${process.env.REACT_APP_BACKEND_URL}${formData.image_url}`}
                alt="Náhled fotografie programu"
                className="w-full md:w-64 h-40 object-cover rounded-lg border border-slate-200"
                data-testid="program-photo-preview"
              />
              <div className="flex flex-col gap-2">
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/webp,image/svg+xml,image/gif"
                    className="hidden"
                    onChange={handleImageUpload}
                    disabled={uploadingImage}
                    data-testid="program-photo-replace-input"
                  />
                  <span className="inline-flex items-center px-3 py-2 rounded-md border border-slate-300 text-sm hover:bg-slate-50">
                    {uploadingImage ? 'Nahrávám...' : 'Vyměnit fotografii'}
                  </span>
                </label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleImageDelete}
                  className="text-red-600 hover:text-red-700"
                  data-testid="program-photo-delete-btn"
                >
                  <Trash2 className="w-4 h-4 mr-1" /> Odstranit
                </Button>
              </div>
            </div>
          ) : editingProgram?.id ? (
            <label
              className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg py-10 px-4 cursor-pointer hover:border-slate-400 hover:bg-slate-50 transition"
              data-testid="program-photo-upload-zone"
            >
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp,image/svg+xml,image/gif"
                className="hidden"
                onChange={handleImageUpload}
                disabled={uploadingImage}
                data-testid="program-photo-upload-input"
              />
              <div className="text-center">
                <p className="text-sm text-slate-700 font-medium">
                  {uploadingImage ? 'Nahrávám...' : 'Klikněte pro nahrání fotografie'}
                </p>
                <p className="text-xs text-slate-500 mt-1">PNG, JPG, WebP, max 5 MB</p>
              </div>
            </label>
          ) : (
            <div className="rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-sm px-3 py-2">
              Nejprve uložte program — pak budete moci nahrát fotografii.
            </div>
          )}
        </Card>
      )}

      {/* Další nastavení */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Další nastavení</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Vyžaduje schválení</p>
              <p className="text-sm text-gray-500">Rezervace vyžaduje schválení před finálním potvrzením.</p>
            </div>
            <Switch
              data-testid="program-requires-approval"
              checked={formData.requires_approval}
              onCheckedChange={(checked) => setFormData({ ...formData, requires_approval: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Zveřejnit program</p>
              <p className="text-sm text-gray-500">Všichni návštěvníci uvidí tento program v online nabídce.</p>
            </div>
            <Switch
              data-testid="program-is-published"
              checked={formData.is_published}
              onCheckedChange={(checked) => setFormData({ ...formData, is_published: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Zobrazit v katalogu „Programy pro školy"</p>
              <p className="text-sm text-gray-500">
                Program se objeví ve veřejném katalogu na <code>/programy-pro-skoly</code>. Vhodné pro programy nabízené školám.
              </p>
            </div>
            <Switch
              data-testid="program-is-in-catalog"
              checked={!!formData.is_in_catalog}
              onCheckedChange={(checked) => setFormData({ ...formData, is_in_catalog: checked })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Odeslat upozornění mailem</p>
              <p className="text-sm text-gray-500">Automaticky odešle mailem upozornění 2 pracovní dny před návštěvou.</p>
            </div>
            <Switch
              data-testid="program-email-notification"
              checked={formData.send_email_notification}
              onCheckedChange={(checked) => setFormData({ ...formData, send_email_notification: checked })}
            />
          </div>
        </div>
      </Card>

      {/* Status */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Status</h3>
        
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="status"
              value="active"
              checked={formData.status === 'active'}
              onChange={() => setFormData({ ...formData, status: 'active' })}
              className="w-5 h-5 text-slate-800"
              data-testid="program-status-active"
            />
            <div>
              <p className="font-medium text-slate-900">Aktivní</p>
              <p className="text-sm text-gray-500">Dostupný pro rezervace</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="status"
              value="concept"
              checked={formData.status === 'concept'}
              onChange={() => setFormData({ ...formData, status: 'concept' })}
              className="w-5 h-5"
              data-testid="program-status-concept"
            />
            <div>
              <p className="font-medium text-slate-900">Koncept</p>
              <p className="text-sm text-gray-500">Návštěvník program neuvidí</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="status"
              value="archived"
              checked={formData.status === 'archived'}
              onChange={() => setFormData({ ...formData, status: 'archived' })}
              className="w-5 h-5"
              data-testid="program-status-archived"
            />
            <div>
              <p className="font-medium text-slate-900">Archivovat</p>
              <p className="text-sm text-gray-500">Program nebude viditelný pro veřejnost</p>
            </div>
          </label>
        </div>
      </Card>
    </div>
  );

  const renderSettingsTab = () => (
    <div className="space-y-6">
      {/* Nabízené dny */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Nabízené dny</h3>
        <div className="flex flex-wrap gap-2">
          {DAYS.map(day => (
            <button
              key={day.key}
              type="button"
              data-testid={`program-day-${day.key}`}
              onClick={() => toggleDay(day.key)}
              className={`w-10 h-10 rounded-lg border text-sm font-medium transition-colors ${
                formData.available_days.includes(day.key)
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
              }`}
            >
              {day.label}
            </button>
          ))}
        </div>
      </Card>

      {/* Časové bloky */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Časové bloky</h3>
        <p className="text-sm text-gray-500">Zadejte čas ve formátu HH:MM (např. 09:00, 14:30)</p>
        <div className="space-y-3">
          {(formData.time_blocks || []).map((block, index) => (
            <div key={index} className="flex items-center gap-3">
              <Switch
                checked={true}
                onCheckedChange={() => {}}
              />
              <div className="flex-1 relative">
                <Input
                  type="text"
                  value={block}
                  onChange={(e) => {
                    let val = e.target.value;
                    // Auto-format: add colon after 2 digits
                    if (val.length === 2 && !val.includes(':') && /^\d{2}$/.test(val)) {
                      val = val + ':';
                    }
                    // Validate format HH:MM
                    if (val === '' || /^[0-2]?[0-9]?:?[0-5]?[0-9]?$/.test(val)) {
                      updateTimeBlock(index, val);
                    }
                  }}
                  onBlur={(e) => {
                    // Normalize on blur (e.g., "9:00" -> "09:00")
                    let val = e.target.value;
                    if (/^\d{1}:\d{2}$/.test(val)) {
                      updateTimeBlock(index, '0' + val);
                    } else if (/^\d{2}:\d{1}$/.test(val)) {
                      updateTimeBlock(index, val + '0');
                    }
                  }}
                  placeholder="09:00"
                  maxLength={5}
                  className="pr-10 font-mono"
                  data-testid={`program-time-block-${index}`}
                />
                <input
                  type="time"
                  value={block}
                  onChange={(e) => updateTimeBlock(index, e.target.value)}
                  className="absolute right-0 top-0 h-full w-10 opacity-0 cursor-pointer"
                  title="Vybrat z hodin"
                  data-testid={`program-time-picker-${index}`}
                />
                <Clock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
              {formData.time_blocks.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeTimeBlock(index)}
                  className="text-gray-400 hover:text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addTimeBlock}
            className="w-full py-2 border border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-gray-400 hover:text-gray-600"
            data-testid="program-add-time-block"
          >
            Přidat další časový blok
          </button>
        </div>
      </Card>

      {/* Termín */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Termín</h3>
        <div className="space-y-4">
          <div>
            <Label className="text-gray-500 text-sm">Začátek programu</Label>
            <Input
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              className="mt-1"
              data-testid="program-start-date"
            />
          </div>
          <div>
            <Label className="text-gray-500 text-sm">Konec programu</Label>
            <Input
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              className="mt-1"
              data-testid="program-end-date"
            />
          </div>
        </div>
      </Card>

      {/* Parametry rezervace */}
      <Card className="p-4 md:p-6 space-y-4 bg-blue-50 border-blue-100">
        <h3 className="font-semibold text-slate-900">Parametry rezervace</h3>
        
        <div>
          <Label className="text-gray-500 text-sm">Minimální počet dnů před rezervací (dní)</Label>
          <Input
            type="number"
            value={formData.min_days_before_booking}
            onChange={(e) => setFormData({ ...formData, min_days_before_booking: parseInt(e.target.value) || 7 })}
            className="mt-1 bg-white"
            data-testid="program-min-days-before"
          />
        </div>

        <div>
          <Label className="text-gray-500 text-sm">Maximální počet dnů před rezervací (dní)</Label>
          <Input
            type="number"
            value={formData.max_days_before_booking}
            onChange={(e) => setFormData({ ...formData, max_days_before_booking: parseInt(e.target.value) || 180 })}
            className="mt-1 bg-white"
            data-testid="program-max-days-before"
          />
        </div>

        <div>
          <Label className="text-gray-500 text-sm">Potřebná doba na přípravu programu (min.)</Label>
          <Input
            type="number"
            value={formData.preparation_time}
            onChange={(e) => setFormData({ ...formData, preparation_time: parseInt(e.target.value) || 10 })}
            className="mt-1 bg-white"
            data-testid="program-preparation-time"
          />
        </div>

        <div>
          <Label className="text-gray-500 text-sm">Potřebný čas na úklid programu (min.)</Label>
          <Input
            type="number"
            value={formData.cleanup_time}
            onChange={(e) => setFormData({ ...formData, cleanup_time: parseInt(e.target.value) || 30 })}
            className="mt-1 bg-white"
            data-testid="program-cleanup-time"
          />
        </div>
      </Card>
    </div>
  );




  const renderProgramForm = () => (
    <div className="space-y-4">
      {/* Header with back button */}
      <div className="flex items-center gap-4 mb-4">
        <button 
          onClick={() => setShowDialog(false)}
          className="p-2 hover:bg-gray-100 rounded-lg"
          data-testid="program-back-button"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-semibold text-slate-900">Programy</h2>
      </div>

      {/* Tabs */}
      <div className="flex border-b overflow-x-auto -mx-1 scrollbar-hide">
        <button
          type="button"
          onClick={() => setActiveTab('detail')}
          className={`px-3 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'detail'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-detail"
        >
          Detail
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('settings')}
          className={`px-3 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'settings'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-settings"
        >
          Nastavení
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('collision')}
          className={`px-3 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'collision'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-collision"
        >
          <ShieldAlert className="w-4 h-4 hidden sm:block" />
          Kolize
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('feedback')}
          className={`px-3 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'feedback'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-feedback"
        >
          <Star className="w-4 h-4 hidden sm:block" />
          Zpětná vazba
        </button>
        {editingProgram && (
          <button
            type="button"
            onClick={() => setActiveTab('mailing')}
            className={`px-3 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'mailing'
                ? 'border-slate-800 text-slate-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid="program-tab-mailing"
          >
            <Mail className="w-4 h-4 hidden sm:block" />
            Mailing
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="max-h-[60vh] overflow-y-auto pb-20">
        {activeTab === 'detail' && renderDetailTab()}
        {activeTab === 'settings' && renderSettingsTab()}
        {activeTab === 'collision' && (
          <ProgramCollisionTab
            formData={formData}
            setFormData={setFormData}
            programs={programs}
            editingProgram={editingProgram}
            rooms={rooms}
            newRoomName={newRoomName}
            setNewRoomName={setNewRoomName}
            newRoomCapacity={newRoomCapacity}
            setNewRoomCapacity={setNewRoomCapacity}
            createRoom={createRoom}
            deleteRoom={deleteRoom}
            teamMembers={teamMembers}
          />
        )}
        {activeTab === 'feedback' && (
          <ProgramFeedbackTab
            formData={formData}
            setFormData={setFormData}
            isPro={isPro}
          />
        )}
        {activeTab === 'mailing' && editingProgram && (
          <ProgramMailingTab 
            programId={editingProgram.id} 
            programName={editingProgram.name_cs}
          />
        )}
      </div>

      {/* Fixed footer - only show for detail/settings/collision/feedback tabs */}
      {activeTab !== 'mailing' && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 flex gap-2 md:relative md:border-0 md:p-0 md:mt-4">
          <Button
            onClick={handleSubmit}
            className="flex-1 bg-slate-800 text-white hover:bg-slate-700"
            data-testid="program-save-button"
          >
            <span className="mr-2">💾</span>
            Uložit volby
          </Button>
          {editingProgram && (
            <Button
              type="button"
              variant="outline"
              onClick={() => handleDelete(editingProgram.id)}
              className="text-red-500 border-red-200 hover:bg-red-50"
              data-testid="program-delete-button"
            >
              <Trash2 className="w-5 h-5" />
            </Button>
          )}
        </div>
      )}
    </div>
  );

  return (
    <AdminLayout>
      {!showDialog ? (
        renderProgramList()
      ) : (
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-2xl max-h-[90dvh] sm:max-h-[95vh] overflow-hidden p-0">
            <DialogHeader className="sr-only">
              <DialogTitle>{editingProgram ? 'Upravit program' : 'Nový program'}</DialogTitle>
            </DialogHeader>
            <div className="p-3 sm:p-6 overflow-y-auto max-h-[85dvh] sm:max-h-[90vh]">
              {renderProgramForm()}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* URL Generator Modal */}
      <ProgramUrlModal
        open={showUrlModal}
        onOpenChange={setShowUrlModal}
        programs={programs}
        institutionData={institutionData}
      />

      {/* Time Block Validation Warning Dialog */}
      <Dialog open={showValidationDialog} onOpenChange={setShowValidationDialog}>
        <DialogContent className="max-w-lg" aria-describedby="validation-description">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="w-5 h-5" />
              Upozornění na nastavení časových bloků
            </DialogTitle>
            <p id="validation-description" className="text-sm text-gray-500 mt-2">
              Byly nalezeny potenciální problémy s nastavením časových bloků:
            </p>
          </DialogHeader>

          <div className="space-y-3 py-4 max-h-[40vh] overflow-y-auto">
            {validationWarnings.map((w, i) => (
              <div key={i} className={`p-3 rounded-lg border text-sm ${
                w.type === 'overlap' 
                  ? 'bg-amber-50 border-amber-200' 
                  : w.type === 'cleanup' 
                    ? 'bg-orange-50 border-orange-200'
                    : 'bg-blue-50 border-blue-200'
              }`} data-testid={`validation-warning-${i}`}>
                <div className="flex gap-2">
                  <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${
                    w.type === 'overlap' ? 'text-amber-500' : w.type === 'cleanup' ? 'text-orange-500' : 'text-blue-500'
                  }`} />
                  <div>
                    <p className="text-slate-700">{w.message}</p>
                    {w.suggestion && (
                      <p className="text-xs text-gray-500 mt-1 italic">{w.suggestion}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-3 pt-2 border-t">
            <Button
              variant="outline"
              onClick={() => {
                setShowValidationDialog(false);
                setActiveTab('settings');
              }}
              data-testid="validation-cancel-btn"
            >
              Upravit nastavení
            </Button>
            <Button
              className="bg-amber-600 hover:bg-amber-700 text-white"
              onClick={() => {
                setShowValidationDialog(false);
                doSubmit();
              }}
              data-testid="validation-accept-btn"
            >
              Beru na vědomí
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};
