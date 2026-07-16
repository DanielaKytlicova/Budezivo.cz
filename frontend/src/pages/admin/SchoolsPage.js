import React, { useEffect, useState, useRef, useContext } from 'react';
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
  Upload, FileSpreadsheet, AlertTriangle, X, Loader2, FileText,
  Tag, Filter, Search, Plus, ChevronDown, ChevronUp, Users,
  AlertCircle, Check, Trash2, Edit2
} from 'lucide-react';
import { API } from '../../config/api';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { AuthContext } from '../../context/AuthContext';

export const SchoolsPage = () => {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const [schools, setSchools] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPro, setIsPro] = useState(false);
  const [selectedSchools, setSelectedSchools] = useState([]);
  const [showPropagationModal, setShowPropagationModal] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState('');
  const [sending, setSending] = useState(false);
  
  // Filters
  const [sourceFilter, setSourceFilter] = useState('all');
  const [tagFilter, setTagFilter] = useState('all');
  const [invalidFilter, setInvalidFilter] = useState(false);
  const [availableTags, setAvailableTags] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Import modal state
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResult, setImportResult] = useState(null);
  const [updateExisting, setUpdateExisting] = useState(false);
  const fileInputRef = useRef(null);
  
  // Tag edit modal
  const [showTagModal, setShowTagModal] = useState(false);
  const [editingSchool, setEditingSchool] = useState(null);
  const [editingTags, setEditingTags] = useState([]);
  const [newTag, setNewTag] = useState('');
  
  // Contact modal
  const [showContactModal, setShowContactModal] = useState(false);
  const [contactSchool, setContactSchool] = useState(null);
  const [contactForm, setContactForm] = useState({ email: '', name: '', phone: '', is_primary: false });
  const [savingContact, setSavingContact] = useState(false);
  
  // Expanded schools (to show all contacts)
  const [expandedSchools, setExpandedSchools] = useState(new Set());
  
  // Predefined tags
  const PREDEFINED_TAGS = ['MŠ', 'ZŠ', 'SŠ', 'VOŠ', 'VŠ', 'Gymnázium', 'ZUŠ', 'DDM', 'Jiné'];

  // Bulk delete
  const [showBulkDelete, setShowBulkDelete] = useState(false);
  const [bulkSummary, setBulkSummary] = useState(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [purgeConfirmChecked, setPurgeConfirmChecked] = useState(false);
  const [purgeConfirmText, setPurgeConfirmText] = useState('');
  // Bulk tags
  const [showBulkTags, setShowBulkTags] = useState(false);
  const [bulkTags, setBulkTags] = useState([]);
  const [bulkNewTag, setBulkNewTag] = useState('');
  const [bulkTagMode, setBulkTagMode] = useState('add');

  const role = user?.role;
  const canPurge = role === 'admin' || role === 'spravce';

  const openBulkDelete = async () => {
    setBulkSummary(null);
    setPurgeConfirmChecked(false);
    setPurgeConfirmText('');
    setShowBulkDelete(true);
    try {
      const res = await axios.post(`${API}/schools/bulk/summary`, { school_ids: selectedSchools });
      setBulkSummary(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Nepodařilo se načíst souhrn');
      setShowBulkDelete(false);
    }
  };

  const runBulkDelete = async (mode) => {
    setBulkBusy(true);
    try {
      const res = await axios.post(`${API}/schools/bulk/delete`, {
        school_ids: selectedSchools, mode,
        confirm_text: mode === 'purge' ? purgeConfirmText : undefined,
      });
      const d = res.data;
      const parts = [];
      if (d.deleted_schools) parts.push(`${d.deleted_schools} škol`);
      if (d.hidden_schools) parts.push(`${d.hidden_schools} skrytých škol`);
      if (d.deleted_contacts) parts.push(`${d.deleted_contacts} kontaktů`);
      if (d.deleted_reservations) parts.push(`${d.deleted_reservations} testovacích rezervací`);
      toast.success('Hotovo: ' + (parts.join(', ') || 'bez změn'));
      setShowBulkDelete(false);
      setSelectedSchools([]);
      await fetchData();
      await fetchTags();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operace selhala');
    } finally {
      setBulkBusy(false);
    }
  };

  const openBulkTags = () => {
    setBulkTags([]);
    setBulkNewTag('');
    setBulkTagMode('add');
    setShowBulkTags(true);
  };

  const toggleBulkTag = (t) => {
    setBulkTags(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  };

  const addBulkNewTag = () => {
    const t = bulkNewTag.trim();
    if (t && !bulkTags.includes(t)) setBulkTags(prev => [...prev, t]);
    setBulkNewTag('');
  };

  const runBulkTags = async () => {
    if (bulkTags.length === 0) { toast.error('Vyberte nebo zadejte alespoň jeden tag'); return; }
    setBulkBusy(true);
    try {
      const res = await axios.post(`${API}/schools/bulk/tags`, {
        school_ids: selectedSchools, tags: bulkTags, mode: bulkTagMode,
      });
      toast.success(`Tagy upraveny u ${res.data.updated_schools} škol`);
      setShowBulkTags(false);
      setSelectedSchools([]);
      await fetchData();
      await fetchTags();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Uložení tagů selhalo');
    } finally {
      setBulkBusy(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchTags();
    // Setup contacts table on mount
    setupContactsTable();
  }, []);

  const setupContactsTable = async () => {
    try {
      await axios.post(`${API}/schools/setup-contacts-table`);
    } catch (error) {
      // Table probably already exists
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (sourceFilter && sourceFilter !== 'all') {
        params.append('source', sourceFilter);
      }
      if (tagFilter && tagFilter !== 'all') {
        params.append('tag', tagFilter);
      }
      if (invalidFilter) {
        params.append('has_invalid', 'true');
      }
      
      const [schoolsRes, proRes, programsRes] = await Promise.all([
        axios.get(`${API}/schools${params.toString() ? '?' + params.toString() : ''}`),
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

  const fetchTags = async () => {
    try {
      const response = await axios.get(`${API}/schools/tags`);
      setAvailableTags(response.data?.tags || []);
    } catch (error) {
      console.log('Could not fetch tags');
    }
  };

  useEffect(() => {
    if (!loading) {
      fetchData();
    }
  }, [sourceFilter, tagFilter, invalidFilter]);

  const handleExportCSV = async () => {
    try {
      const response = await axios.get(`${API}/schools/export-csv`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'skoly_kontakty_export.csv');
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
      link.setAttribute('download', 'vzorovy_import_skol_kontaktu.xlsx');
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
      
      if (response.data.new_schools > 0 || response.data.new_contacts > 0) {
        toast.success(`Úspěšně: ${response.data.new_schools} nových škol, ${response.data.new_contacts} nových kontaktů`);
        fetchData();
      } else if (response.data.duplicates > 0) {
        toast.info(`Všechny kontakty již existují (${response.data.duplicates} duplicit)`);
      }
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při importu');
      setImportResult({
        success: false,
        total_rows: 0,
        imported: 0,
        new_schools: 0,
        new_contacts: 0,
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

  const handleEditTags = (school) => {
    setEditingSchool(school);
    setEditingTags(school.tags || []);
    setNewTag('');
    setShowTagModal(true);
  };

  const handleAddTag = (tag) => {
    if (tag && !editingTags.includes(tag)) {
      setEditingTags([...editingTags, tag]);
    }
    setNewTag('');
  };

  const handleRemoveTag = (tag) => {
    setEditingTags(editingTags.filter(t => t !== tag));
  };

  const handleSaveTags = async () => {
    if (!editingSchool) return;
    
    try {
      await axios.put(`${API}/schools/${editingSchool.id}/tags`, editingTags);
      toast.success('Tagy uloženy');
      setShowTagModal(false);
      fetchData();
      fetchTags();
    } catch (error) {
      toast.error('Nepodařilo se uložit tagy');
    }
  };

  // Contact management
  const handleAddContact = (school) => {
    setContactSchool(school);
    setContactForm({ email: '', name: '', phone: '', is_primary: false });
    setShowContactModal(true);
  };

  const handleSaveContact = async () => {
    if (!contactSchool || !contactForm.email) {
      toast.error('Vyplňte email');
      return;
    }
    
    setSavingContact(true);
    try {
      await axios.post(`${API}/schools/${contactSchool.id}/contacts`, contactForm);
      toast.success('Kontakt přidán');
      setShowContactModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se přidat kontakt');
    } finally {
      setSavingContact(false);
    }
  };

  const handleDeleteContact = async (schoolId, contactId) => {
    if (!window.confirm('Opravdu chcete odstranit tento kontakt?')) return;
    
    try {
      await axios.delete(`${API}/schools/${schoolId}/contacts/${contactId}`);
      toast.success('Kontakt odstraněn');
      fetchData();
    } catch (error) {
      toast.error('Nepodařilo se odstranit kontakt');
    }
  };

  const handleFixEmail = async (schoolId, contactId) => {
    try {
      const response = await axios.post(`${API}/schools/${schoolId}/contacts/${contactId}/fix-email`);
      toast.success(`Email opraven na: ${response.data.new_email}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se opravit email');
    }
  };

  const handleMarkInvalid = async (schoolId, contactId) => {
    try {
      await axios.put(`${API}/schools/${schoolId}/contacts/${contactId}`, { status: 'invalid' });
      toast.success('Kontakt označen jako neplatný');
      fetchData();
    } catch (error) {
      toast.error('Nepodařilo se aktualizovat kontakt');
    }
  };

  const handleMarkActive = async (schoolId, contactId) => {
    try {
      await axios.put(`${API}/schools/${schoolId}/contacts/${contactId}`, { status: 'active' });
      toast.success('Kontakt označen jako aktivní');
      fetchData();
    } catch (error) {
      toast.error('Nepodařilo se aktualizovat kontakt');
    }
  };

  const getSourceLabel = (source) => {
    switch (source) {
      case 'import': return 'Import';
      case 'reservation': return 'Rezervace';
      case 'organic': return 'Ručně';
      default: return source || 'Neznámý';
    }
  };

  const getSourceColor = (source) => {
    switch (source) {
      case 'import': return 'bg-blue-100 text-blue-700';
      case 'reservation': return 'bg-green-100 text-green-700';
      case 'organic': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'invalid':
        return <Badge className="bg-red-100 text-red-700 text-xs">Neplatný</Badge>;
      case 'pending_verification':
        return <Badge className="bg-yellow-100 text-yellow-700 text-xs">K ověření</Badge>;
      default:
        return null;
    }
  };

  // Filter schools by search query
  const filteredSchools = schools.filter(school => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      school.name?.toLowerCase().includes(query) ||
      school.email?.toLowerCase().includes(query) ||
      school.city?.toLowerCase().includes(query) ||
      school.contacts?.some(c => c.email?.toLowerCase().includes(query) || c.name?.toLowerCase().includes(query))
    );
  });

  const toggleSchoolSelection = (schoolId) => {
    setSelectedSchools(prev => 
      prev.includes(schoolId) 
        ? prev.filter(id => id !== schoolId)
        : [...prev, schoolId]
    );
  };

  const selectAllSchools = () => {
    if (selectedSchools.length === filteredSchools.length) {
      setSelectedSchools([]);
    } else {
      setSelectedSchools(filteredSchools.map(s => s.id));
    }
  };

  const toggleExpanded = (schoolId) => {
    setExpandedSchools(prev => {
      const newSet = new Set(prev);
      if (newSet.has(schoolId)) {
        newSet.delete(schoolId);
      } else {
        newSet.add(schoolId);
      }
      return newSet;
    });
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

  // Count total active contacts
  const totalActiveContacts = schools.reduce((sum, s) => 
    sum + (s.contacts?.filter(c => c.status === 'active').length || 0), 0
  );
  const totalInvalidContacts = schools.reduce((sum, s) => 
    sum + (s.invalid_contacts_count || 0), 0
  );

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">{t('schools.title')}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {schools.length} škol • {totalActiveContacts} aktivních kontaktů
              {totalInvalidContacts > 0 && (
                <span className="text-red-600 ml-2">• {totalInvalidContacts} neplatných</span>
              )}
            </p>
          </div>
          
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  const res = await axios.post(`${API}/schools/auto-tag`, {}, { withCredentials: true });
                  toast.success(res.data.message);
                  fetchData();
                } catch { toast.error('Chyba při auto-tagování'); }
              }}
              data-testid="auto-tag-schools-btn"
            >
              <Tag className="w-4 h-4 mr-2" />
              Auto-tag
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowImportModal(true)}
              data-testid="import-schools-btn"
            >
              <Upload className="w-4 h-4 mr-2" />
              Importovat
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
                  Rozeslat ({selectedSchools.length})
                </Button>
                <Button
                  onClick={openBulkTags}
                  disabled={selectedSchools.length === 0}
                  variant="outline"
                  data-testid="bulk-add-tags-btn"
                >
                  <Tag className="w-4 h-4 mr-2" />
                  Přidat tagy
                </Button>
                <Button
                  onClick={openBulkDelete}
                  disabled={selectedSchools.length === 0}
                  variant="outline"
                  className="text-red-600 border-red-200 hover:bg-red-50"
                  data-testid="bulk-delete-schools-btn"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Smazat vybrané školy ({selectedSchools.length})
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Filters Section */}
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center flex-wrap">
            {/* Search */}
            <div className="relative flex-1 w-full sm:max-w-xs">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Hledat školy nebo kontakty..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                data-testid="search-schools-input"
              />
            </div>
            
            {/* Source Filter */}
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="w-full sm:w-[180px]" data-testid="source-filter">
                <Filter className="w-4 h-4 mr-2 text-gray-400" />
                <SelectValue placeholder="Zdroj" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Všechny zdroje</SelectItem>
                <SelectItem value="import">Importované</SelectItem>
                <SelectItem value="reservation">Z rezervací</SelectItem>
                <SelectItem value="organic">Ručně přidané</SelectItem>
              </SelectContent>
            </Select>
            
            {/* Tag Filter */}
            <Select value={tagFilter} onValueChange={setTagFilter}>
              <SelectTrigger className="w-full sm:w-[180px]" data-testid="tag-filter">
                <Tag className="w-4 h-4 mr-2 text-gray-400" />
                <SelectValue placeholder="Typ školy" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Všechny typy</SelectItem>
                {PREDEFINED_TAGS.map(tag => (
                  <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                ))}
                {availableTags.filter(t => !PREDEFINED_TAGS.includes(t)).map(tag => (
                  <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {/* Invalid contacts filter */}
            <div className="flex items-center gap-2">
              <Checkbox
                id="invalid-filter"
                checked={invalidFilter}
                onCheckedChange={setInvalidFilter}
              />
              <label htmlFor="invalid-filter" className="text-sm text-gray-700 cursor-pointer flex items-center gap-1">
                <AlertCircle className="w-4 h-4 text-red-500" />
                S neplatnými kontakty
              </label>
            </div>
            
            {/* Reset filters */}
            {(sourceFilter !== 'all' || tagFilter !== 'all' || searchQuery || invalidFilter) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSourceFilter('all');
                  setTagFilter('all');
                  setSearchQuery('');
                  setInvalidFilter(false);
                }}
                data-testid="reset-filters-btn"
              >
                <X className="w-4 h-4 mr-1" />
                Resetovat
              </Button>
            )}
          </div>
          
          {/* Results count */}
          <div className="mt-3 text-sm text-gray-500">
            Nalezeno: {filteredSchools.length} škol
            {(sourceFilter !== 'all' || tagFilter !== 'all' || invalidFilter) && (
              <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                Filtrováno
              </span>
            )}
          </div>
        </Card>

        {isPro && filteredSchools.length > 0 && (
          <div className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg">
            <Checkbox
              checked={selectedSchools.length === filteredSchools.length && filteredSchools.length > 0}
              onCheckedChange={selectAllSchools}
              data-testid="select-all-schools"
            />
            <span className="text-sm text-slate-600">
              {selectedSchools.length === filteredSchools.length 
                ? 'Odznačit vše' 
                : 'Vybrat všechny školy'}
            </span>
            {selectedSchools.length > 0 && (
              <span className="text-sm font-medium text-slate-800">
                Vybráno: {selectedSchools.length} z {filteredSchools.length}
              </span>
            )}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-800 mx-auto"></div>
          </div>
        ) : filteredSchools.length === 0 ? (
          <Card className="p-12 text-center">
            <Building className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            {schools.length === 0 ? (
              <>
                <p className="text-gray-500">Zatím nemáte žádné registrované školy</p>
                <p className="text-sm text-gray-400 mt-2">Importujte školy z Excelu nebo se automaticky přidají po rezervaci</p>
              </>
            ) : (
              <>
                <p className="text-gray-500">Žádné školy nevyhovují filtru</p>
                <Button 
                  variant="link" 
                  onClick={() => { setSourceFilter('all'); setTagFilter('all'); setSearchQuery(''); setInvalidFilter(false); }}
                  className="mt-2"
                >
                  Zrušit filtry
                </Button>
              </>
            )}
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {filteredSchools.map((school) => (
              <Card 
                key={school.id} 
                className={`p-5 transition-all ${
                  selectedSchools.includes(school.id) 
                    ? 'ring-2 ring-slate-800 bg-slate-50' 
                    : ''
                } ${school.invalid_contacts_count > 0 ? 'border-red-200' : ''}`}
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
                  <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-slate-900 truncate">{school.name}</h3>
                        {school.city && (
                          <p className="text-sm text-gray-500 flex items-center gap-1">
                            <Building className="w-3 h-3" />
                            {school.city}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge className={`text-xs ${getSourceColor(school.source)}`}>
                          {getSourceLabel(school.source)}
                        </Badge>
                        {school.invalid_contacts_count > 0 && (
                          <Badge className="bg-red-100 text-red-700 text-xs">
                            <AlertCircle className="w-3 h-3 mr-1" />
                            {school.invalid_contacts_count}
                          </Badge>
                        )}
                      </div>
                    </div>
                    
                    {/* Tags */}
                    <div className="flex flex-wrap gap-1 mb-3">
                      {school.tags && school.tags.length > 0 ? (
                        school.tags.map((tag, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
                            {tag}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-gray-400 italic">Bez tagů</span>
                      )}
                      <button
                        onClick={() => handleEditTags(school)}
                        className="ml-1 p-0.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                        title="Upravit tagy"
                        data-testid={`edit-tags-${school.id}`}
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                    </div>
                    
                    {/* Contacts Section */}
                    <div className="border-t pt-3 mt-2">
                      <div className="flex items-center justify-between mb-2">
                        <button
                          onClick={() => toggleExpanded(school.id)}
                          className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-gray-900"
                        >
                          <Users className="w-4 h-4" />
                          Kontakty ({school.contacts?.length || 0})
                          {expandedSchools.has(school.id) ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleAddContact(school)}
                          className="h-7 px-2"
                        >
                          <Plus className="w-3 h-3 mr-1" />
                          Přidat
                        </Button>
                      </div>
                      
                      {/* Contact list */}
                      <div className="space-y-2">
                        {(school.contacts || [])
                          .slice(0, expandedSchools.has(school.id) ? undefined : 2)
                          .map((contact, idx) => (
                          <div 
                            key={contact.id || idx} 
                            className={`flex items-center justify-between p-2 rounded-lg text-sm ${
                              contact.status === 'invalid' ? 'bg-red-50' : 'bg-gray-50'
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              {contact.is_primary && (
                                <span className="text-yellow-500" title="Hlavní kontakt">★</span>
                              )}
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <a href={`mailto:${contact.email}`} className="text-blue-600 hover:underline truncate">
                                    {contact.email}
                                  </a>
                                  {getStatusBadge(contact.status)}
                                  {contact.suggested_correction && contact.status !== 'invalid' && (
                                    <button
                                      onClick={() => handleFixEmail(school.id, contact.id)}
                                      className="text-xs text-orange-600 hover:text-orange-800 flex items-center gap-0.5"
                                      title={`Opravit na: ${contact.suggested_correction}`}
                                    >
                                      <AlertTriangle className="w-3 h-3" />
                                      Opravit
                                    </button>
                                  )}
                                </div>
                                {contact.name && (
                                  <p className="text-xs text-gray-500 truncate">{contact.name}</p>
                                )}
                              </div>
                            </div>
                            
                            {contact.id && (
                              <div className="flex items-center gap-1 shrink-0 ml-2">
                                {contact.status === 'invalid' ? (
                                  <button
                                    onClick={() => handleMarkActive(school.id, contact.id)}
                                    className="p-1 text-green-600 hover:bg-green-100 rounded"
                                    title="Označit jako aktivní"
                                  >
                                    <Check className="w-3 h-3" />
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleMarkInvalid(school.id, contact.id)}
                                    className="p-1 text-orange-600 hover:bg-orange-100 rounded"
                                    title="Označit jako neplatný"
                                  >
                                    <AlertCircle className="w-3 h-3" />
                                  </button>
                                )}
                                <button
                                  onClick={() => handleDeleteContact(school.id, contact.id)}
                                  className="p-1 text-red-600 hover:bg-red-100 rounded"
                                  title="Odstranit kontakt"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                        
                        {!expandedSchools.has(school.id) && (school.contacts?.length || 0) > 2 && (
                          <button
                            onClick={() => toggleExpanded(school.id)}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            + dalších {school.contacts.length - 2} kontaktů
                          </button>
                        )}
                      </div>
                    </div>
                    
                    {/* Footer stats */}
                    <div className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-sm">
                      <span className="text-gray-500">
                        Rezervací: <span className="font-semibold text-green-600">{school.booking_count || 0}</span>
                      </span>
                      {school.contacts?.some(c => c.phone) && (
                        <a 
                          href={`tel:${school.contacts.find(c => c.phone)?.phone}`}
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <Phone className="w-3 h-3" />
                          {school.contacts.find(c => c.phone)?.phone}
                        </a>
                      )}
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
              Email bude odeslán všem aktivním kontaktům vybraných škol.
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

            <div className="bg-slate-50 p-3 rounded-lg space-y-1">
              <div className="flex items-center gap-2 text-sm">
                <Building className="w-4 h-4 text-slate-600" />
                <span>Vybrané školy: <strong>{selectedSchools.length}</strong></span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Mail className="w-4 h-4 text-green-600" />
                <span>
                  Odhadovaný počet emailů: <strong>
                    {schools
                      .filter(s => selectedSchools.includes(s.id))
                      .reduce((sum, s) => sum + (s.contacts?.filter(c => c.status === 'active').length || 0), 0)
                    }
                  </strong>
                </span>
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

      {/* Bulk delete schools */}
      <Dialog open={showBulkDelete} onOpenChange={setShowBulkDelete}>
        <DialogContent className="sm:max-w-lg" data-testid="bulk-delete-dialog">
          <DialogHeader>
            <DialogTitle>
              {bulkSummary && bulkSummary.booking_count > 0 ? 'Vybrané školy mají rezervace' : 'Trvale smazat vybrané školy?'}
            </DialogTitle>
          </DialogHeader>
          {!bulkSummary ? (
            <p className="text-sm text-gray-500 py-4">Načítám souhrn…</p>
          ) : bulkSummary.booking_count === 0 ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-700" data-testid="bulk-delete-summary">
                Budou trvale odstraněny <strong>{bulkSummary.school_count}</strong> školy a <strong>{bulkSummary.contact_count}</strong> kontaktní osoby. Tuto akci nelze vrátit zpět.
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowBulkDelete(false)} data-testid="bulk-delete-cancel">Zrušit</Button>
                <Button className="bg-red-600 hover:bg-red-700 text-white" disabled={bulkBusy} onClick={() => runBulkDelete('hard')} data-testid="bulk-delete-confirm-hard">Trvale smazat</Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800" data-testid="bulk-delete-summary">
                Vybrané školy mají <strong>{bulkSummary.booking_count}</strong> navázaných rezervací. Jejich odstranění by ovlivnilo statistiky a historii rezervací.
              </div>
              <Button variant="outline" className="w-full" disabled={bulkBusy} onClick={() => runBulkDelete('hide')} data-testid="bulk-delete-hide">
                Pouze skrýt školy (rezervace i statistiky zůstanou)
              </Button>
              {canPurge && (
                <div className="border-t pt-3 space-y-2">
                  <p className="text-sm font-medium text-slate-800">Smazat jako testovací data</p>
                  {bulkSummary.ambiguous_reservations > 0 ? (
                    <p className="text-sm text-red-600" data-testid="purge-ambiguous-warning">
                      {bulkSummary.ambiguous_reservations} rezervací nelze bezpečně přiřadit k těmto školám (chybí spolehlivá vazba). Automatické smazání je zablokováno — použijte „Pouze skrýt školy".
                    </p>
                  ) : (
                    <>
                      <p className="text-sm text-gray-600" data-testid="purge-counts">
                        Trvale bude odstraněno: <strong>{bulkSummary.school_count}</strong> škol, <strong>{bulkSummary.contact_count}</strong> kontaktů a <strong>{bulkSummary.linked_reservations ?? bulkSummary.booking_count}</strong> rezervací (včetně jejich zpětné vazby). Nevratné.
                      </p>
                      <label className="flex items-start gap-2 text-sm text-gray-600">
                        <input type="checkbox" checked={purgeConfirmChecked} onChange={e => setPurgeConfirmChecked(e.target.checked)} className="mt-1" data-testid="purge-understand-checkbox" />
                        Rozumím, že budou odstraněny také rezervace a změní se statistiky.
                      </label>
                      <Input placeholder="Napište SMAZAT" value={purgeConfirmText} onChange={e => setPurgeConfirmText(e.target.value)} data-testid="purge-confirm-input" />
                      <Button
                        className="w-full bg-red-600 hover:bg-red-700 text-white"
                        disabled={bulkBusy || !purgeConfirmChecked || purgeConfirmText !== 'SMAZAT'}
                        onClick={() => runBulkDelete('purge')}
                        data-testid="bulk-delete-purge"
                      >
                        Smazat jako testovací data
                      </Button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Bulk add tags */}
      <Dialog open={showBulkTags} onOpenChange={setShowBulkTags}>
        <DialogContent className="sm:max-w-lg" data-testid="bulk-tags-dialog">
          <DialogHeader>
            <DialogTitle>Přidat tagy ({selectedSchools.length} škol)</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {[...new Set([...PREDEFINED_TAGS, ...availableTags])].map(tag => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleBulkTag(tag)}
                  className={`px-3 py-1 rounded-full text-sm border ${bulkTags.includes(tag) ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-700 border-slate-200'}`}
                  data-testid={`bulk-tag-option-${tag}`}
                >
                  {tag}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Input placeholder="Nový tag" value={bulkNewTag} onChange={e => setBulkNewTag(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addBulkNewTag(); } }} data-testid="bulk-new-tag-input" />
              <Button variant="outline" onClick={addBulkNewTag} data-testid="bulk-add-new-tag">Přidat</Button>
            </div>
            {bulkTags.length > 0 && (
              <div className="flex flex-wrap gap-1" data-testid="bulk-selected-tags">
                {bulkTags.map(t => <Badge key={t} variant="secondary">{t}</Badge>)}
              </div>
            )}
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-1"><input type="radio" checked={bulkTagMode === 'add'} onChange={() => setBulkTagMode('add')} data-testid="bulk-tag-mode-add" /> Přidat ke stávajícím</label>
              <label className="flex items-center gap-1"><input type="radio" checked={bulkTagMode === 'replace'} onChange={() => setBulkTagMode('replace')} data-testid="bulk-tag-mode-replace" /> Nahradit stávající</label>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowBulkTags(false)}>Zrušit</Button>
              <Button className="bg-slate-800 text-white" disabled={bulkBusy} onClick={runBulkTags} data-testid="bulk-tags-confirm">Uložit tagy</Button>
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
              Importovat školy a kontakty
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {!importResult ? (
              <>
                {/* Instructions */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
                  <p className="font-medium text-blue-800 mb-2">Multi-kontakt import:</p>
                  <ul className="text-blue-700 space-y-1 ml-4 list-disc">
                    <li>Jeden řádek = jeden kontakt</li>
                    <li>Škola je identifikována kombinací <strong>Název + Město</strong></li>
                    <li>Více kontaktů pro stejnou školu = více řádků</li>
                    <li>Duplikátní emaily jsou přeskočeny</li>
                  </ul>
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
                    Aktualizovat tagy existujících škol
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
                  importResult.new_schools > 0 || importResult.new_contacts > 0 
                    ? 'bg-green-50 border border-green-200' 
                    : importResult.errors > 0 
                      ? 'bg-red-50 border border-red-200' 
                      : 'bg-yellow-50 border border-yellow-200'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {importResult.new_schools > 0 || importResult.new_contacts > 0 ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : importResult.errors > 0 ? (
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-yellow-600" />
                    )}
                    <span className="font-semibold">
                      {importResult.new_schools > 0 || importResult.new_contacts > 0 
                        ? 'Import dokončen' 
                        : importResult.errors > 0 
                          ? 'Import selhal' 
                          : 'Žádná nová data'}
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-green-600">{importResult.new_schools}</p>
                    <p className="text-xs text-gray-500">Nových škol</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-blue-600">{importResult.new_contacts}</p>
                    <p className="text-xs text-gray-500">Nových kontaktů</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-yellow-600">{importResult.duplicates}</p>
                    <p className="text-xs text-gray-500">Duplicit</p>
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

      {/* Tag Edit Modal */}
      <Dialog open={showTagModal} onOpenChange={setShowTagModal}>
        <DialogContent className="max-w-md" aria-describedby="tag-edit-description">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Tag className="w-5 h-5 text-purple-600" />
              Upravit tagy školy
            </DialogTitle>
            <p id="tag-edit-description" className="text-sm text-gray-500 mt-1">
              {editingSchool?.name}
            </p>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Current Tags */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Aktuální tagy
              </label>
              <div className="flex flex-wrap gap-2 min-h-[40px] p-2 border rounded-lg bg-gray-50">
                {editingTags.length > 0 ? (
                  editingTags.map((tag, idx) => (
                    <Badge 
                      key={idx} 
                      className="bg-purple-100 text-purple-700 flex items-center gap-1 pr-1"
                    >
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-1 hover:bg-purple-200 rounded p-0.5"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))
                ) : (
                  <span className="text-gray-400 text-sm italic">Žádné tagy</span>
                )}
              </div>
            </div>

            {/* Predefined Tags */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Přidat typ školy
              </label>
              <div className="flex flex-wrap gap-2">
                {PREDEFINED_TAGS.map(tag => (
                  <button
                    key={tag}
                    onClick={() => handleAddTag(tag)}
                    disabled={editingTags.includes(tag)}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                      editingTags.includes(tag)
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : 'bg-white hover:bg-purple-50 hover:border-purple-300 text-gray-700'
                    }`}
                  >
                    + {tag}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Tag */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Vlastní tag
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="Např. 'Speciální škola'"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newTag.trim()) {
                      handleAddTag(newTag.trim());
                    }
                  }}
                  data-testid="custom-tag-input"
                />
                <Button
                  variant="outline"
                  onClick={() => newTag.trim() && handleAddTag(newTag.trim())}
                  disabled={!newTag.trim()}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setShowTagModal(false)}
                className="flex-1"
              >
                Zrušit
              </Button>
              <Button
                onClick={handleSaveTags}
                className="flex-1 bg-purple-600 text-white hover:bg-purple-700"
                data-testid="save-tags-btn"
              >
                Uložit tagy
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Contact Modal */}
      <Dialog open={showContactModal} onOpenChange={setShowContactModal}>
        <DialogContent className="max-w-md" aria-describedby="contact-add-description">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <User className="w-5 h-5 text-blue-600" />
              Přidat kontakt
            </DialogTitle>
            <p id="contact-add-description" className="text-sm text-gray-500 mt-1">
              {contactSchool?.name}
            </p>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Email <span className="text-red-500">*</span>
              </label>
              <Input
                type="email"
                placeholder="email@skola.cz"
                value={contactForm.email}
                onChange={(e) => setContactForm({...contactForm, email: e.target.value})}
                data-testid="contact-email-input"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Jméno kontaktu
              </label>
              <Input
                placeholder="Např. Jan Novák, Pedagog"
                value={contactForm.name}
                onChange={(e) => setContactForm({...contactForm, name: e.target.value})}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Telefon
              </label>
              <Input
                placeholder="+420 123 456 789"
                value={contactForm.phone}
                onChange={(e) => setContactForm({...contactForm, phone: e.target.value})}
              />
            </div>
            
            <div className="flex items-center gap-2">
              <Checkbox
                id="is-primary"
                checked={contactForm.is_primary}
                onCheckedChange={(checked) => setContactForm({...contactForm, is_primary: checked})}
              />
              <label htmlFor="is-primary" className="text-sm text-gray-700 cursor-pointer">
                Označit jako hlavní kontakt
              </label>
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setShowContactModal(false)}
                className="flex-1"
              >
                Zrušit
              </Button>
              <Button
                onClick={handleSaveContact}
                disabled={savingContact || !contactForm.email}
                className="flex-1 bg-blue-600 text-white hover:bg-blue-700"
                data-testid="save-contact-btn"
              >
                {savingContact ? 'Ukládám...' : 'Přidat kontakt'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};
