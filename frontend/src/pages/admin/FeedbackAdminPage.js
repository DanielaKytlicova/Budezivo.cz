/**
 * FeedbackAdminPage - Admin stránka pro správu zpětné vazby
 * 
 * Funkce:
 * - Přehled všech zpětných vazeb s filtry
 * - Správa otázek (CRUD)
 * - Statistiky
 * - Export do CSV
 */
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Star, 
  Download, 
  Plus, 
  Edit2, 
  Trash2, 
  Filter,
  BarChart3,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  X,
  Check
} from 'lucide-react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../components/ui/dialog';
import { useToast } from '../../hooks/use-toast';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Star Display Component
const StarDisplay = ({ rating }) => (
  <div className="flex gap-0.5">
    {[1, 2, 3, 4, 5].map((star) => (
      <Star
        key={star}
        className={`w-4 h-4 ${
          star <= rating
            ? 'fill-yellow-400 text-yellow-400'
            : 'text-gray-300'
        }`}
      />
    ))}
  </div>
);

// Statistics Card
const StatCard = ({ title, value, icon: Icon, color = 'blue' }) => (
  <div className="bg-white rounded-xl p-6 shadow-sm border">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-500 mb-1">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
      <div className={`p-3 rounded-lg bg-${color}-50`}>
        <Icon className={`w-6 h-6 text-${color}-500`} />
      </div>
    </div>
  </div>
);

export default function FeedbackAdminPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('submissions');
  const [loading, setLoading] = useState(true);
  
  // Submissions state
  const [submissions, setSubmissions] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [filters, setFilters] = useState({
    status: '',
    program_id: '',
    min_rating: '',
    date_from: '',
    date_to: ''
  });
  
  // Questions state
  const [questions, setQuestions] = useState([]);
  const [questionDialog, setQuestionDialog] = useState({ open: false, mode: 'create', data: null });
  
  // Programs for filter
  const [programs, setPrograms] = useState([]);
  
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  
  // Fetch data
  const fetchSubmissions = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key === 'status' ? 'status_filter' : key, value);
      });
      
      const response = await axios.get(`${API_URL}/api/feedback/submissions?${params}`, { headers });
      setSubmissions(response.data);
    } catch (err) {
      console.error('Error fetching submissions:', err);
      toast({ variant: 'destructive', title: 'Chyba', description: 'Nepodařilo se načíst zpětné vazby' });
    }
  }, [filters, toast]);
  
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/feedback/statistics`, { headers });
      setStatistics(response.data);
    } catch (err) {
      console.error('Error fetching statistics:', err);
    }
  }, []);
  
  const fetchQuestions = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/feedback/questions?include_inactive=true`, { headers });
      setQuestions(response.data);
    } catch (err) {
      console.error('Error fetching questions:', err);
    }
  }, []);
  
  const fetchPrograms = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/programs`, { headers });
      setPrograms(response.data.data || response.data || []);
    } catch (err) {
      console.error('Error fetching programs:', err);
    }
  }, []);
  
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchSubmissions(), fetchStatistics(), fetchQuestions(), fetchPrograms()]);
      setLoading(false);
    };
    loadData();
  }, [fetchSubmissions, fetchStatistics, fetchQuestions, fetchPrograms]);
  
  // Question CRUD
  const handleSaveQuestion = async (data) => {
    try {
      if (questionDialog.mode === 'create') {
        await axios.post(`${API_URL}/api/feedback/questions`, data, { headers });
        toast({ title: 'Úspěch', description: 'Otázka byla vytvořena' });
      } else {
        await axios.put(`${API_URL}/api/feedback/questions/${questionDialog.data.id}`, data, { headers });
        toast({ title: 'Úspěch', description: 'Otázka byla upravena' });
      }
      setQuestionDialog({ open: false, mode: 'create', data: null });
      fetchQuestions();
    } catch (err) {
      toast({ variant: 'destructive', title: 'Chyba', description: err.response?.data?.detail || 'Operace selhala' });
    }
  };
  
  const handleDeleteQuestion = async (id) => {
    if (!window.confirm('Opravdu chcete deaktivovat tuto otázku?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/feedback/questions/${id}`, { headers });
      toast({ title: 'Úspěch', description: 'Otázka byla deaktivována' });
      fetchQuestions();
    } catch (err) {
      toast({ variant: 'destructive', title: 'Chyba', description: 'Nepodařilo se deaktivovat otázku' });
    }
  };
  
  // Export
  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.program_id) params.append('program_id', filters.program_id);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);
      
      const response = await axios.get(`${API_URL}/api/feedback/export?${params}`, {
        headers,
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `feedback_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast({ title: 'Úspěch', description: 'Export byl stažen' });
    } catch (err) {
      toast({ variant: 'destructive', title: 'Chyba', description: 'Export selhal' });
    }
  };
  
  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-[#5a7aae]" />
        </div>
      </AdminLayout>
    );
  }
  
  return (
    <AdminLayout>
      <div className="space-y-6" data-testid="feedback-admin-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Zpětná vazba</h1>
            <p className="text-gray-500">Správa zpětné vazby od učitelů</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleExport}
              data-testid="export-feedback-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
        
        {/* Statistics */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard
              title="Celkem zpětných vazeb"
              value={statistics.total_feedbacks}
              icon={MessageSquare}
              color="blue"
            />
            <StatCard
              title="Průměrné hodnocení"
              value={statistics.average_rating ? `${statistics.average_rating}/5` : '-'}
              icon={Star}
              color="yellow"
            />
            <StatCard
              title="Míra doporučení"
              value={statistics.recommendation_rate ? `${statistics.recommendation_rate}%` : '-'}
              icon={ThumbsUp}
              color="green"
            />
            <StatCard
              title="Programů s feedbackem"
              value={statistics.by_program?.length || 0}
              icon={BarChart3}
              color="purple"
            />
          </div>
        )}
        
        {/* Tabs */}
        <div className="border-b">
          <nav className="flex gap-4">
            {[
              { id: 'submissions', label: 'Zpětné vazby' },
              { id: 'questions', label: 'Otázky' },
              { id: 'statistics', label: 'Statistiky' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#5a7aae] text-[#5a7aae]'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        
        {/* Submissions Tab */}
        {activeTab === 'submissions' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="bg-white rounded-lg p-4 shadow-sm border">
              <div className="flex items-center gap-2 mb-4">
                <Filter className="w-4 h-4 text-gray-500" />
                <span className="font-medium text-gray-700">Filtry</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Select
                  value={filters.status || 'all'}
                  onValueChange={(val) => setFilters(prev => ({ ...prev, status: val === 'all' ? '' : val }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Stav" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Všechny stavy</SelectItem>
                    <SelectItem value="submitted">Odesláno</SelectItem>
                    <SelectItem value="pending">Čeká</SelectItem>
                  </SelectContent>
                </Select>
                
                <Select
                  value={filters.program_id || 'all'}
                  onValueChange={(val) => setFilters(prev => ({ ...prev, program_id: val === 'all' ? '' : val }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Program" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Všechny programy</SelectItem>
                    {programs.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name_cs}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Input
                  type="date"
                  placeholder="Od"
                  value={filters.date_from}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                />
                
                <Input
                  type="date"
                  placeholder="Do"
                  value={filters.date_to}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
                />
              </div>
            </div>
            
            {/* Submissions List */}
            <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Datum</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Program</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Škola</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hodnocení</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Doporučuje</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stav</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {submissions.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        Žádné zpětné vazby nenalezeny
                      </td>
                    </tr>
                  ) : (
                    submissions.map((fb) => (
                      <tr key={fb.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{fb.reservation_date}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{fb.program_name || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{fb.school_name}</td>
                        <td className="px-4 py-3">
                          {fb.overall_rating ? <StarDisplay rating={fb.overall_rating} /> : '-'}
                        </td>
                        <td className="px-4 py-3">
                          {fb.would_recommend === true && <ThumbsUp className="w-5 h-5 text-green-500" />}
                          {fb.would_recommend === false && <ThumbsDown className="w-5 h-5 text-red-500" />}
                          {fb.would_recommend === null && '-'}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                            fb.status === 'submitted'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {fb.status === 'submitted' ? 'Odesláno' : 'Čeká'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {/* Questions Tab */}
        {activeTab === 'questions' && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button
                onClick={() => setQuestionDialog({ open: true, mode: 'create', data: null })}
                data-testid="add-question-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Přidat otázku
              </Button>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pořadí</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Otázka</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Typ</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Povinná</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stav</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Akce</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {questions.map((q) => (
                    <tr key={q.id} className={!q.is_active ? 'bg-gray-50 opacity-60' : ''}>
                      <td className="px-4 py-3 text-sm text-gray-500">{q.display_order}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{q.question_text}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {q.question_type === 'rating' && 'Hodnocení (1-5)'}
                        {q.question_type === 'text' && 'Text'}
                        {q.question_type === 'yesno' && 'Ano/Ne'}
                      </td>
                      <td className="px-4 py-3">
                        {q.is_required ? (
                          <Check className="w-4 h-4 text-green-500" />
                        ) : (
                          <X className="w-4 h-4 text-gray-400" />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                          q.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {q.is_active ? 'Aktivní' : 'Neaktivní'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setQuestionDialog({ open: true, mode: 'edit', data: q })}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          {q.is_active && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteQuestion(q.id)}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {/* Statistics Tab */}
        {activeTab === 'statistics' && statistics && (
          <div className="space-y-6">
            {/* Rating Distribution */}
            <div className="bg-white rounded-lg p-6 shadow-sm border">
              <h3 className="font-semibold text-gray-900 mb-4">Rozložení hodnocení</h3>
              <div className="space-y-3">
                {[5, 4, 3, 2, 1].map((rating) => {
                  const count = statistics.by_rating?.[rating] || 0;
                  const total = Object.values(statistics.by_rating || {}).reduce((a, b) => a + b, 0);
                  const percentage = total > 0 ? (count / total) * 100 : 0;
                  
                  return (
                    <div key={rating} className="flex items-center gap-3">
                      <div className="flex items-center gap-1 w-20">
                        <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-sm font-medium">{rating}</span>
                      </div>
                      <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-yellow-400 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 w-16 text-right">{count}x</span>
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* By Program */}
            <div className="bg-white rounded-lg p-6 shadow-sm border">
              <h3 className="font-semibold text-gray-900 mb-4">Hodnocení podle programů</h3>
              {statistics.by_program?.length > 0 ? (
                <div className="space-y-3">
                  {statistics.by_program.map((p, idx) => (
                    <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                      <span className="text-sm text-gray-900">{p.program_name}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-500">{p.count} hodnocení</span>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                          <span className="font-medium">{p.avg_rating || '-'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">Zatím žádná data</p>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Question Dialog */}
      <QuestionDialog
        open={questionDialog.open}
        mode={questionDialog.mode}
        data={questionDialog.data}
        onClose={() => setQuestionDialog({ open: false, mode: 'create', data: null })}
        onSave={handleSaveQuestion}
      />
    </AdminLayout>
  );
}

// Question Dialog Component
function QuestionDialog({ open, mode, data, onClose, onSave }) {
  const [formData, setFormData] = useState({
    question_text: '',
    question_type: 'rating',
    is_required: true,
    display_order: 0,
    is_active: true
  });
  
  useEffect(() => {
    if (data && mode === 'edit') {
      setFormData({
        question_text: data.question_text,
        question_type: data.question_type,
        is_required: data.is_required,
        display_order: data.display_order,
        is_active: data.is_active
      });
    } else {
      setFormData({
        question_text: '',
        question_type: 'rating',
        is_required: true,
        display_order: 0,
        is_active: true
      });
    }
  }, [data, mode, open]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === 'create' ? 'Nová otázka' : 'Upravit otázku'}
          </DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Text otázky *</Label>
            <Textarea
              value={formData.question_text}
              onChange={(e) => setFormData(prev => ({ ...prev, question_text: e.target.value }))}
              placeholder="Např.: Jak hodnotíte srozumitelnost výkladu?"
              required
            />
          </div>
          
          <div>
            <Label>Typ odpovědi</Label>
            <Select
              value={formData.question_type}
              onValueChange={(val) => setFormData(prev => ({ ...prev, question_type: val }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="rating">Hodnocení (1-5 hvězdiček)</SelectItem>
                <SelectItem value="yesno">Ano / Ne</SelectItem>
                <SelectItem value="text">Textová odpověď</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Pořadí zobrazení</Label>
              <Input
                type="number"
                value={formData.display_order}
                onChange={(e) => setFormData(prev => ({ ...prev, display_order: parseInt(e.target.value) || 0 }))}
              />
            </div>
            
            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="is_required"
                checked={formData.is_required}
                onChange={(e) => setFormData(prev => ({ ...prev, is_required: e.target.checked }))}
                className="rounded"
              />
              <Label htmlFor="is_required" className="cursor-pointer">Povinná otázka</Label>
            </div>
          </div>
          
          {mode === 'edit' && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                className="rounded"
              />
              <Label htmlFor="is_active" className="cursor-pointer">Aktivní</Label>
            </div>
          )}
          
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Zrušit
            </Button>
            <Button type="submit" className="bg-[#5a7aae] hover:bg-[#4a6a9e]">
              {mode === 'create' ? 'Vytvořit' : 'Uložit'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
