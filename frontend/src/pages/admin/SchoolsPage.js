import React, { useEffect, useState } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Checkbox } from '../../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import axios from 'axios';
import { Download, Send, Mail, Phone, User, Building, CheckCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const SchoolsPage = () => {
  const { t } = useTranslation();
  const [schools, setSchools] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPro, setIsPro] = useState(false);
  const [selectedSchools, setSelectedSchools] = useState([]);
  const [showPropagationModal, setShowPropagationModal] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [schoolsRes, proRes, programsRes] = await Promise.all([
        axios.get(`${API}/schools`),
        axios.get(`${API}/settings/pro`),
        axios.get(`${API}/programs`)
      ]);
      setSchools(Array.isArray(schoolsRes.data) ? schoolsRes.data : []);
      setIsPro(proRes.data.is_pro);
      setPrograms(Array.isArray(programsRes.data) ? programsRes.data : []);
    } catch (error) {
      toast.error(t('common.error'));
      setSchools([]);
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const response = await axios.get(`${API}/schools/export-csv`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'skoly_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Export dokončen');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při exportu');
    }
  };

  const toggleSchoolSelection = (schoolId) => {
    setSelectedSchools(prev => 
      prev.includes(schoolId) 
        ? prev.filter(id => id !== schoolId)
        : [...prev, schoolId]
    );
  };

  const selectAllSchools = () => {
    if (selectedSchools.length === schools.length) {
      setSelectedSchools([]);
    } else {
      setSelectedSchools((schools || []).map(s => s.id));
    }
  };

  const handleSendPropagation = async () => {
    if (!selectedProgram) {
      toast.error('Vyberte program');
      return;
    }
    if (selectedSchools.length === 0) {
      toast.error('Vyberte alespoň jednu školu');
      return;
    }

    setSending(true);
    try {
      const response = await axios.post(`${API}/schools/send-propagation`, {
        school_ids: selectedSchools,
        program_id: selectedProgram
      });
      toast.success(response.data.message);
      setShowPropagationModal(false);
      setSelectedSchools([]);
      setSelectedProgram('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při odesílání');
    } finally {
      setSending(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900">{t('schools.title')}</h1>
          
          {isPro && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleExportCSV}
                data-testid="export-csv-btn"
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
              <Button
                onClick={() => setShowPropagationModal(true)}
                disabled={selectedSchools.length === 0}
                className="bg-slate-800 text-white"
                data-testid="send-propagation-btn"
              >
                <Send className="w-4 h-4 mr-2" />
                Rozeslat propagaci ({selectedSchools.length})
              </Button>
            </div>
          )}
        </div>

        {isPro && schools.length > 0 && (
          <div className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg">
            <Checkbox
              checked={selectedSchools.length === schools.length && schools.length > 0}
              onCheckedChange={selectAllSchools}
              data-testid="select-all-schools"
            />
            <span className="text-sm text-slate-600">
              {selectedSchools.length === schools.length 
                ? 'Odznačit vše' 
                : 'Vybrat všechny školy'}
            </span>
            {selectedSchools.length > 0 && (
              <span className="text-sm font-medium text-slate-800">
                Vybráno: {selectedSchools.length} z {schools.length}
              </span>
            )}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto"></div>
          </div>
        ) : schools.length === 0 ? (
          <Card className="p-12 text-center">
            <Building className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">Zatím nemáte žádné registrované školy</p>
            <p className="text-sm text-gray-400 mt-2">Školy se automaticky přidají po vytvoření rezervace</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.isArray(schools) && schools.map((school) => (
              <Card 
                key={school.id} 
                className={`p-6 transition-all ${
                  selectedSchools.includes(school.id) 
                    ? 'ring-2 ring-slate-800 bg-slate-50' 
                    : ''
                }`}
                data-testid={`school-card-${school.id}`}
              >
                <div className="flex items-start gap-3">
                  {isPro && (
                    <Checkbox
                      checked={selectedSchools.includes(school.id)}
                      onCheckedChange={() => toggleSchoolSelection(school.id)}
                      className="mt-1"
                      data-testid={`select-school-${school.id}`}
                    />
                  )}
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-slate-900 mb-4">{school.name}</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">{school.contact_person}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-gray-400" />
                        <a href={`mailto:${school.email}`} className="text-blue-600 hover:underline">
                          {school.email}
                        </a>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-gray-400" />
                        <a href={`tel:${school.phone}`} className="text-blue-600 hover:underline">
                          {school.phone}
                        </a>
                      </div>
                      {school.city && (
                        <div className="flex items-center gap-2">
                          <Building className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-600">{school.city}</span>
                        </div>
                      )}
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <span className="text-gray-500">Počet rezervací: </span>
                        <span className="font-semibold text-green-600">{school.booking_count || 0}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Propagation Modal */}
      <Dialog open={showPropagationModal} onOpenChange={setShowPropagationModal}>
        <DialogContent className="max-w-md" aria-describedby="propagation-description">
          <DialogHeader>
            <DialogTitle>Rozeslat propagaci programu</DialogTitle>
            <p id="propagation-description" className="text-sm text-gray-500 mt-2">
              Vybraným školám bude odeslán email s informací o programu.
            </p>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-2">
                Vyberte program
              </label>
              <Select value={selectedProgram} onValueChange={setSelectedProgram}>
                <SelectTrigger data-testid="select-program-propagation">
                  <SelectValue placeholder="Vyberte program..." />
                </SelectTrigger>
                <SelectContent>
                  {Array.isArray(programs) && programs.map(program => (
                    <SelectItem key={program.id} value={program.id}>
                      {program.name_cs}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span>Vybrané školy: <strong>{selectedSchools.length}</strong></span>
              </div>
            </div>

            <div className="flex gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setShowPropagationModal(false)}
                className="flex-1"
              >
                Zrušit
              </Button>
              <Button
                onClick={handleSendPropagation}
                disabled={sending || !selectedProgram}
                className="flex-1 bg-slate-800 text-white"
                data-testid="confirm-send-propagation"
              >
                {sending ? 'Odesílám...' : 'Odeslat'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};
