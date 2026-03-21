import React, { useEffect, useState, useRef } from 'react';
import { useTranslation } from '../../i18n/useTranslation';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Checkbox } from '../../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Progress } from '../../components/ui/progress';
import { toast } from 'sonner';
import axios from 'axios';
import { 
  Download, Send, Mail, Phone, User, Building, CheckCircle, 
  Upload, FileSpreadsheet, AlertTriangle, X, Loader2, FileText
} from 'lucide-react';
import { API } from '../../config/api';

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
  
  // Import modal state
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResult, setImportResult] = useState(null);
  const [updateExisting, setUpdateExisting] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleDownloadTemplate = async () => {
    try {
      const response = await axios.get(`${API}/schools/import-template`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'vzorovy_import_skol.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      toast.error('Chyba při stahování šablony');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/csv',
        'application/csv'
      ];
      const validExtensions = ['.xlsx', '.xls', '.csv'];
      
      const isValidType = validTypes.includes(file.type) || 
        validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
      
      if (!isValidType) {
        toast.error('Nepodporovaný formát. Použijte .xlsx, .xls nebo .csv');
        return;
      }
      
      // Validate file size (10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Soubor je příliš velký (max 10 MB)');
        return;
      }
      
      setImportFile(file);
      setImportResult(null);
    }
  };

  const handleImport = async () => {
    if (!importFile) {
      toast.error('Vyberte soubor');
      return;
    }
    
    setImporting(true);
    setImportProgress(10);
    
    try {
      const formData = new FormData();
      formData.append('file', importFile);
      
      setImportProgress(30);
      
      const response = await axios.post(
        `${API}/schools/import?update_existing=${updateExisting}`, 
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 50) / progressEvent.total) + 30;
            setImportProgress(Math.min(progress, 80));
          }
        }
      );
      
      setImportProgress(100);
      setImportResult(response.data);
      
      if (response.data.imported > 0) {
        toast.success(`Úspěšně importováno ${response.data.imported} škol`);
        fetchData();
      } else if (response.data.duplicates > 0) {
        toast.info(`Všechny školy již existují (${response.data.duplicates} duplicit)`);
      }
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při importu');
      setImportResult({
        success: false,
        total_rows: 0,
        imported: 0,
        skipped: 0,
        errors: 1,
        duplicates: 0,
        error_details: [{ row: 0, error: error.response?.data?.detail || 'Neznámá chyba' }]
      });
    } finally {
      setImporting(false);
    }
  };

  const handleDownloadErrors = () => {
    if (!importResult?.error_details?.length) return;
    
    const errors = importResult.error_details;
    const csv = "Řádek;Chyba\n" + errors.map(e => `${e.row};${e.error}`).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'import_chyby.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const resetImportModal = () => {
    setShowImportModal(false);
    setImportFile(null);
    setImportResult(null);
    setImportProgress(0);
    setUpdateExisting(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
          
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => setShowImportModal(true)}
              data-testid="import-schools-btn"
            >
              <Upload className="w-4 h-4 mr-2" />
              Importovat školy
            </Button>
            
            {isPro && (
              <>
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
              </>
            )}
          </div>
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

      {/* Import Modal */}
      <Dialog open={showImportModal} onOpenChange={resetImportModal}>
        <DialogContent className="max-w-lg" aria-describedby="import-description">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-green-600" />
              Importovat školy z Excelu
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {!importResult ? (
              <>
                {/* Instructions */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
                  <p className="font-medium text-blue-800 mb-2">Podporované formáty:</p>
                  <ul className="text-blue-700 space-y-1 ml-4 list-disc">
                    <li>Excel (.xlsx, .xls)</li>
                    <li>CSV (.csv)</li>
                  </ul>
                  <p className="text-blue-700 mt-2">
                    <strong>Povinné sloupce:</strong> Název školy, Email
                  </p>
                </div>

                {/* Download template */}
                <button
                  onClick={handleDownloadTemplate}
                  className="flex items-center gap-2 text-sm text-[#5a7aae] hover:underline"
                  data-testid="download-template-btn"
                >
                  <FileText className="w-4 h-4" />
                  Stáhnout vzorový soubor
                </button>

                {/* File Upload Area */}
                <div 
                  className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                    importFile 
                      ? 'border-green-300 bg-green-50' 
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    data-testid="file-input"
                  />
                  
                  {importFile ? (
                    <div className="flex items-center justify-center gap-3">
                      <FileSpreadsheet className="w-8 h-8 text-green-600" />
                      <div className="text-left">
                        <p className="font-medium text-slate-900">{importFile.name}</p>
                        <p className="text-sm text-gray-500">
                          {(importFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          setImportFile(null);
                          if (fileInputRef.current) fileInputRef.current.value = '';
                        }}
                        className="p-1 hover:bg-gray-100 rounded"
                      >
                        <X className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  ) : (
                    <div>
                      <Upload className="w-10 h-10 mx-auto text-gray-400 mb-2" />
                      <p className="text-gray-600 mb-2">
                        Přetáhněte soubor sem nebo
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        Vybrat soubor
                      </Button>
                      <p className="text-xs text-gray-400 mt-2">Max. velikost: 10 MB</p>
                    </div>
                  )}
                </div>

                {/* Options */}
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="update-existing"
                    checked={updateExisting}
                    onCheckedChange={setUpdateExisting}
                  />
                  <label htmlFor="update-existing" className="text-sm text-gray-700 cursor-pointer">
                    Aktualizovat existující záznamy (podle emailu)
                  </label>
                </div>

                {/* Progress */}
                {importing && (
                  <div className="space-y-2">
                    <Progress value={importProgress} className="h-2" />
                    <p className="text-sm text-center text-gray-500">
                      Importuji... {importProgress}%
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    onClick={resetImportModal}
                    className="flex-1"
                    disabled={importing}
                  >
                    Zrušit
                  </Button>
                  <Button
                    onClick={handleImport}
                    disabled={!importFile || importing}
                    className="flex-1 bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
                    data-testid="start-import-btn"
                  >
                    {importing ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Importuji...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Importovat
                      </>
                    )}
                  </Button>
                </div>
              </>
            ) : (
              /* Import Results */
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${
                  importResult.imported > 0 ? 'bg-green-50 border border-green-200' : 
                  importResult.errors > 0 ? 'bg-red-50 border border-red-200' : 
                  'bg-yellow-50 border border-yellow-200'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {importResult.imported > 0 ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : importResult.errors > 0 ? (
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-yellow-600" />
                    )}
                    <span className="font-semibold">
                      {importResult.imported > 0 ? 'Import dokončen' : 
                       importResult.errors > 0 ? 'Import selhal' : 
                       'Žádné nové školy'}
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-green-600">{importResult.imported}</p>
                    <p className="text-xs text-gray-500">Importováno</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-yellow-600">{importResult.duplicates}</p>
                    <p className="text-xs text-gray-500">Duplicit</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-red-600">{importResult.errors}</p>
                    <p className="text-xs text-gray-500">Chyb</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-gray-600">{importResult.total_rows}</p>
                    <p className="text-xs text-gray-500">Celkem řádků</p>
                  </div>
                </div>

                {/* Error details */}
                {importResult.error_details?.length > 0 && (
                  <div className="border border-red-200 rounded-lg overflow-hidden">
                    <div className="bg-red-50 px-3 py-2 flex items-center justify-between">
                      <span className="text-sm font-medium text-red-800">
                        Chyby ({importResult.error_details.length})
                      </span>
                      <button
                        onClick={handleDownloadErrors}
                        className="text-xs text-red-600 hover:underline flex items-center gap-1"
                      >
                        <Download className="w-3 h-3" />
                        Stáhnout CSV
                      </button>
                    </div>
                    <div className="max-h-32 overflow-y-auto p-2 text-xs">
                      {importResult.error_details.slice(0, 10).map((err, idx) => (
                        <div key={idx} className="py-1 border-b last:border-0 text-red-700">
                          {err.error}
                        </div>
                      ))}
                      {importResult.error_details.length > 10 && (
                        <div className="py-1 text-gray-500 italic">
                          ... a dalších {importResult.error_details.length - 10} chyb
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Close button */}
                <Button
                  onClick={resetImportModal}
                  className="w-full bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
                >
                  Zavřít
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};
