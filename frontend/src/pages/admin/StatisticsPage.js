import React, { useState, useEffect } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Calendar, Users, TrendingUp, Download, FileSpreadsheet,
  GraduationCap, Building2, Clock, CheckCircle, XCircle, Loader2,
  Star, MessageSquare, ThumbsUp
} from 'lucide-react';

// Barvy pro grafy
const COLORS = ['#1E293B', '#84A98C', '#E9C46A', '#F4A261', '#E76F51', '#2A9D8F'];
const STATUS_COLORS = {
  'Potvrzené': '#22C55E',
  'Čekající': '#F59E0B',
  'Zrušené': '#EF4444',
  'Dokončené': '#3B82F6',
  'Nedostavil se': '#6B7280',
};

// Pomocné funkce
const getCurrentSchoolYear = () => {
  const now = new Date();
  return now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
};

const getYearOptions = () => {
  const currentYear = new Date().getFullYear();
  const years = [];
  for (let y = currentYear; y >= currentYear - 5; y--) {
    years.push(y);
  }
  return years;
};

const MONTHS = [
  { value: 1, label: 'Leden' },
  { value: 2, label: 'Únor' },
  { value: 3, label: 'Březen' },
  { value: 4, label: 'Duben' },
  { value: 5, label: 'Květen' },
  { value: 6, label: 'Červen' },
  { value: 7, label: 'Červenec' },
  { value: 8, label: 'Srpen' },
  { value: 9, label: 'Září' },
  { value: 10, label: 'Říjen' },
  { value: 11, label: 'Listopad' },
  { value: 12, label: 'Prosinec' },
];

export const StatisticsPage = () => {
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [stats, setStats] = useState(null);
  const [isPro, setIsPro] = useState(false);
  const [feedbackStats, setFeedbackStats] = useState(null);
  const [loadingFeedback, setLoadingFeedback] = useState(true);

  // Advanced analytics state
  const [heatmapData, setHeatmapData] = useState(null);
  const [trendsData, setTrendsData] = useState(null);
  const [topSchools, setTopSchools] = useState(null);
  const [conversionData, setConversionData] = useState(null);
  
  // Filtry
  const [periodType, setPeriodType] = useState('month');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedSemester, setSelectedSemester] = useState(1);

  useEffect(() => {
    fetchStatistics();
    fetchFeedbackStatistics();
    checkProStatus();
    fetchAdvancedAnalytics();
  }, [periodType, selectedYear, selectedMonth, selectedSemester]);

  const checkProStatus = async () => {
    try {
      const response = await axios.get(`${API}/settings/pro`);
      setIsPro(response.data?.is_pro || response.data?.csv_export_exception || false);
    } catch (error) {
      console.error('Error checking PRO status');
    }
  };

  const fetchFeedbackStatistics = async () => {
    setLoadingFeedback(true);
    try {
      const response = await axios.get(`${API}/feedback/statistics`);
      setFeedbackStats(response.data);
    } catch (error) {
      console.log('Feedback statistics not available');
      setFeedbackStats(null);
    } finally {
      setLoadingFeedback(false);
    }
  };

  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('period_type', periodType);
      
      if (periodType === 'month') {
        params.append('year', selectedYear);
        params.append('month', selectedMonth);
      } else if (periodType === 'school_year') {
        params.append('year', selectedYear);
      } else if (periodType === 'semester') {
        params.append('year', selectedYear);
        params.append('semester', selectedSemester);
      } else if (periodType === 'calendar_year') {
        params.append('year', selectedYear);
      }

      const response = await axios.get(`${API}/statistics?${params.toString()}`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching statistics:', error);
      toast.error('Nepodařilo se načíst statistiky');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (exportType) => {
    if (!isPro) {
      toast.error('Export CSV je dostupný pouze pro PRO verzi');
      return;
    }

    setExporting(true);
    try {
      const params = new URLSearchParams();
      params.append('period_type', periodType);
      params.append('export_type', exportType);
      
      if (periodType === 'month') {
        params.append('year', selectedYear);
        params.append('month', selectedMonth);
      } else if (periodType === 'school_year') {
        params.append('year', selectedYear);
      } else if (periodType === 'semester') {
        params.append('year', selectedYear);
        params.append('semester', selectedSemester);
      } else if (periodType === 'calendar_year') {
        params.append('year', selectedYear);
      }

      const response = await axios.get(`${API}/statistics/export/csv?${params.toString()}`, {
        responseType: 'blob'
      });

      // Stáhnout soubor
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') || 'export.csv';
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success('Export byl úspěšně stažen');
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Export CSV je dostupný pouze pro PRO verzi');
      } else {
        toast.error('Nepodařilo se exportovat data');
      }
    } finally {
      setExporting(false);
    }
  };

  const fetchAdvancedAnalytics = async () => {
    const params = `year=${selectedYear}&month=${selectedMonth}`;
    try {
      const [hm, tr, ts, cv] = await Promise.all([
        axios.get(`${API}/statistics/heatmap?${params}`),
        axios.get(`${API}/statistics/trends?year=${selectedYear}`),
        axios.get(`${API}/statistics/top-schools?${params}`),
        axios.get(`${API}/statistics/conversion?${params}`),
      ]);
      setHeatmapData(hm.data);
      setTrendsData(tr.data);
      setTopSchools(ts.data);
      setConversionData(cv.data);
    } catch {
      // Silently fail — advanced analytics are optional
    }
  };

  // Příprava dat pro grafy
  const monthlyChartData = stats?.monthly?.map(m => ({
    name: m.month.substring(0, 3),
    Rezervace: m.bookings,
    Žáci: m.students,
    Pedagogové: m.teachers,
  })) || [];

  const programChartData = stats?.by_program?.slice(0, 5).map(p => ({
    name: p.program_name.length > 20 ? p.program_name.substring(0, 20) + '...' : p.program_name,
    fullName: p.program_name,
    Rezervace: p.bookings_count,
    Návštěvníci: p.total_students + p.total_teachers,
  })) || [];

  const statusChartData = stats?.by_status?.map(s => ({
    name: s.status,
    value: s.count,
  })) || [];

  const ageGroupChartData = stats?.by_age_group?.map(a => ({
    name: a.age_group,
    value: a.count,
  })) || [];

  // Feedback rating distribution data
  const feedbackRatingData = feedbackStats?.by_rating ? 
    Object.entries(feedbackStats.by_rating).map(([rating, count]) => ({
      name: `${rating} ⭐`,
      value: count,
      rating: parseInt(rating)
    })).sort((a, b) => a.rating - b.rating) : [];

  // Feedback by program data
  const feedbackByProgramData = feedbackStats?.by_program?.slice(0, 5).map(p => ({
    name: p.program_name?.length > 18 ? p.program_name.substring(0, 18) + '...' : p.program_name,
    fullName: p.program_name,
    'Průměr': p.avg_rating ? parseFloat(Number(p.avg_rating).toFixed(1)) : 0,
    'Počet': p.count
  })) || [];

  if (loading && !stats) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Statistiky</h1>
            <p className="text-sm text-gray-500 mt-1">
              {stats?.period?.label || 'Načítání...'}
            </p>
          </div>
          
          {/* Export tlačítka */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('summary')}
              disabled={exporting || !isPro}
              className="text-sm"
              data-testid="export-summary"
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Souhrn
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('reservations')}
              disabled={exporting || !isPro}
              className="text-sm"
              data-testid="export-reservations"
            >
              <Download className="w-4 h-4 mr-2" />
              Rezervace
            </Button>
            {!isPro && (
              <span className="text-xs text-gray-400 self-center ml-2">PRO</span>
            )}
          </div>
        </div>

        {/* Filtry */}
        <Card className="p-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="min-w-[180px]">
              <label className="text-sm font-medium text-gray-700 mb-1 block">Období</label>
              <Select value={periodType} onValueChange={setPeriodType}>
                <SelectTrigger data-testid="period-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="month">Měsíc</SelectItem>
                  <SelectItem value="school_year">Školní rok</SelectItem>
                  <SelectItem value="semester">Pololetí</SelectItem>
                  <SelectItem value="calendar_year">Kalendářní rok</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {periodType === 'month' && (
              <div className="min-w-[140px]">
                <label className="text-sm font-medium text-gray-700 mb-1 block">Měsíc</label>
                <Select value={String(selectedMonth)} onValueChange={(v) => setSelectedMonth(Number(v))}>
                  <SelectTrigger data-testid="month-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MONTHS.map(m => (
                      <SelectItem key={m.value} value={String(m.value)}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {periodType === 'semester' && (
              <div className="min-w-[140px]">
                <label className="text-sm font-medium text-gray-700 mb-1 block">Pololetí</label>
                <Select value={String(selectedSemester)} onValueChange={(v) => setSelectedSemester(Number(v))}>
                  <SelectTrigger data-testid="semester-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1. pololetí (září-leden)</SelectItem>
                    <SelectItem value="2">2. pololetí (únor-červen)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="min-w-[120px]">
              <label className="text-sm font-medium text-gray-700 mb-1 block">
                {periodType === 'school_year' || periodType === 'semester' ? 'Školní rok' : 'Rok'}
              </label>
              <Select value={String(selectedYear)} onValueChange={(v) => setSelectedYear(Number(v))}>
                <SelectTrigger data-testid="year-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {getYearOptions().map(y => (
                    <SelectItem key={y} value={String(y)}>
                      {periodType === 'school_year' || periodType === 'semester' ? `${y}/${y+1}` : y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {loading && <Loader2 className="w-5 h-5 animate-spin text-slate-400 ml-2" />}
          </div>
        </Card>

        {/* Přehledové karty */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4" data-testid="stat-total-bookings">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Celkem rezervací</p>
                <p className="text-2xl font-bold text-slate-900">{stats?.overview?.total_bookings || 0}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4" data-testid="stat-total-students">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 rounded-lg">
                <GraduationCap className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Počet žáků</p>
                <p className="text-2xl font-bold text-slate-900">{stats?.overview?.total_students || 0}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4" data-testid="stat-total-teachers">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-50 rounded-lg">
                <Users className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Počet pedagogů</p>
                <p className="text-2xl font-bold text-slate-900">{stats?.overview?.total_teachers || 0}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4" data-testid="stat-total-visitors">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-50 rounded-lg">
                <TrendingUp className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Celkem návštěvníků</p>
                <p className="text-2xl font-bold text-slate-900">{stats?.overview?.total_visitors || 0}</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Status karty */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-3 border-l-4 border-l-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Potvrzené</p>
                <p className="text-lg font-semibold">{stats?.overview?.confirmed_bookings || 0}</p>
              </div>
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
          </Card>
          <Card className="p-3 border-l-4 border-l-yellow-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Čekající</p>
                <p className="text-lg font-semibold">{stats?.overview?.pending_bookings || 0}</p>
              </div>
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
          </Card>
          <Card className="p-3 border-l-4 border-l-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Dokončené</p>
                <p className="text-lg font-semibold">{stats?.overview?.completed_bookings || 0}</p>
              </div>
              <Building2 className="w-5 h-5 text-blue-500" />
            </div>
          </Card>
          <Card className="p-3 border-l-4 border-l-red-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Zrušené</p>
                <p className="text-lg font-semibold">{stats?.overview?.cancelled_bookings || 0}</p>
              </div>
              <XCircle className="w-5 h-5 text-red-500" />
            </div>
          </Card>
        </div>

        {/* Grafy */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Trend rezervací */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Trend rezervací</h2>
            {monthlyChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={monthlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="Rezervace" 
                    stroke="#1E293B" 
                    strokeWidth={2}
                    dot={{ fill: '#1E293B' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="Žáci" 
                    stroke="#84A98C" 
                    strokeWidth={2}
                    dot={{ fill: '#84A98C' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-gray-400">
                Žádná data pro vybrané období
              </div>
            )}
          </Card>

          {/* Nejpopulárnější programy */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Nejpopulárnější programy</h2>
            {programChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={programChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis 
                    type="category" 
                    dataKey="name" 
                    width={120}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }}
                    formatter={(value, name, props) => [value, name]}
                    labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
                  />
                  <Legend />
                  <Bar dataKey="Rezervace" fill="#1E293B" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="Návštěvníci" fill="#84A98C" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-gray-400">
                Žádná data pro vybrané období
              </div>
            )}
          </Card>

          {/* Rozložení podle statusu */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Stav rezervací</h2>
            {statusChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={statusChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {statusChartData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={STATUS_COLORS[entry.name] || COLORS[index % COLORS.length]} 
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-gray-400">
                Žádná data pro vybrané období
              </div>
            )}
          </Card>

          {/* Rozložení podle věkových skupin */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Věkové skupiny</h2>
            {ageGroupChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={ageGroupChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis 
                    dataKey="name" 
                    tick={{ fontSize: 10 }}
                    angle={-20}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }}
                  />
                  <Bar dataKey="value" name="Počet rezervací" fill="#E9C46A" radius={[4, 4, 0, 0]}>
                    {ageGroupChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-gray-400">
                Žádná data pro vybrané období
              </div>
            )}
          </Card>
        </div>

        {/* Průměrná velikost skupiny */}
        {stats?.overview?.avg_group_size > 0 && (
          <Card className="p-4 bg-slate-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Průměrná velikost skupiny</p>
                <p className="text-3xl font-bold text-slate-900">{stats.overview.avg_group_size} žáků</p>
              </div>
              <Users className="w-12 h-12 text-slate-300" />
            </div>
          </Card>
        )}

        {/* Feedback Statistics Section */}
        {feedbackStats && feedbackStats.total_feedbacks > 0 && (
          <>
            {/* Feedback Header */}
            <div className="pt-6 border-t border-gray-200">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <MessageSquare className="w-6 h-6 text-[#84A98C]" />
                Zpětná vazba od učitelů
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Souhrnné statistiky z odeslaných zpětných vazeb
              </p>
            </div>

            {/* Feedback Overview Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4" data-testid="feedback-total">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#84A98C]/10 rounded-lg">
                    <MessageSquare className="w-5 h-5 text-[#84A98C]" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Celkem hodnocení</p>
                    <p className="text-2xl font-bold text-slate-900">{feedbackStats.total_feedbacks}</p>
                  </div>
                </div>
              </Card>

              <Card className="p-4" data-testid="feedback-avg-rating">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-50 rounded-lg">
                    <Star className="w-5 h-5 text-yellow-500" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Průměrné hodnocení</p>
                    <p className="text-2xl font-bold text-slate-900">
                      {feedbackStats.average_rating ? feedbackStats.average_rating.toFixed(1) : '-'}
                      <span className="text-base font-normal text-gray-400">/5</span>
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="p-4" data-testid="feedback-recommendation">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-50 rounded-lg">
                    <ThumbsUp className="w-5 h-5 text-green-500" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Doporučení</p>
                    <p className="text-2xl font-bold text-slate-900">
                      {feedbackStats.recommendation_rate !== null ? `${feedbackStats.recommendation_rate}%` : '-'}
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-to-br from-yellow-50 to-orange-50" data-testid="feedback-stars">
                <div className="flex items-center gap-2 justify-center h-full">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star 
                      key={star}
                      className={`w-6 h-6 ${
                        feedbackStats.average_rating && star <= Math.round(feedbackStats.average_rating)
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>
              </Card>
            </div>

            {/* Feedback Charts */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Rating Distribution */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Rozložení hodnocení</h3>
                {feedbackRatingData.length > 0 && feedbackRatingData.some(d => d.value > 0) ? (
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={feedbackRatingData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis type="number" tick={{ fontSize: 12 }} />
                      <YAxis 
                        type="category" 
                        dataKey="name" 
                        width={60}
                        tick={{ fontSize: 12 }}
                      />
                      <Tooltip 
                        contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }}
                        formatter={(value) => [value, 'Počet']}
                      />
                      <Bar dataKey="value" name="Počet" radius={[0, 4, 4, 0]}>
                        {feedbackRatingData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.rating >= 4 ? '#22C55E' : entry.rating >= 3 ? '#F59E0B' : '#EF4444'} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[250px] flex items-center justify-center text-gray-400">
                    Zatím žádné hodnocení
                  </div>
                )}
              </Card>

              {/* Rating by Program */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Hodnocení podle programu</h3>
                {feedbackByProgramData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={feedbackByProgramData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis type="number" domain={[0, 5]} tick={{ fontSize: 12 }} />
                      <YAxis 
                        type="category" 
                        dataKey="name" 
                        width={100}
                        tick={{ fontSize: 11 }}
                      />
                      <Tooltip 
                        contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }}
                        labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
                      />
                      <Legend />
                      <Bar dataKey="Průměr" fill="#F59E0B" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[250px] flex items-center justify-center text-gray-400">
                    Zatím žádná data
                  </div>
                )}
              </Card>
            </div>

            {/* Link to full feedback page */}
            <Card className="p-4 bg-[#84A98C]/5 border-[#84A98C]/20">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">Podrobná zpětná vazba</h3>
                  <p className="text-sm text-gray-600">
                    Zobrazte všechny odpovědi, spravujte otázky a exportujte data.
                  </p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => window.location.href = '/admin/feedback'}
                  className="border-[#84A98C] text-[#84A98C] hover:bg-[#84A98C]/10"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Zobrazit zpětnou vazbu
                </Button>
              </div>
            </Card>
          </>
        )}

        {/* PRO banner */}
        {!isPro && (
          <Card className="p-4 bg-gradient-to-r from-slate-800 to-slate-700 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Chcete exportovat data?</h3>
                <p className="text-sm text-slate-300">
                  CSV export pro výroční zprávy je dostupný v PRO verzi.
                </p>
              </div>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => window.location.href = '/admin/plan'}
              >
                Zobrazit plány
              </Button>
            </div>
          </Card>
        )}

        {/* ── Pokročilá analytika ─────────────────────────── */}
        <div className="pt-4 border-t border-gray-100">
          <h2 className="text-lg font-semibold text-slate-800 mb-4" data-testid="advanced-analytics-heading">Pokročilá analytika</h2>
        </div>

        {/* Konverzní poměr */}
        {conversionData && (
          <Card className="p-4" data-testid="conversion-card">
            <h3 className="font-medium text-slate-700 mb-3">Konverzní poměr — {conversionData.period}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-slate-800">{conversionData.total}</div>
                <div className="text-xs text-slate-500">Celkem</div>
              </div>
              <div className="text-center p-3 bg-emerald-50 rounded-lg">
                <div className="text-2xl font-bold text-emerald-600">{conversionData.confirmed}</div>
                <div className="text-xs text-slate-500">Potvrzeno</div>
              </div>
              <div className="text-center p-3 bg-amber-50 rounded-lg">
                <div className="text-2xl font-bold text-amber-600">{conversionData.pending}</div>
                <div className="text-xs text-slate-500">Čeká</div>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-500">{conversionData.cancelled}</div>
                <div className="text-xs text-slate-500">Zrušeno</div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${conversionData.conversion_rate}%` }} />
              </div>
              <span className="text-sm font-semibold text-slate-700">{conversionData.conversion_rate}%</span>
            </div>
          </Card>
        )}

        {/* Heatmapa vytíženosti */}
        {heatmapData && heatmapData.time_blocks.length > 0 && (
          <Card className="p-4" data-testid="heatmap-card">
            <h3 className="font-medium text-slate-700 mb-3">Heatmapa vytíženosti — {heatmapData.period}</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="p-2 text-left text-slate-500">Den</th>
                    {heatmapData.time_blocks.map(tb => (
                      <th key={tb} className="p-2 text-center text-slate-500">{tb}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmapData.data.map((row) => (
                    <tr key={row.day}>
                      <td className="p-2 font-medium text-slate-700">{row.day}</td>
                      {heatmapData.time_blocks.map(tb => {
                        const val = row[tb] || 0;
                        const maxVal = Math.max(...heatmapData.data.map(r => Math.max(...heatmapData.time_blocks.map(t => r[t] || 0))), 1);
                        const intensity = val / maxVal;
                        const bg = val === 0 ? 'bg-gray-50' : intensity > 0.7 ? 'bg-emerald-500 text-white' : intensity > 0.3 ? 'bg-emerald-200' : 'bg-emerald-100';
                        return (
                          <td key={tb} className={`p-2 text-center rounded ${bg}`}>
                            {val > 0 ? val : ''}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Trend graf */}
        {trendsData && (
          <Card className="p-4" data-testid="trends-card">
            <h3 className="font-medium text-slate-700 mb-3">Roční trend — {trendsData.current_year} vs {trendsData.previous_year}</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendsData.chart_data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', fontSize: '12px', border: '1px solid #e2e8f0' }}
                    formatter={(value, name) => [value, name.includes('Žáci') ? 'Žáků' : 'Rezervací']}
                  />
                  <Bar dataKey={String(trendsData.current_year)} fill="#1E293B" radius={[3,3,0,0]} name={String(trendsData.current_year)} />
                  <Bar dataKey={String(trendsData.previous_year)} fill="#CBD5E1" radius={[3,3,0,0]} name={String(trendsData.previous_year)} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Top školy */}
        {topSchools && topSchools.schools.length > 0 && (
          <Card className="p-4" data-testid="top-schools-card">
            <h3 className="font-medium text-slate-700 mb-3">Nejaktivnější školy — {topSchools.period}</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="p-2 text-left text-slate-500 text-xs">#</th>
                    <th className="p-2 text-left text-slate-500 text-xs">Škola</th>
                    <th className="p-2 text-center text-slate-500 text-xs">Rezervace</th>
                    <th className="p-2 text-center text-slate-500 text-xs">Žáci</th>
                    <th className="p-2 text-center text-slate-500 text-xs">Učitelé</th>
                  </tr>
                </thead>
                <tbody>
                  {topSchools.schools.map((s, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="p-2 text-slate-400 text-xs">{i + 1}</td>
                      <td className="p-2 font-medium text-slate-700">{s.name}</td>
                      <td className="p-2 text-center">
                        <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full text-xs font-medium">{s.bookings}</span>
                      </td>
                      <td className="p-2 text-center text-slate-600">{s.students}</td>
                      <td className="p-2 text-center text-slate-600">{s.teachers}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </AdminLayout>
  );
};

export default StatisticsPage;
