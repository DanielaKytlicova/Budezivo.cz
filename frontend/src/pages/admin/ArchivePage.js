import React, { useEffect, useState, useContext } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { AuthContext } from '../../context/AuthContext';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { toast } from 'sonner';
import axios from 'axios';
import { Archive, RotateCcw, FileText, Users, Calendar, Download, ChevronDown, ChevronUp, Pencil, Loader2 } from 'lucide-react';
import { API } from '../../config/api';

export const ArchivePage = () => {
  const { user } = useContext(AuthContext);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reportDialog, setReportDialog] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [expandedSchools, setExpandedSchools] = useState(false);

  // Edit-archived dialog state
  const [editDialog, setEditDialog] = useState(null); // full program object
  const [editForm, setEditForm] = useState({});
  const [editSaving, setEditSaving] = useState(false);

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
      const res = await axios.get(`${API}/programs/${program.id}/archive-report`, { params: { format: 'json' } });
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

  // ---- PDF export — direct download (custom text comes from the program's
  // saved `archive_custom_text` field, set via the Edit dialog).
  const handleDownloadPdf = async (program) => {
    try {
      const res = await axios.get(`${API}/programs/${program.id}/archive-report`, {
        params: { format: 'pdf' },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      const name = (program.name_cs || program.name_en || 'program').replace(/[^\p{L}\p{N}_-]/gu, '_').slice(0, 60);
      link.download = `archivni_zprava_${name}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success('PDF staženo');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Chyba při generování PDF');
    }
  };

  // ---- Inline edit of editable archived-program fields ----
  // Lecturer can update fields they originally filled; statistics & feedback
  // remain read-only (computed from historical bookings).
  const openEditDialog = (program) => {
    setEditDialog(program);
    setEditForm({
      name_cs: program.name_cs || '',
      name_en: program.name_en || '',
      description_cs: program.description_cs || '',
      description_en: program.description_en || '',
      age_group: program.age_group || '',
      duration: program.duration ?? '',
      min_capacity: program.min_capacity ?? '',
      max_capacity: program.max_capacity ?? '',
      price: program.price ?? '',
      pricing_info: program.pricing_info || '',
      image_url: program.image_url || '',
      archive_custom_text: program.archive_custom_text || '',
    });
  };

  const handleSaveEdit = async () => {
    if (!editDialog) return;
    setEditSaving(true);
    try {
      // Merge new edited fields into the existing program payload (PUT
      // requires the full ProgramCreate shape — preserve everything else).
      const merged = {
        ...editDialog,
        name_cs: editForm.name_cs?.trim() || editDialog.name_cs,
        name_en: editForm.name_en?.trim() || null,
        description_cs: editForm.description_cs ?? null,
        description_en: editForm.description_en ?? null,
        age_group: editForm.age_group || editDialog.age_group,
        duration: editForm.duration === '' ? null : Number(editForm.duration),
        min_capacity: editForm.min_capacity === '' ? null : Number(editForm.min_capacity),
        max_capacity: editForm.max_capacity === '' ? null : Number(editForm.max_capacity),
        price: editForm.price === '' ? null : Number(editForm.price),
        pricing_info: editForm.pricing_info ?? null,
        image_url: editForm.image_url?.trim() || null,
        archive_custom_text: editForm.archive_custom_text?.trim() || null,
      };
      // Strip server-managed fields that PUT doesn't expect on the body.
      delete merged.id;
      delete merged.created_at;
      delete merged.updated_at;
      delete merged.archived_at;
      delete merged.archived_by;
      delete merged.institution_id;
      await axios.put(`${API}/programs/${editDialog.id}`, merged);
      toast.success('Program aktualizován');
      setEditDialog(null);
      fetchArchived();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Uložení selhalo');
    } finally {
      setEditSaving(false);
    }
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
                  <div className="flex gap-2 flex-wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openEditDialog(p)}
                      data-testid={`edit-archived-${p.id}`}
                    >
                      <Pencil className="w-4 h-4 mr-1" />
                      Upravit
                    </Button>
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
                      variant="outline"
                      onClick={() => handleDownloadPdf(p)}
                      data-testid={`export-pdf-${p.id}`}
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Stáhnout PDF
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
          ) : reportData && reportData.program ? (
            <div className="space-y-5" data-testid="archive-report">
              {/* Program Info */}
              <Card className="p-4 space-y-2 bg-slate-50">
                <h3 className="font-semibold text-slate-800">Program</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-gray-500">Název:</span> {reportData.program.name || '-'}</div>
                  <div><span className="text-gray-500">Věková skupina:</span> {reportData.program.age_group || '-'}</div>
                  <div><span className="text-gray-500">Kapacita:</span> {reportData.program.capacity ?? '-'}</div>
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
                    { label: 'Rezervací celkem', value: reportData.statistics?.total_reservations ?? 0 },
                    { label: 'Potvrzených', value: reportData.statistics?.confirmed ?? 0 },
                    { label: 'Dokončených', value: reportData.statistics?.completed ?? 0 },
                    { label: 'Zrušených', value: reportData.statistics?.cancelled ?? 0 },
                    { label: 'Studentů celkem', value: reportData.statistics?.total_students ?? 0 },
                    { label: 'Pedagogů celkem', value: reportData.statistics?.total_teachers ?? 0 },
                    { label: 'Unikátních škol', value: reportData.statistics?.unique_schools ?? 0 },
                    { label: 'Zpětných vazeb', value: reportData.feedback_count ?? 0 },
                  ].map((s, i) => (
                    <div key={i} className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-slate-800">{s.value}</p>
                      <p className="text-xs text-gray-500">{s.label}</p>
                    </div>
                  ))}
                </div>
                {reportData.statistics?.date_range?.from && (
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

      {/* Edit-archived-program dialog — only fields the lecturer originally
          filled. Statistics & feedback remain read-only. */}
      <Dialog open={!!editDialog} onOpenChange={(o) => !o && setEditDialog(null)}>
        <DialogContent className="w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-2xl max-h-[85vh] overflow-y-auto" aria-describedby="edit-desc">
          <DialogHeader>
            <DialogTitle>Upravit archivovaný program</DialogTitle>
          </DialogHeader>
          <p id="edit-desc" className="sr-only">Upravte pole, která jste vyplnili při založení programu. Tabulky rezervací a zpětnou vazbu měnit nelze.</p>

          {editDialog && (
            <div className="space-y-4 text-sm" data-testid="edit-archived-form">
              <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Statistiky, rezervace a zpětná vazba se z bezpečnostních důvodů nedají měnit — odráží historickou skutečnost.
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="edit-name-cs">Název (CZ)</Label>
                  <Input id="edit-name-cs" data-testid="edit-name-cs"
                    value={editForm.name_cs}
                    onChange={(e) => setEditForm(f => ({ ...f, name_cs: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="edit-name-en">Název (EN)</Label>
                  <Input id="edit-name-en" data-testid="edit-name-en"
                    value={editForm.name_en}
                    onChange={(e) => setEditForm(f => ({ ...f, name_en: e.target.value }))}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="edit-desc-cs">Popis programu (CZ)</Label>
                <Textarea id="edit-desc-cs" data-testid="edit-desc-cs"
                  className="min-h-[140px]"
                  value={editForm.description_cs}
                  onChange={(e) => setEditForm(f => ({ ...f, description_cs: e.target.value }))}
                />
                <p className="text-[11px] text-gray-400 mt-1">Tento text se objeví v PDF jako sekce „O programu — co se žáci naučí".</p>
              </div>

              <div>
                <Label htmlFor="edit-desc-en">Popis programu (EN)</Label>
                <Textarea id="edit-desc-en" data-testid="edit-desc-en"
                  className="min-h-[80px]"
                  value={editForm.description_en}
                  onChange={(e) => setEditForm(f => ({ ...f, description_en: e.target.value }))}
                />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div>
                  <Label htmlFor="edit-age">Věková skupina</Label>
                  <Input id="edit-age" data-testid="edit-age"
                    value={editForm.age_group}
                    onChange={(e) => setEditForm(f => ({ ...f, age_group: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="edit-duration">Délka (min)</Label>
                  <Input id="edit-duration" data-testid="edit-duration" type="number" min="1"
                    value={editForm.duration}
                    onChange={(e) => setEditForm(f => ({ ...f, duration: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="edit-price">Cena (Kč)</Label>
                  <Input id="edit-price" data-testid="edit-price" type="number" min="0"
                    value={editForm.price}
                    onChange={(e) => setEditForm(f => ({ ...f, price: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="edit-min-cap">Min. kapacita</Label>
                  <Input id="edit-min-cap" data-testid="edit-min-cap" type="number" min="0"
                    value={editForm.min_capacity}
                    onChange={(e) => setEditForm(f => ({ ...f, min_capacity: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="edit-max-cap">Max. kapacita</Label>
                  <Input id="edit-max-cap" data-testid="edit-max-cap" type="number" min="0"
                    value={editForm.max_capacity}
                    onChange={(e) => setEditForm(f => ({ ...f, max_capacity: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="edit-pricing-info">Cenová info (text)</Label>
                  <Input id="edit-pricing-info" data-testid="edit-pricing-info"
                    value={editForm.pricing_info}
                    onChange={(e) => setEditForm(f => ({ ...f, pricing_info: e.target.value }))}
                    placeholder="např. 30 Kč / žák, pedagog zdarma"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="edit-image">URL úvodního obrázku <span className="text-gray-400 text-xs">(pro Hero variantu PDF)</span></Label>
                <Input id="edit-image" data-testid="edit-image"
                  value={editForm.image_url}
                  onChange={(e) => setEditForm(f => ({ ...f, image_url: e.target.value }))}
                  placeholder="https://… nebo /uploads/programs/…"
                />
                <p className="text-[11px] text-gray-400 mt-1">Pokud je vyplněno, PDF dostane úvodní stránku přes celou plochu s tímto obrázkem.</p>
              </div>

              <div>
                <Label htmlFor="edit-custom-text">
                  Vlastní poznámka v PDF <span className="text-gray-400 text-xs">(volitelné)</span>
                </Label>
                <Textarea id="edit-custom-text" data-testid="edit-custom-text"
                  className="min-h-[120px]"
                  value={editForm.archive_custom_text}
                  onChange={(e) => setEditForm(f => ({ ...f, archive_custom_text: e.target.value.slice(0, 2000) }))}
                  placeholder="Např. „Program byl realizován v rámci výstavy XYZ, doplňující kurátorský komentář…“&#10;&#10;Více odstavců můžete oddělit prázdným řádkem."
                />
                <p className="text-[11px] text-gray-400 mt-1">
                  Text se v PDF zobrazí jako sekce „Poznámka" hned za přehledem programu. {(editForm.archive_custom_text || '').length}/2000
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog(null)} disabled={editSaving}>
              Zrušit
            </Button>
            <Button
              onClick={handleSaveEdit}
              disabled={editSaving}
              className="bg-slate-800 hover:bg-slate-700 text-white"
              data-testid="edit-archived-save"
            >
              {editSaving ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Ukládám…</>
              ) : (
                <>Uložit změny</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
};

export default ArchivePage;
