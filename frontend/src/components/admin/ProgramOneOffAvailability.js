import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '../../config/api';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

const emptyForm = { date: '', start_time: '13:30', end_time: '15:00' };
const errorMessage = (error) => {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string'
    ? detail
    : 'Změnu se nepodařilo uložit. Zkontrolujte datum a čas.';
};

export const ProgramOneOffAvailability = ({ program, open, onOpenChange, onSaved, onDeleted }) => {
  const [slots, setSlots] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState(false);
  const listVersion = useRef(0);
  const endpoint = `${API}/availability-unified/program/${program?.id}/one-offs`;

  useEffect(() => {
    if (!program?.id) return;
    let active = true;
    const version = ++listVersion.current;
    axios
      .get(endpoint)
      .then(({ data }) => {
        if (active && version === listVersion.current) {
          setSlots(data);
          setLoadError(false);
        }
      })
      .catch(() => {
        if (active && version === listVersion.current) setLoadError(true);
      });
    return () => {
      active = false;
    };
  }, [endpoint, program?.id]);

  useEffect(() => {
    if (open) {
      setForm(emptyForm);
      setError('');
    }
  }, [open]);

  const save = async (event) => {
    event.preventDefault();
    if (busy || !program?.id) return;
    if (!form.date || !form.start_time || !form.end_time || form.end_time <= form.start_time) {
      setError('Vyplňte datum a čas. Konec musí být později než začátek.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const { data } = await axios.post(endpoint, form);
      listVersion.current += 1;
      setSlots((current) => [...current.filter((slot) => slot.id !== data.id), data]);
      toast.success(`Jednorázový termín programu „${program.name_cs}“ přidán.`);
      onOpenChange(false);
      onSaved(data.date);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (slot) => {
    if (
      busy ||
      !window.confirm(
        'Odstranit nabídku tohoto jednorázového termínu? Existující rezervace zůstanou zachované.'
      )
    )
      return;
    setBusy(true);
    try {
      await axios.delete(`${endpoint}/${slot.id}`);
      listVersion.current += 1;
      setSlots((current) => current.filter((item) => item.id !== slot.id));
      toast.success('Jednorázový termín odstraněn.');
      onDeleted();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Card className="p-4 md:p-6 space-y-3" data-testid="program-one-off-summary">
        <h2 className="font-semibold text-slate-900">Jednorázové termíny programu</h2>
        {loadError && (
          <p role="alert" className="text-sm text-red-600">
            Termíny se nepodařilo načíst. Obnovte stránku.
          </p>
        )}
        {!loadError && slots.length === 0 && (
          <p className="text-sm text-gray-500">Žádné jednorázové termíny.</p>
        )}
        {[...slots]
          .sort((a, b) => `${a.date} ${a.start_time}`.localeCompare(`${b.date} ${b.start_time}`))
          .map((slot) => (
            <div
              key={slot.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3"
            >
              <span className="text-sm">
                {slot.date} · {slot.start_time}–{slot.end_time}
              </span>
              <Button variant="outline" size="sm" disabled={busy} onClick={() => remove(slot)}>
                Odstranit
              </Button>
            </div>
          ))}
      </Card>
      <Dialog
        open={open}
        onOpenChange={(value) => {
          if (!busy) onOpenChange(value);
        }}
      >
        <DialogContent aria-describedby="program-one-off-description">
          <DialogHeader>
            <DialogTitle>Přidat jednorázový termín programu</DialogTitle>
          </DialogHeader>
          <p id="program-one-off-description" className="text-sm text-gray-600">
            {program?.name_cs} — termín platí pouze pro zadané datum. Stávající blokace a kontroly
            kolizí platí i pro tento termín.
          </p>
          <form onSubmit={save} className="space-y-4">
            <div>
              <Label htmlFor="program-one-off-date">Datum</Label>
              <Input
                id="program-one-off-date"
                type="date"
                required
                value={form.date}
                disabled={busy}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="program-one-off-start">Od</Label>
                <Input
                  id="program-one-off-start"
                  type="time"
                  required
                  value={form.start_time}
                  disabled={busy}
                  onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="program-one-off-end">Do</Label>
                <Input
                  id="program-one-off-end"
                  type="time"
                  required
                  value={form.end_time}
                  disabled={busy}
                  onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                />
              </div>
            </div>
            {error && (
              <p role="alert" className="text-sm text-red-600">
                {error}
              </p>
            )}
            <Button
              type="submit"
              disabled={busy || !program?.id}
              className="w-full"
              data-testid="program-one-off-submit"
            >
              {busy ? 'Ukládám…' : 'Přidat termín programu'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};
