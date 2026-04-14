import React, { useEffect, useState, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';
import { Archive, RotateCcw, FileText, Users, Calendar, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { API } from '../../config/api';

export const ArchivePage = () => {
  const { user } = useContext(AuthContext);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reportDialog, setReportDialog] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [expandedSchools, setExpandedSchools] = useState(false);

  const fetchArchived = async () => {
    try {
      const res = await axios.get(`${API}/programs/archived`);
      setPrograms(res.data);
    } catch (err) {
      toast.error('Chyba při načítání archivu');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchArchived(); }, []);

  const handleUnarchive = async (id) => {
    try {
      await axios.post(`${API}/programs/${id}/unarchive`);
      toast.success('Program obnoven mezi aktivní');
      fetchArchived();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při obnovení');
    }
  };

  const handleOpenReport = async (program) => {
    setReportDialog(program);
    setReportLoading(true);
    setReportData(null);
    setExpandedSchools(false);
    try {
      const res = await axios.get(`${API}/programs/${program.id}/archive-report`);
      setReportData(res.data);
    } catch (err) {
      toast.error('Chyba při generování reportu');
    } finally {
      setReportLoading(false);
    }
  };

  const handleExportJSON = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `archiv_${reportData.program?.name || 'program'}_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success('Report exportován');
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Archive className="w-6 h-6 text-slate-600" />
          <h1 className="text-2xl font-bold text-slate-900" data-testid="archive-title">Archiv programů</h1>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-slate-800 mx-auto" />
          </div>
        ) : programs.length === 0 ? (
          <Card className="p-12 text-center" data-testid="archive-empty">
            <Archive className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500">Archiv je prázdný</p>
            <p className="text-sm text-gray-400 mt-1">Programy se sem přesunou po vypršení platnosti nebo ručním archivováním.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {programs.map(p => (
              <Card key={p.id} className="p-4 md:p-5" data-testid={`archived-program-${p.id}`}>
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-slate-900">{p.name_cs || p.name_en || 'Program'}</h3>
                      <Badge variant="outline" className="text-xs bg-gray-100">Archivováno</Badge>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500">
                      {p.archived_at && (
                        <span>Archivováno: {new Date(p.archived_at).toLocaleDateString('cs-CZ')}</span>
                      )}
                      {p.archive_reason && (
                        <span className="italic">{p.archive_reason}</span>
                      )}
                      {p.age_group && <span>Věková skupina: {p.age_group}</span>}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleOpenReport(p)}
                      data-testid={`report-${p.id}`}
                    >
                      <FileText className="w-4 h-4 mr-1" />
                      Report
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleUnarchive(p.id)}
                      className="bg-slate-800 hover:bg-slate-700 text-white"
                      data-testid={`unarchive-${p.id}`}
                    >
                      <RotateCcw className="w-4 h-4 mr-1" />
                      Obnovit
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Report dialog */}
      <Dialog open={!!reportDialog} onOpenChange={() => setReportDialog(null)}>
        <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-2xl max-h-[85vh] overflow-y-auto" aria-describedby="report-desc">
          <DialogHeader>
            <DialogTitle>
              Archivní report: {reportDialog?.name_cs || reportDialog?.name_en}
            </DialogTitle>
          </DialogHeader>
          <p id="report-desc" className="sr-only">Detailní report archivovaného programu</p>

          {reportLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800 mx-auto" />
            </div>
          ) : reportData ? (
            <div className="space-y-5" data-testid="archive-report">
              {/* Program Info */}
              <Card className="p-4 space-y-2 bg-slate-50">
                <h3 className="font-semibold text-slate-800">Program</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-gray-500">Název:</span> {reportData.program.name}</div>
                  <div><span className="text-gray-500">Věková skupina:</span> {reportData.program.age_group || '-'}</div>
                  <div><span className="text-gray-500">Kapacita:</span> {reportData.program.capacity}</div>
                  <div><span className="text-gray-500">Cena:</span> {reportData.program.price ? `${reportData.program.price} Kč` : 'Zdarma'}</div>
                  {reportData.program.archive_reason && (
                    <div className="col-span-2"><span className="text-gray-500">Důvod archivace:</span> {reportData.program.archive_reason}</div>
                  )}
                </div>
              </Card>

              {/* Statistics */}
              <Card className="p-4 space-y-3">
                <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                  <Users className="w-4 h-4" /> Statistiky
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Rezervací celkem', value: reportData.statistics.total_reservations },
                    { label: 'Potvrzených', value: reportData.statistics.confirmed },
                    { label: 'Dokončených', value: reportData.statistics.completed },
                    { label: 'Zrušených', value: reportData.statistics.cancelled },
                    { label: 'Studentů celkem', value: reportData.statistics.total_students },
                    { label: 'Pedagogů celkem', value: reportData.statistics.total_teachers },
                    { label: 'Unikátních škol', value: reportData.statistics.unique_schools },
                    { label: 'Zpětných vazeb', value: reportData.feedback_count },
                  ].map((s, i) => (
                    <div key={i} className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-slate-800">{s.value}</p>
                      <p className="text-xs text-gray-500">{s.label}</p>
                    </div>
                  ))}
                </div>
                {reportData.statistics.date_range?.from && (
                  <p className="text-xs text-gray-400">
                    Období: {reportData.statistics.date_range.from} — {reportData.statistics.date_range.to}
                  </p>
                )}
              </Card>

              {/* Schools */}
              {Object.keys(reportData.schools || {}).length > 0 && (
                <Card className="p-4 space-y-2">
                  <button
                    className="flex items-center justify-between w-full"
                    onClick={() => setExpandedSchools(!expandedSchools)}
                  >
                    <h3 className="font-semibold text-slate-800">Zúčastněné školy ({Object.keys(reportData.schools).length})</h3>
                    {expandedSchools ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSchools && (
                    <div className="space-y-1">
                      {Object.entries(reportData.schools).map(([name, data]) => (
                        <div key={name} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                          <span className="font-medium">{name}</span>
                          <span className="text-gray-500">{data.visits}x | {data.students} studentů | {data.last_visit}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              )}

              {/* Export */}
              <Button
                onClick={handleExportJSON}
                variant="outline"
                className="w-full"
                data-testid="export-report"
              >
                <Download className="w-4 h-4 mr-2" />
                Exportovat report (JSON)
              </Button>
            </div>
          ) : (
            <p className="text-center py-8 text-gray-400">Nepodařilo se načíst report.</p>
          )}
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};

export default ArchivePage;
