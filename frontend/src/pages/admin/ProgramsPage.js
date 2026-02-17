import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Plus, Edit, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ProgramsPage = () => {
  const { t } = useTranslation();
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingProgram, setEditingProgram] = useState(null);
  const [formData, setFormData] = useState({
    name_cs: '',
    name_en: '',
    description_cs: '',
    description_en: '',
    duration: 60,
    capacity: 30,
    target_group: 'schools',
    price: 0,
    status: 'active',
  });

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
      if (editingProgram) {
        await axios.put(`${API}/programs/${editingProgram.id}`, formData);
      } else {
        await axios.post(`${API}/programs`, formData);
      }
      toast.success(t('common.success'));
      setShowDialog(false);
      resetForm();
      fetchPrograms();
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('common.delete') + '?')) return;
    try {
      await axios.delete(`${API}/programs/${id}`);
      toast.success(t('common.success'));
      fetchPrograms();
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const resetForm = () => {
    setFormData({
      name_cs: '',
      name_en: '',
      description_cs: '',
      description_en: '',
      duration: 60,
      capacity: 30,
      target_group: 'schools',
      price: 0,
      status: 'active',
    });
    setEditingProgram(null);
  };

  const handleEdit = (program) => {
    setEditingProgram(program);
    setFormData(program);
    setShowDialog(true);
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-slate-900">{t('programs.title')}</h1>
          <Dialog open={showDialog} onOpenChange={setShowDialog}>
            <DialogTrigger asChild>
              <Button data-testid="create-program-button" className="bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90" onClick={resetForm}>
                <Plus className="w-4 h-4 mr-2" />
                {t('programs.create')}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingProgram ? t('programs.edit') : t('programs.create')}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="program-form">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>{t('programs.name')} (CZ)</Label>
                    <Input
                      data-testid="program-name-cs-input"
                      value={formData.name_cs}
                      onChange={(e) => setFormData({ ...formData, name_cs: e.target.value })}
                      required
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label>{t('programs.name')} (EN)</Label>
                    <Input
                      data-testid="program-name-en-input"
                      value={formData.name_en}
                      onChange={(e) => setFormData({ ...formData, name_en: e.target.value })}
                      required
                      className="mt-2"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>{t('programs.description')} (CZ)</Label>
                    <Textarea
                      data-testid="program-description-cs-input"
                      value={formData.description_cs}
                      onChange={(e) => setFormData({ ...formData, description_cs: e.target.value })}
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label>{t('programs.description')} (EN)</Label>
                    <Textarea
                      data-testid="program-description-en-input"
                      value={formData.description_en}
                      onChange={(e) => setFormData({ ...formData, description_en: e.target.value })}
                      className="mt-2"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label>{t('programs.duration')}</Label>
                    <Input
                      type="number"
                      data-testid="program-duration-input"
                      value={formData.duration}
                      onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) })}
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label>{t('programs.capacity')}</Label>
                    <Input
                      type="number"
                      data-testid="program-capacity-input"
                      value={formData.capacity}
                      onChange={(e) => setFormData({ ...formData, capacity: parseInt(e.target.value) })}
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label>{t('programs.price')}</Label>
                    <Input
                      type="number"
                      step="0.01"
                      data-testid="program-price-input"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                      className="mt-2"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>{t('programs.targetGroup')}</Label>
                    <Select value={formData.target_group} onValueChange={(value) => setFormData({ ...formData, target_group: value })}>
                      <SelectTrigger className="mt-2" data-testid="program-target-group-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="schools">{t('programs.targetGroups.schools')}</SelectItem>
                        <SelectItem value="public">{t('programs.targetGroups.public')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>{t('programs.status')}</Label>
                    <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
                      <SelectTrigger className="mt-2" data-testid="program-status-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">{t('programs.statuses.active')}</SelectItem>
                        <SelectItem value="inactive">{t('programs.statuses.inactive')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button type="submit" data-testid="program-submit-button" className="w-full bg-slate-800 hover:bg-slate-700">
                  {t('programs.save')}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          </div>
        ) : programs.length === 0 ? (
          <Card className="p-12 text-center">
            <p className="text-muted-foreground">{t('common.noResults')}</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {programs.map((program) => (
              <Card key={program.id} className="p-6" data-testid={`program-card-${program.id}`}>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">{program.name_cs}</h3>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{program.description_cs}</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('programs.duration')}:</span>
                    <span className="font-medium">{program.duration} min</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('programs.capacity')}:</span>
                    <span className="font-medium">{program.capacity}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('programs.price')}:</span>
                    <span className="font-medium">{program.price} Kč</span>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <Button
                    size="sm"
                    variant="outline"
                    data-testid={`edit-program-${program.id}`}
                    onClick={() => handleEdit(program)}
                    className="flex-1"
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    {t('common.edit')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    data-testid={`delete-program-${program.id}`}
                    onClick={() => handleDelete(program.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  );
};
