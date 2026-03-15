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
  GraduationCap, Building2, Clock, CheckCircle, XCircle, Loader2
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
  
  // Filtry
  const [periodType, setPeriodType] = useState('month');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedSemester, setSelectedSemester] = useState(1);

  useEffect(() => {
    fetchStatistics();
    checkProStatus();
  }, [periodType, selectedYear, selectedMonth, selectedSemester]);

  const checkProStatus = async () => {
    try {
      const response = await axios.get(`${API}/settings/pro`);
      setIsPro(response.data?.is_pro || response.data?.csv_export_exception || false);
    } catch (error) {
      console.error('Error checking PRO status');
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
      </div>
    </AdminLayout>
  );
};

export default StatisticsPage;
