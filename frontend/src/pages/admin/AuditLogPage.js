import React, { useState, useEffect, useCallback } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Badge } from '../../components/ui/badge';
import { FileText, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import axios from 'axios';
import { API } from '../../config/api';

const ACTION_LABELS = {
  create: { label: 'Vytvořeno', color: 'bg-green-100 text-green-800' },
  update: { label: 'Upraveno', color: 'bg-blue-100 text-blue-800' },
  delete: { label: 'Smazáno', color: 'bg-red-100 text-red-800' },
  archive: { label: 'Archivováno', color: 'bg-gray-100 text-gray-800' },
  unarchive: { label: 'Obnoveno', color: 'bg-emerald-100 text-emerald-800' },
  confirmed: { label: 'Potvrzeno', color: 'bg-green-100 text-green-800' },
  cancelled: { label: 'Zrušeno', color: 'bg-red-100 text-red-800' },
  completed: { label: 'Dokončeno', color: 'bg-indigo-100 text-indigo-800' },
  pending: { label: 'Čeká', color: 'bg-yellow-100 text-yellow-800' },
};

const ENTITY_LABELS = {
  program: 'Program',
  reservation: 'Rezervace',
  school: 'Škola',
  settings: 'Nastavení',
  user: 'Uživatel',
};

export const AuditLogPage = () => {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [entityFilter, setEntityFilter] = useState('all');
  const perPage = 30;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, per_page: perPage });
      if (entityFilter !== 'all') params.append('entity_type', entityFilter);
      const res = await axios.get(`${API}/audit-log?${params}`);
      setLogs(res.data.items);
      setTotal(res.data.total);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [page, entityFilter]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const totalPages = Math.ceil(total / perPage);

  const formatDate = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric' })
      + ' ' + d.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });
  };

  const getActionBadge = (action) => {
    const a = ACTION_LABELS[action] || { label: action, color: 'bg-gray-100 text-gray-700' };
    return <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${a.color}`}>{a.label}</span>;
  };

  const getDetailText = (log) => {
    const d = log.details || {};
    const parts = [];
    if (d.name) parts.push(d.name);
    if (d.school) parts.push(d.school);
    if (d.old_status && d.new_status) parts.push(`${d.old_status} → ${d.new_status}`);
    if (d.reason) parts.push(`Důvod: ${d.reason}`);
    return parts.join(' | ');
  };

  return (
    <AdminLayout>
      <div className="space-y-6" data-testid="audit-log-page">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Audit log</h1>
            <p className="text-sm text-gray-500 mt-1">Přehled všech akcí v systému ({total} záznamů)</p>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <Select value={entityFilter} onValueChange={(v) => { setEntityFilter(v); setPage(1); }}>
              <SelectTrigger className="w-[180px]" data-testid="audit-entity-filter">
                <SelectValue placeholder="Filtrovat typ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Vše</SelectItem>
                <SelectItem value="program">Programy</SelectItem>
                <SelectItem value="reservation">Rezervace</SelectItem>
                <SelectItem value="school">Školy</SelectItem>
                <SelectItem value="settings">Nastavení</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <Card className="overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-gray-400">Načítání...</div>
          ) : logs.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Žádné záznamy v audit logu</p>
              <p className="text-sm text-gray-400 mt-1">Záznamy se budou ukládat při akcích v systému</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="audit-log-table">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Datum</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Uživatel</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Akce</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Typ</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(log.created_at)}</td>
                      <td className="px-4 py-3 text-gray-700">{log.user_email || '—'}</td>
                      <td className="px-4 py-3">{getActionBadge(log.action)}</td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className="text-xs">
                          {ENTITY_LABELS[log.entity_type] || log.entity_type}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{getDetailText(log)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
              <p className="text-sm text-gray-500">
                Strana {page} z {totalPages}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page <= 1}>
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </AdminLayout>
  );
};
