import React, { useEffect, useState, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Loader2, Eye, Users as UsersIcon, BarChart3, ExternalLink, Shield } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import axios from 'axios';
import { Navigate } from 'react-router-dom';
import { API } from '../../config/api';

const RANGE_OPTIONS = [
  { days: 7, label: '7 dní' },
  { days: 30, label: '30 dní' },
  { days: 90, label: '90 dní' },
];

const Kpi = ({ label, value, icon: Icon, accent = 'slate', testid }) => {
  const accents = {
    slate: 'text-slate-700 bg-slate-100',
    emerald: 'text-emerald-700 bg-emerald-100',
    indigo: 'text-indigo-700 bg-indigo-100',
    amber: 'text-amber-700 bg-amber-100',
  };
  return (
    <Card className="p-4" data-testid={testid}>
      <div className="flex items-center gap-3">
        {Icon && <div className={`w-10 h-10 rounded-md flex items-center justify-center ${accents[accent]}`}><Icon className="w-5 h-5" /></div>}
        <div>
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">{label}</div>
          <div className="text-2xl font-bold text-slate-900 leading-tight">{value ?? '—'}</div>
        </div>
      </div>
    </Card>
  );
};

export default function SuperadminAnalyticsPage() {
  const { user } = useContext(AuthContext);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  // The platform owner is identified by e-mail (matches the AdminLayout nav
  // visibility rule) — same convention as `/admin/superadmin`.
  const isSuperadmin = !user || (
    user.email === 'demo@budezivo.cz' ||
    user.email === 'admin@budezivo.cz' ||
    user.role === 'superadmin'
  );

  const load = async (range) => {
    setLoading(true);
    setErr(null);
    try {
      const res = await axios.get(`${API}/analytics/stats`, { params: { days: range } });
      setData(res.data);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Chyba při načítání analytiky');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isSuperadmin) return;
    load(days);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, isSuperadmin]);

  // Hard-gate non-superadmins after hooks run (Rules of Hooks compliant).
  if (user && !isSuperadmin) {
    return <Navigate to="/admin" replace />;
  }

  return (
    <AdminLayout>
      <div className="space-y-6" data-testid="superadmin-analytics-page">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Shield className="w-6 h-6 text-purple-600" />
            <h1 className="text-2xl font-bold text-slate-900">Návštěvnost webu</h1>
            <span className="text-xs text-slate-500 hidden sm:inline">vlastní lehká analytika · Superadmin</span>
          </div>
          <div className="flex gap-1.5" role="tablist" aria-label="Časový rozsah">
            {RANGE_OPTIONS.map(opt => (
              <Button
                key={opt.days}
                size="sm"
                variant={days === opt.days ? 'default' : 'outline'}
                onClick={() => setDays(opt.days)}
                data-testid={`range-${opt.days}`}
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mr-2" /> Načítám analytiku…
          </div>
        )}

        {err && !loading && (
          <Card className="p-4 bg-red-50 border-red-200 text-sm text-red-800" data-testid="analytics-error">
            {err}
          </Card>
        )}

        {!loading && !err && data && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Kpi label="Návštěvy dnes" value={data.today_views} icon={Eye} accent="indigo" testid="kpi-today" />
              <Kpi label="Návštěvy 7 dní" value={data.views_7d} icon={Eye} accent="slate" testid="kpi-7d" />
              <Kpi label="Návštěvy 30 dní" value={data.views_30d} icon={Eye} accent="emerald" testid="kpi-30d" />
              <Kpi label="Unikátní (30 dní)" value={data.unique_visitors_30d} icon={UsersIcon} accent="amber" testid="kpi-unique-30d" />
            </div>

            <Card className="p-4" data-testid="analytics-chart-card">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4" />
                    Návštěvnost v čase
                  </h2>
                  <p className="text-xs text-slate-500">Posledních {data.range_days} dní · denní agregace (UTC)</p>
                </div>
                <div className="flex gap-3 text-[11px] text-slate-500">
                  <span className="inline-flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-[#263FA8]" /> Zobrazení</span>
                  <span className="inline-flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-[#84a98c]" /> Unikátní</span>
                </div>
              </div>
              <div className="h-64 w-full" data-testid="analytics-chart">
                {data.daily.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-sm text-slate-400">
                    Zatím žádná data za zvolené období.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.daily} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                      <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748b' }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                      <Tooltip
                        contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        labelFormatter={(v) => `Den: ${v}`}
                      />
                      <Line type="monotone" dataKey="views" stroke="#263FA8" strokeWidth={2} dot={false} name="Zobrazení" />
                      <Line type="monotone" dataKey="unique_visitors" stroke="#84a98c" strokeWidth={2} dot={false} name="Unikátní" />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </Card>

            <Card className="p-4" data-testid="analytics-top-paths">
              <h2 className="text-sm font-semibold text-slate-900 mb-3">Nejnavštěvovanější stránky</h2>
              {data.top_paths.length === 0 ? (
                <p className="text-sm text-slate-400 py-4 text-center">Zatím žádná data.</p>
              ) : (
                <div className="overflow-x-auto -mx-4 sm:mx-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200">
                        <th className="px-4 py-2 font-medium">URL</th>
                        <th className="px-4 py-2 font-medium text-right w-24">Zobrazení</th>
                        <th className="px-4 py-2 font-medium w-12"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_paths.map(row => (
                        <tr key={row.path} className="border-b border-slate-100 last:border-b-0" data-testid={`path-row-${row.path}`}>
                          <td className="px-4 py-2 font-mono text-xs text-slate-700 truncate max-w-md">{row.path}</td>
                          <td className="px-4 py-2 text-right tabular-nums">{row.views}</td>
                          <td className="px-4 py-2">
                            <a
                              href={row.path}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-400 hover:text-slate-700 inline-flex items-center"
                              title="Otevřít stránku v novém tabu"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <p className="text-xs text-slate-400">
              Vaše vlastní IP adresy jsou ze statistik vyloučeny (ENV <code className="font-mono">ADMIN_IP</code>).
              Statické soubory ani API endpointy se nezapočítávají. Data jsou anonymizovaná (hash IP + denní salt).
            </p>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
