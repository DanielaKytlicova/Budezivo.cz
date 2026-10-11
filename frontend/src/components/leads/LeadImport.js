import React, { useRef, useState } from 'react';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { leadsApi } from '../../services/leadsApi';

const labels = { new: 'Nová', duplicate: 'Přeskočit duplicitu', error: 'Chyba' };
const maxBytes = 3 * 1024 * 1024;

function template() {
  const csv =
    '\ufeffNázev;Typ;Město;Kraj;Web;Odkaz na programy;Jméno kontaktu;Příjmení kontaktu;E-mail;Telefon;Interní poznámka\r\n';
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'budezivo-sablona-instituce.csv';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(new Error('Soubor nelze načíst. Vyberte jej znovu.'));
    reader.readAsDataURL(file);
  });
}

export default function LeadImport({ onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [payload, setPayload] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);

  const choose = (event) => {
    generation.current += 1;
    setFile(event.target.files?.[0] || null);
    setPreview(null);
    setPayload(null);
    setResult(null);
    setError('');
  };
  const inspect = async () => {
    if (!file || busy) return;
    if (file.size > maxBytes) {
      setError('Soubor může mít nejvýše 3 MB.');
      return;
    }
    if (!/\.(csv|xlsx|xls)$/i.test(file.name)) {
      setError('Vyberte soubor CSV, XLSX nebo XLS.');
      return;
    }
    const current = generation.current;
    setBusy(true);
    setError('');
    setPreview(null);
    try {
      const body = { filename: file.name, content: await readFile(file) };
      const report = await leadsApi('/import/preview', { method: 'POST', body });
      if (current === generation.current) {
        setPayload(body);
        setPreview(report);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const confirm = async () => {
    if (!preview?.new || !payload || busy) return;
    setBusy(true);
    setError('');
    try {
      const report = await leadsApi('/import', {
        method: 'POST',
        body: { ...payload, preview_digest: preview.preview_digest },
      });
      setResult(report);
      setPreview(null);
      setPayload(null);
      onImported();
    } catch (e) {
      // Always require another preview after an uncertain response or concurrent change.
      setPreview(null);
      setPayload(null);
      setError(`${e.message} Před dalším pokusem znovu zobrazte náhled.`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open onOpenChange={(open) => !open && !busy && onClose()}>
      <DialogContent
        className="leads-app lead-import-dialog"
        onInteractOutside={(event) => event.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Import institucí z tabulky</DialogTitle>
          <DialogDescription>
            Nahrajte Excel nebo CSV, zkontrolujte náhled a potvrďte přidání nových institucí.
            Existující záznamy se nepřepisují.
          </DialogDescription>
        </DialogHeader>
        <p className="text-sm">
          Podporujeme XLSX, XLS a CSV (čárka, středník nebo tabulátor), nejvýše 3 MB a 500 řádků. Z
          Excelu se načítá první list. První řádek obsahuje názvy sloupců; povinný je pouze Název.
          Přijímáme také anglické názvy polí z exportu CRM.
        </p>
        <Button variant="outline" onClick={template}>
          Stáhnout vzor CSV pro Excel
        </Button>
        <label>
          Soubor s institucemi
          <input type="file" accept=".xlsx,.xls,.csv" disabled={busy} onChange={choose} />
        </label>
        <p className="text-xs text-slate-600">
          Shodný název a město (bez ohledu na velikost písmen a diakritiku) označíme jako duplicitu,
          včetně archivovaných institucí a opakování v souboru. Nové instituce budou nepřidělené.
          Bez souřadnic se zobrazí v seznamu a pipeline; do mapy se přidají po doplnění polohy.
        </p>
        {error && (
          <p role="alert" className="lead-error">
            {error}
          </p>
        )}
        {result ? (
          <div role="status" className="lead-import-success">
            Přidáno institucí: <strong>{result.imported}</strong>. Přeskočeno duplicit:{' '}
            {result.duplicates}. Řádků s chybou: {result.errors}.
          </div>
        ) : (
          <Button variant="outline" onClick={inspect} disabled={!file || busy}>
            {busy ? 'Zpracovávám…' : 'Zobrazit náhled'}
          </Button>
        )}
        {preview && (
          <>
            <p role="status">
              Celkem: {preview.total} · <strong>Nové: {preview.new}</strong> · Duplicity:{' '}
              {preview.duplicates} · Chyby: {preview.errors}
            </p>
            {preview.ignored_columns.length > 0 && (
              <p className="lead-notice">
                Tyto sloupce nepoužijeme: {preview.ignored_columns.join(', ')}.
              </p>
            )}
            <div className="lead-import-table" tabIndex={0} aria-label="Náhled importu">
              <table>
                <thead>
                  <tr>
                    <th>Řádek</th>
                    <th>Instituce</th>
                    <th>Město</th>
                    <th>Výsledek kontroly</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row) => (
                    <tr key={row.row}>
                      <td>{row.row}</td>
                      <td>{row.name || 'Chybí název'}</td>
                      <td>{row.city || '—'}</td>
                      <td>
                        <strong>{labels[row.status]}</strong>
                        {row.message && <p>{row.message}</p>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm">
              Přidají se pouze řádky označené Nová. Duplicity a chybné řádky se přeskočí.
            </p>
            <Button onClick={confirm} disabled={busy || !preview.new}>
              {busy ? 'Importuji…' : `Importovat instituce (${preview.new})`}
            </Button>
          </>
        )}
        <Button variant="outline" onClick={onClose} disabled={busy}>
          {result ? 'Hotovo' : 'Zavřít'}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
