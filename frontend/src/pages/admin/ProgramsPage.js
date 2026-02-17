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
import { Plus, ArrowLeft, Clock, Users, MoreVertical, Copy, Archive, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  { value: 'zs1_7_12', label: 'I. stupeň ZŠ' },
  { value: 'zs2_12_15', label: 'II. stupeň ZŠ' },
  { value: 'ss_14_18', label: 'SŠ' },
  { value: 'schools', label: 'Školy a veřejnost' },
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
  min_days_before_booking: 14,
  max_days_before_booking: 14,
  preparation_time: 10,
  cleanup_time: 30,
  age_group: 'zs1_7_12',
});

export const ProgramsPage = () => {
  const { t } = useTranslation();
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingProgram, setEditingProgram] = useState(null);
  const [activeTab, setActiveTab] = useState('detail');
  const [formData, setFormData] = useState(getDefaultFormData());
  const [openMenu, setOpenMenu] = useState(null);

  useEffect(() => {
    fetchPrograms();
  }, []);

  const fetchPrograms = async () => {
    try {
      const response = await axios.get(`${API}/programs`);
      setPrograms(response.data);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      await axios.put(`${API}/programs/${program.id}`, {
        ...program,
        status: 'archived'
      });
      toast.success('Program byl archivován');
      fetchPrograms();
    } catch (error) {
      toast.error(t('common.error'));
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
    setFormData({
      ...getDefaultFormData(),
      ...program,
      target_group: program.target_group || program.age_group || 'schools',
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

      {/* Plan limit banner */}
      <Card className="p-4 bg-gray-50 border-gray-200">
        <p className="text-sm text-gray-600">
          Máte ještě {Math.max(0, freeLimit - programsCount)} volné místo pro bezúplatný tarif.
        </p>
        <button className="text-sm font-medium text-slate-800 hover:underline">
          Navýšit tarif
        </button>
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
          {programs.filter(p => p.status !== 'archived').map((program) => (
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
                      {getTargetGroupLabel(program.target_group || program.age_group)}
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
          <Label className="text-gray-500 text-sm">Cílová skupina</Label>
          <Select
            value={formData.target_group}
            onValueChange={(value) => setFormData({ ...formData, target_group: value, age_group: value })}
          >
            <SelectTrigger className="mt-1" data-testid="program-target-group">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TARGET_GROUPS.map(group => (
                <SelectItem key={group.value} value={group.value}>{group.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
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
        <div className="space-y-3">
          {formData.time_blocks.map((block, index) => (
            <div key={index} className="flex items-center gap-3">
              <Switch
                checked={true}
                onCheckedChange={() => {}}
              />
              <Input
                type="time"
                value={block}
                onChange={(e) => updateTimeBlock(index, e.target.value)}
                className="flex-1"
                data-testid={`program-time-block-${index}`}
              />
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
            onChange={(e) => setFormData({ ...formData, min_days_before_booking: parseInt(e.target.value) || 14 })}
            className="mt-1 bg-white"
            data-testid="program-min-days-before"
          />
        </div>

        <div>
          <Label className="text-gray-500 text-sm">Maximální počet dnů před rezervací (dní)</Label>
          <Input
            type="number"
            value={formData.max_days_before_booking}
            onChange={(e) => setFormData({ ...formData, max_days_before_booking: parseInt(e.target.value) || 14 })}
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
      <div className="flex border-b">
        <button
          type="button"
          onClick={() => setActiveTab('detail')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
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
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'settings'
              ? 'border-slate-800 text-slate-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
          data-testid="program-tab-settings"
        >
          Nastavení
        </button>
      </div>

      {/* Tab content */}
      <div className="max-h-[60vh] overflow-y-auto pb-20">
        {activeTab === 'detail' ? renderDetailTab() : renderSettingsTab()}
      </div>

      {/* Fixed footer */}
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
    </div>
  );

  return (
    <AdminLayout>
      {!showDialog ? (
        renderProgramList()
      ) : (
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-2xl max-h-[95vh] overflow-hidden p-0">
            <div className="p-6">
              {renderProgramForm()}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </AdminLayout>
  );
};
