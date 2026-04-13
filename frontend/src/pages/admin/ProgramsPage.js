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
import { Plus, ArrowLeft, Clock, Users, MoreVertical, Copy, Archive, Trash2, Link as LinkIcon, ExternalLink, Mail, ShieldAlert, Info, User, SlidersHorizontal, Star, MessageSquare, Lock, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ProgramMailingTab } from '../../components/admin/ProgramMailingTab.jsx';
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
  requires_approval: false,
  is_published: true,
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
  const [urlData, setUrlData] = useState(null);
  const [selectedProgramForUrl, setSelectedProgramForUrl] = useState('all');
  const [urlAgeFilters, setUrlAgeFilters] = useState([]);
  const [institutionData, setInstitutionData] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomCapacity, setNewRoomCapacity] = useState('');
  const [isPro, setIsPro] = useState(false);
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [showValidationDialog, setShowValidationDialog] = useState(false);

  const URL_AGE_OPTIONS = [
    { code: 'MS', label: 'MŠ (3-6 let)' },
    { code: 'ZS1', label: 'I. stupeň ZŠ (7-12 let)' },
    { code: 'ZS2', label: 'II. stupeň ZŠ (12-15 let)' },
    { code: 'SS', label: 'SŠ (14-18 let)' },
    { code: 'GYM', label: 'Gymnázium (14-18 let)' },
  ];

  useEffect(() => {
    fetchPrograms();
    fetchInstitutionData();
    fetchRooms();
    fetchPlanStatus();
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
    setSelectedProgramForUrl('all');
    setUrlAgeFilters([]);
    setUrlData(null);
    setShowUrlModal(true);
  };

  const generateUrl = (programId = 'all', ageFilters = []) => {
    if (!institutionData) return;
    
    const baseUrl = "https://budezivo.cz";
    const previewBase = window.location.origin;
    const institutionId = institutionData.institution_id;
    const institutionName = institutionData.institution_name || 'Vaše instituce';
    
    // Build query params
    const params = new URLSearchParams();
    if (programId !== 'all') params.set('program', programId);
    if (ageFilters.length > 0) params.set('age', ageFilters.join(','));
    const queryStr = params.toString() ? `?${params.toString()}` : '';
    const path = `/booking/${institutionId}${queryStr}`;
    
    if (programId === 'all') {
      const url = `${baseUrl}${path}`;
      const filterLabel = ageFilters.length > 0 ? ` (${ageFilters.join(', ')})` : '';
      setUrlData({
        url,
        previewUrl: `${previewBase}${path}`,
        program_name: `Všechny programy${filterLabel}`,
        institution_name: institutionName,
        embed_code: `<a href="${url}" target="_blank">Rezervovat program v ${institutionName}</a>`
      });
    } else {
      const program = programs.find(p => p.id === programId);
      const url = `${baseUrl}${path}`;
      setUrlData({
        url,
        previewUrl: `${previewBase}${path}`,
        program_name: program?.name_cs || 'Program',
        institution_name: institutionName,
        embed_code: `<a href="${url}" target="_blank">Rezervovat: ${program?.name_cs || 'Program'}</a>`
      });
    }
  };

  const handleProgramSelectForUrl = (programId) => {
    setSelectedProgramForUrl(programId);
    generateUrl(programId, urlAgeFilters);
  };

  const toggleUrlAgeFilter = (code) => {
    const newFilters = urlAgeFilters.includes(code)
      ? urlAgeFilters.filter(c => c !== code)
      : [...urlAgeFilters, code];
    setUrlAgeFilters(newFilters);
    generateUrl(selectedProgramForUrl, newFilters);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Zkopírováno do schránky');
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
                  onClick={() => handleDuplicate(program)}
                  className="flex-1"
                >
                  Duplikovat
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleArchive(program)}
                  className="flex-1"
                >
                  Archivovat
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

      {/* Ceník */}
      <Card className="p-4 md:p-6 space-y-4">
        <div className="flex justify-between items-start">
          <h3 className="font-semibold text-slate-900">Ceník</h3>
          <button className="text-sm text-slate-600 underline hover:text-slate-800">
            Chceš k programům přidat i fotografie? Vylepši svůj tarif.
          </button>
        </div>
        
        <div>
          <Label className="text-gray-500 text-sm">Vybraný tarif</Label>
          <Select
            value={formData.tariff}
            onValueChange={(value) => setFormData({ ...formData, tariff: value, price: value === 'free' ? 0 : formData.price })}
          >
            <SelectTrigger className="mt-1" data-testid="program-tariff">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TARIFFS.map(tariff => (
                <SelectItem key={tariff.value} value={tariff.value}>{tariff.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {formData.tariff === 'paid' && (
          <div>
            <Label className="text-gray-500 text-sm">Cena (Kč)</Label>
            <Input
              type="number"
              data-testid="program-price"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
              className="mt-1"
            />
          </div>
        )}
      </Card>

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


  const toggleCollisionResource = (resource) => {
    setFormData(prev => ({
      ...prev,
      collision_resources: prev.collision_resources.includes(resource)
        ? prev.collision_resources.filter(r => r !== resource)
        : [...prev.collision_resources, resource]
    }));
  };

  const toggleBlockedProgram = (programId) => {
    setFormData(prev => ({
      ...prev,
      blocked_program_ids: prev.blocked_program_ids.includes(programId)
        ? prev.blocked_program_ids.filter(id => id !== programId)
        : [...prev.blocked_program_ids, programId]
    }));
  };

  const renderCollisionTab = () => {
    const otherPrograms = programs.filter(p => 
      p.id !== editingProgram?.id && p.status !== 'archived'
    );

    return (
      <div className="space-y-6">
        {/* Section 1: Basic toggle */}
        <Card className="p-4 md:p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900">Paralelní provoz</h3>
              <p className="text-sm text-gray-500 mt-1">
                Určuje, zda se tento program může časově překrývat s jinými programy.
              </p>
            </div>
            <div className="relative group ml-4">
              <Info className="w-4 h-4 text-gray-400 cursor-help" />
              <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                Pokud je paralelní provoz zakázán, program blokuje celý svůj časový slot a žádný jiný program se nemůže v tomto čase rezervovat.
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
            <div>
              <p className="font-medium text-slate-900 text-sm">
                {!formData.allow_parallel 
                  ? 'Nelze paralelně provozovat (překryv zakázán)' 
                  : 'Paralelní provoz povolen'
                }
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {!formData.allow_parallel
                  ? 'Program blokuje svůj časový slot globálně'
                  : 'Program se může překrývat s jinými programy (s omezením)'
                }
              </p>
            </div>
            <Switch
              checked={formData.allow_parallel}
              onCheckedChange={(checked) => setFormData({ ...formData, allow_parallel: checked })}
              data-testid="collision-allow-parallel-toggle"
            />
          </div>
        </Card>

        {/* Sections 2 & 3: Only visible when parallel is allowed */}
        {formData.allow_parallel && (
          <>
            {/* Section 2: Affected resources */}
            <Card className="p-4 md:p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-slate-900">Ovlivněné zdroje</h3>
                <div className="relative group">
                  <Info className="w-4 h-4 text-gray-400 cursor-help" />
                  <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                    Zaškrtněte zdroje, u kterých chcete kontrolovat kolize. Pokud nezaškrtnete nic, program nemá žádná omezení.
                  </div>
                </div>
              </div>
              <p className="text-sm text-gray-500">
                Vyberte, které zdroje chcete kontrolovat při překryvu s jinými programy.
              </p>

              <div className="space-y-3">
                <label 
                  className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                    formData.collision_resources.includes('lecturer')
                      ? 'border-[#4A6FA5] bg-[#4A6FA5]/5'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  data-testid="collision-resource-lecturer"
                >
                  <Checkbox
                    checked={formData.collision_resources.includes('lecturer')}
                    onCheckedChange={() => toggleCollisionResource('lecturer')}
                  />
                  <User className="w-5 h-5 text-[#4A6FA5]" />
                  <div className="flex-1">
                    <p className="font-medium text-slate-900 text-sm">Lektor</p>
                    <p className="text-xs text-gray-500">
                      Kontrola, zda stejný lektor není přiřazen k překrývající se rezervaci
                    </p>
                  </div>
                  <div className="relative group">
                    <Info className="w-4 h-4 text-gray-400 cursor-help" />
                    <div className="absolute right-0 bottom-full mb-2 w-56 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                      Pokud je lektor přiřazen k jinému programu ve stejném čase, nová rezervace bude odmítnuta.
                    </div>
                  </div>
                </label>

                <label 
                  className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                    formData.collision_resources.includes('room')
                      ? 'border-[#4A6FA5] bg-[#4A6FA5]/5'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  data-testid="collision-resource-room"
                >
                  <Checkbox
                    checked={formData.collision_resources.includes('room')}
                    onCheckedChange={() => toggleCollisionResource('room')}
                  />
                  <ShieldAlert className="w-5 h-5 text-[#C4AB86]" />
                  <div className="flex-1">
                    <p className="font-medium text-slate-900 text-sm">Místnost</p>
                    <p className="text-xs text-gray-500">
                      Kontrola, zda není překryv s jinou rezervací ve stejné místnosti
                    </p>
                  </div>
                  <div className="relative group">
                    <Info className="w-4 h-4 text-gray-400 cursor-help" />
                    <div className="absolute right-0 bottom-full mb-2 w-56 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                      Pokud je místnost rezervována pro jiný program ve stejném čase, nová rezervace nebude povolena.
                    </div>
                  </div>
                </label>
              </div>

              {formData.collision_resources.length === 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm text-amber-700">
                    Žádný zdroj není vybrán — program se může překrývat se vším bez omezení.
                  </p>
                </div>
              )}

              {/* Room assignment - visible when room collision is checked */}
              {formData.collision_resources.includes('room') && (
                <div className="space-y-3 pt-3 border-t">
                  <Label className="text-sm font-medium text-slate-700">Přiřazená místnost</Label>
                  <Select 
                    value={formData.room_id || 'none'} 
                    onValueChange={(val) => setFormData({ ...formData, room_id: val === 'none' ? null : val })}
                  >
                    <SelectTrigger data-testid="room-select">
                      <SelectValue placeholder="Vyberte místnost..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Žádná místnost</SelectItem>
                      {rooms.filter(r => r.is_active).map(room => (
                        <SelectItem key={room.id} value={room.id}>
                          {room.name}{room.capacity ? ` (${room.capacity} míst)` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {rooms.length === 0 && (
                    <p className="text-xs text-gray-500">Zatím nemáte žádné místnosti. Vytvořte je níže.</p>
                  )}

                  {/* Inline room creation */}
                  <div className="flex gap-2 items-end">
                    <div className="flex-1">
                      <Input
                        placeholder="Název místnosti..."
                        value={newRoomName}
                        onChange={(e) => setNewRoomName(e.target.value)}
                        className="text-sm"
                        data-testid="new-room-name"
                      />
                    </div>
                    <div className="w-24">
                      <Input
                        placeholder="Kapacita"
                        type="number"
                        value={newRoomCapacity}
                        onChange={(e) => setNewRoomCapacity(e.target.value)}
                        className="text-sm"
                        data-testid="new-room-capacity"
                      />
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      onClick={createRoom}
                      disabled={!newRoomName.trim()}
                      data-testid="create-room-btn"
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>

                  {/* Existing rooms list */}
                  {rooms.length > 0 && (
                    <div className="space-y-1">
                      {rooms.map(room => (
                        <div key={room.id} className="flex items-center justify-between text-xs text-gray-600 px-2 py-1 bg-gray-50 rounded">
                          <span>{room.name}{room.capacity ? ` · ${room.capacity} míst` : ''}</span>
                          <button
                            type="button"
                            onClick={() => deleteRoom(room.id)}
                            className="text-red-400 hover:text-red-600"
                            data-testid={`delete-room-${room.id}`}
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* Section 3: Manual program exclusions */}
            <Card className="p-4 md:p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-slate-900">Ruční omezení mezi programy</h3>
                <div className="relative group">
                  <Info className="w-4 h-4 text-gray-400 cursor-help" />
                  <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                    Vyberte programy, které se nesmí časově překrývat s tímto programem, bez ohledu na zdroje.
                  </div>
                </div>
              </div>
              <p className="text-sm text-gray-500">
                Nesmí se překrývat s těmito programy:
              </p>

              {otherPrograms.length > 0 ? (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {otherPrograms.map(prog => {
                    const isBlocked = formData.blocked_program_ids.includes(prog.id);
                    return (
                      <label
                        key={prog.id}
                        className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                          isBlocked
                            ? 'border-red-300 bg-red-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        data-testid={`collision-block-program-${prog.id}`}
                      >
                        <Checkbox
                          checked={isBlocked}
                          onCheckedChange={() => toggleBlockedProgram(prog.id)}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-slate-900 text-sm truncate">{prog.name_cs}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className={`px-1.5 py-0.5 text-xs rounded ${
                              prog.status === 'active' ? 'bg-slate-800 text-white' : 'bg-gray-200 text-gray-600'
                            }`}>
                              {prog.status === 'active' ? 'aktivní' : 'koncept'}
                            </span>
                            <span className="text-xs text-gray-400">{prog.duration} min</span>
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              ) : (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <p className="text-sm text-gray-500">Žádné další programy k dispozici.</p>
                </div>
              )}

              {formData.blocked_program_ids.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">
                    <strong>{formData.blocked_program_ids.length}</strong> {formData.blocked_program_ids.length === 1 ? 'program' : 'programů'} nesmí běžet současně s tímto programem.
                  </p>
                </div>
              )}
            </Card>
          </>
        )}

        {/* Summary card */}
        <Card className="p-4 md:p-6 bg-slate-50 border-slate-200">
          <h3 className="font-semibold text-slate-900 mb-3">Shrnutí nastavení</h3>
          <div className="space-y-2 text-sm">
            {!formData.allow_parallel ? (
              <p className="text-slate-700">
                Program <strong>blokuje</strong> svůj časový slot globálně. Žádný jiný program se nemůže časově překrývat.
              </p>
            ) : (
              <>
                <p className="text-slate-700">
                  Program <strong>umožňuje</strong> paralelní provoz.
                </p>
                {formData.collision_resources.length > 0 && (
                  <p className="text-slate-600">
                    Kontrola kolizí: {formData.collision_resources.map(r => 
                      r === 'lecturer' ? 'Lektor' : 'Místnost'
                    ).join(', ')}
                  </p>
                )}
                {formData.blocked_program_ids.length > 0 && (
                  <p className="text-slate-600">
                    Ručně blokované programy: {formData.blocked_program_ids.length}
                  </p>
                )}
                {formData.collision_resources.length === 0 && formData.blocked_program_ids.length === 0 && (
                  <p className="text-amber-600">
                    Bez omezení — program se může překrývat se vším.
                  </p>
                )}
              </>
            )}
          </div>
        </Card>
      </div>
    );
  };

  const renderFeedbackTab = () => {
    const questionTypes = [
      { value: 'text', label: 'Textová odpověď' },
      { value: 'scale', label: 'Škála 1-5' },
      { value: 'yesno', label: 'Ano / Ne' },
    ];

    const addQuestion = () => {
      if (formData.feedback_questions.length >= 5) {
        toast.error('Maximální počet otázek je 5');
        return;
      }
      setFormData(prev => ({
        ...prev,
        feedback_questions: [
          ...prev.feedback_questions,
          { id: Date.now().toString(), question: '', type: 'text' }
        ]
      }));
    };

    const updateQuestion = (id, field, value) => {
      setFormData(prev => ({
        ...prev,
        feedback_questions: prev.feedback_questions.map(q =>
          q.id === id ? { ...q, [field]: value } : q
        )
      }));
    };

    const removeQuestion = (id) => {
      setFormData(prev => ({
        ...prev,
        feedback_questions: prev.feedback_questions.filter(q => q.id !== id)
      }));
    };

    return (
      <div className="space-y-4 md:space-y-6">
        {/* Default feedback toggle */}
        <Card className="p-4 md:p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-slate-900">Zpětná vazba</h3>
              <p className="text-sm text-gray-500 mt-1">Povolit sběr zpětné vazby po dokončení programu</p>
            </div>
            <Switch
              checked={formData.feedback_enabled}
              onCheckedChange={(checked) => setFormData(prev => ({ ...prev, feedback_enabled: checked }))}
              data-testid="feedback-enabled-toggle"
            />
          </div>

          {formData.feedback_enabled && (
            <div className="border-t border-gray-100 pt-4 mt-4">
              <h4 className="text-sm font-medium text-slate-700 mb-3">Výchozí zpětná vazba (vždy přítomná)</h4>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Star className="w-4 h-4 text-amber-500" />
                  <span className="text-sm text-slate-700">Hodnocení hvězdičkami (1-5)</span>
                  <span className="ml-auto text-xs text-gray-400">povinné</span>
                </div>
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <MessageSquare className="w-4 h-4 text-blue-500" />
                  <span className="text-sm text-slate-700">Doporučuji / Nedoporučuji</span>
                  <span className="ml-auto text-xs text-gray-400">povinné</span>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Custom questions - PRO only */}
        {formData.feedback_enabled && (
          <Card className="p-4 md:p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                  Individuální otázky
                  {!isPro && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">PRO</span>}
                </h3>
                <p className="text-sm text-gray-500 mt-1">Vlastní otázky specifické pro tento program (max 5)</p>
              </div>
            </div>

            {!isPro ? (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
                <Lock className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600 mb-2">Individuální otázky jsou dostupné v PRO verzi</p>
                <button
                  type="button"
                  onClick={() => window.location.href = '/admin/settings'}
                  className="text-sm text-slate-800 underline hover:text-slate-600"
                >
                  Aktivovat PRO verzi
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {formData.feedback_questions.map((q, index) => (
                  <div key={q.id} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg" data-testid={`feedback-question-${index}`}>
                    <span className="text-xs text-gray-400 mt-2 font-mono w-5 shrink-0">{index + 1}.</span>
                    <div className="flex-1 space-y-2">
                      <Input
                        value={q.question}
                        onChange={(e) => updateQuestion(q.id, 'question', e.target.value)}
                        placeholder="Zadejte otázku..."
                        className="text-sm"
                        data-testid={`feedback-question-input-${index}`}
                      />
                      <select
                        value={q.type}
                        onChange={(e) => updateQuestion(q.id, 'type', e.target.value)}
                        className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white w-full md:w-auto"
                        data-testid={`feedback-question-type-${index}`}
                      >
                        {questionTypes.map(t => (
                          <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                      </select>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeQuestion(q.id)}
                      className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded shrink-0"
                      data-testid={`feedback-question-remove-${index}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}

                {formData.feedback_questions.length < 5 && (
                  <button
                    type="button"
                    onClick={addQuestion}
                    className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-800 px-3 py-2 border border-dashed border-gray-300 rounded-lg hover:border-gray-400 w-full justify-center"
                    data-testid="feedback-add-question-btn"
                  >
                    <Plus className="w-4 h-4" />
                    Přidat otázku ({formData.feedback_questions.length}/5)
                  </button>
                )}
              </div>
            )}
          </Card>
        )}
      </div>
    );
  };

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
      <div className="flex border-b overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab('detail')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
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
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
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
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === 'collision'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-collision"
        >
          <ShieldAlert className="w-4 h-4" />
          Kolize
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('feedback')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === 'feedback'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-feedback"
        >
          <Star className="w-4 h-4" />
          Zpětná vazba
        </button>
        {editingProgram && (
          <button
            type="button"
            onClick={() => setActiveTab('mailing')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
              activeTab === 'mailing'
                ? 'border-slate-800 text-slate-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid="program-tab-mailing"
          >
            <Mail className="w-4 h-4" />
            Mailing
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="max-h-[60vh] overflow-y-auto pb-20">
        {activeTab === 'detail' && renderDetailTab()}
        {activeTab === 'settings' && renderSettingsTab()}
        {activeTab === 'collision' && renderCollisionTab()}
        {activeTab === 'feedback' && renderFeedbackTab()}
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
          <DialogContent className="max-w-2xl max-h-[95vh] overflow-hidden p-0">
            <DialogHeader className="sr-only">
              <DialogTitle>{editingProgram ? 'Upravit program' : 'Nový program'}</DialogTitle>
            </DialogHeader>
            <div className="p-6">
              {renderProgramForm()}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* URL Generator Modal */}
      <Dialog open={showUrlModal} onOpenChange={setShowUrlModal}>
        <DialogContent className="max-w-lg" aria-describedby="url-description">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <LinkIcon className="w-5 h-5" />
              URL pro vložení na web
            </DialogTitle>
            <p id="url-description" className="text-sm text-gray-500 mt-2">
              Vyberte program a zkopírujte URL pro vložení na webové stránky.
            </p>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Program Selection */}
            <div>
              <Label className="text-sm font-medium text-slate-700 mb-2 block">Vyberte program</Label>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-2">
                <button
                  type="button"
                  onClick={() => handleProgramSelectForUrl('all')}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedProgramForUrl === 'all' 
                      ? 'bg-slate-800 text-white' 
                      : 'hover:bg-gray-100'
                  }`}
                  data-testid="url-select-all"
                >
                  Všechny programy
                </button>
                {Array.isArray(programs) && programs.filter(p => p.status === 'active').map(program => (
                  <button
                    key={program.id}
                    type="button"
                    onClick={() => handleProgramSelectForUrl(program.id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                      selectedProgramForUrl === program.id 
                        ? 'bg-slate-800 text-white' 
                        : 'hover:bg-gray-100'
                    }`}
                    data-testid={`url-select-${program.id}`}
                  >
                    {program.name_cs}
                  </button>
                ))}
              </div>
            </div>

            {/* Age Filter for URL */}
            <div>
              <Label className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4" />
                Filtr věkové skupiny (volitelné)
              </Label>
              <p className="text-xs text-gray-500 mb-2">Vyberte cílovou skupinu — učitelé uvidí jen relevantní programy</p>
              <div className="flex flex-wrap gap-2">
                {URL_AGE_OPTIONS.map(opt => {
                  const isActive = urlAgeFilters.includes(opt.code);
                  return (
                    <button
                      key={opt.code}
                      type="button"
                      onClick={() => toggleUrlAgeFilter(opt.code)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                        isActive 
                          ? 'bg-slate-800 text-white border-slate-800' 
                          : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                      }`}
                      data-testid={`url-age-filter-${opt.code}`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Generated URL */}
            {urlData && (
              <>
                <div>
                  <Label className="text-xs text-gray-500">Vybraný program</Label>
                  <p className="font-medium">{urlData.program_name}</p>
                </div>

                <div>
                  <Label className="text-xs text-gray-500">URL pro rezervaci</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      value={urlData.url}
                      readOnly
                      className="flex-1 text-sm font-mono"
                      data-testid="external-url-input"
                    />
                    <Button
                      size="sm"
                      onClick={() => copyToClipboard(urlData.url)}
                      className="bg-slate-800 text-white"
                      data-testid="copy-url-btn"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div>
                  <Label className="text-xs text-gray-500">HTML kód pro vložení</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      value={urlData.embed_code}
                      readOnly
                      className="flex-1 text-sm font-mono"
                      data-testid="embed-code-input"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyToClipboard(urlData.embed_code)}
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t">
                  <Button
                    variant="outline"
                    onClick={() => window.open(urlData.previewUrl, '_blank')}
                    className="flex-1"
                    data-testid="preview-url-btn"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Náhled
                  </Button>
                  <Button
                    onClick={() => setShowUrlModal(false)}
                    className="flex-1 bg-slate-800 text-white"
                  >
                    Zavřít
                  </Button>
                </div>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

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
