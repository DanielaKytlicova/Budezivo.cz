import React, { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { leadsApi } from '../../services/leadsApi';

const fields = [
  ['name', 'Název'],
  ['type', 'Typ instituce'],
  ['type_label', 'Zobrazovaný typ'],
  ['city', 'Město'],
  ['region', 'Kraj'],
  ['cluster', 'Klastr'],
  ['address', 'Adresa'],
  ['country', 'Země'],
  ['postal_code', 'PSČ'],
  ['district', 'Okres'],
  ['lat', 'Zeměpisná šířka', 'number'],
  ['lng', 'Zeměpisná délka', 'number'],
  ['location_accuracy', 'Přesnost / zdroj polohy'],
  ['programs', 'Počet / rozsah programů'],
  ['catalog_programs', 'Ověřený počet programů v katalogu', 'number'],
  ['booking', 'Způsob rezervace'],
  ['online', 'Viditelné online termíny'],
  ['online_completion', 'Dokončení rezervace online'],
  ['regularity', 'Pravidelnost nabídky'],
  ['score', 'Potenciál 0–100', 'number'],
  ['catalog', 'Katalogová hodnota'],
  ['catalog_role', 'Role instituce pro katalog'],
  ['activity', 'Obchodní zařazení'],
  ['relationship', 'Dosavadní vztah'],
  ['website_url', 'Web instituce', 'url'],
  ['program_url', 'URL nabídky programů', 'url'],
  ['last_contact', 'Poslední kontakt', 'date'],
  ['next_action_date', 'Termín dalšího kroku', 'date'],
  ['why', 'Důvod zajímavosti', 'textarea'],
  ['next_action', 'Další krok', 'textarea'],
  ['result_reason', 'Důvod výsledku / odmítnutí / odložení', 'textarea'],
  ['internal_note', 'Individuální interní poznámka', 'textarea'],
];
const contactFields = [
  ['first_name', 'Jméno kontaktu'],
  ['last_name', 'Příjmení kontaktu'],
  ['position', 'Pozice / oddělení'],
  ['email', 'Pracovní e-mail (více adres oddělte středníkem)'],
  ['phone', 'Pracovní telefon'],
  ['note', 'Poznámka ke kontaktu'],
];
export const dateText = (value) => (value ? new Date(value).toLocaleString('cs-CZ') : '—');
const display = (value) =>
  value === null || value === ''
    ? '—'
    : typeof value === 'object'
      ? JSON.stringify(value)
      : String(value);

export default function LeadDetail({ id, metadata, actor, onClose, onSaved }) {
  const titleRef = useRef(null);
  const firstStage = metadata.stages[0];
  const [item, setItem] = useState(null),
    [form, setForm] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState('');
  const [activity, setActivity] = useState({
    kind: 'note',
    subject: '',
    body: '',
    occurred_at: '',
  });
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setItem(null);
    setError('');
    setMessage('');
    if (id === 'new') {
      setItem({ can_edit: true });
      setForm({ name: '', type: 'museum', stage: firstStage, plan: 'ověřit', contact: {} });
      return;
    }
    leadsApi(`/${id}`)
      .then((data) => {
        if (!active) return;
        setItem(data);
        const { contacts, activities, audit, can_edit, ...values } = data;
        const primary = contacts.find((c) => c.primary) || {};
        setForm({
          ...values,
          contact: Object.fromEntries(contactFields.map(([key]) => [key, primary[key] || ''])),
        });
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [id, reload, firstStage]);
  useEffect(() => {
    if (item) titleRef.current?.focus();
  }, [item]);
  const set = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const values = Object.fromEntries(
        [
          ...fields.map(([key]) => key),
          'stage',
          'plan',
          'contact',
          ...(actor.superadmin ? ['assignee_id', 'archived'] : []),
        ]
          .filter((key) => form[key] !== undefined)
          .map((key) => [key, form[key]])
      );
      const result = await leadsApi(id === 'new' ? '' : `/${id}`, {
        method: id === 'new' ? 'POST' : 'PATCH',
        body: id === 'new' ? values : { version: item.version, changes: values },
      });
      setMessage('Změny byly uloženy.');
      onSaved(result.id);
      setReload((v) => v + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const addActivity = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await leadsApi(`/${id}/activities`, {
        method: 'POST',
        body: { ...activity, occurred_at: new Date(activity.occurred_at).toISOString() },
      });
      setActivity({ kind: 'note', subject: '', body: '', occurred_at: '' });
      setReload((v) => v + 1);
      onSaved(id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="lead-detail" aria-label="Detail instituce">
      <div className="flex items-start justify-between gap-3">
        <h2 ref={titleRef} tabIndex={-1}>
          {item?.name || (id === 'new' ? 'Nová instituce' : 'Detail instituce')}
        </h2>
        <Button variant="outline" onClick={onClose}>
          Zavřít
        </Button>
      </div>
      {error && (
        <div role="alert" className="lead-error">
          {error}
          <Button variant="outline" onClick={() => setReload((v) => v + 1)}>
            Načíst znovu
          </Button>
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {!item || !form ? (
        <p role="status">Načítám detail…</p>
      ) : (
        <>
          {!item.can_edit && (
            <p className="lead-notice">
              Tento lead není přidělen vám nebo je archivovaný. Údaje můžete pouze číst.
            </p>
          )}
          {item.location_accuracy && (
            <p className="lead-notice">Poloha: {item.location_accuracy}</p>
          )}
          {item.program_url && (
            <a
              className="lead-link"
              href={item.program_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Otevřít nabídku programů ↗
            </a>
          )}
          <p className="text-sm text-slate-600">
            Naposledy upraveno: {dateText(item.updated_at)} ·{' '}
            {item.audit?.find((entry) => entry.actor_id === item.updated_by)?.actor_name ||
              item.updated_by ||
              'Nový záznam'}
          </p>
          <form onSubmit={save}>
            <fieldset disabled={!item.can_edit || busy}>
              <div className="lead-field-grid">
                <label>
                  Stav
                  <select value={form.stage} onChange={(e) => set('stage', e.target.value)}>
                    {metadata.stages.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Odhad tarifu
                  <select value={form.plan} onChange={(e) => set('plan', e.target.value)}>
                    {metadata.plans.map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                </label>
                {actor.superadmin && (
                  <>
                    <label>
                      Přidělený spolupracovník
                      <select
                        value={form.assignee_id || ''}
                        onChange={(e) => set('assignee_id', e.target.value || null)}
                      >
                        <option value="">Nepřiděleno</option>
                        {metadata.accounts.map((a) => (
                          <option key={a.id} value={a.id} disabled={!a.active}>
                            {a.name}
                            {a.active ? '' : ' (neaktivní)'}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="lead-check">
                      <input
                        type="checkbox"
                        checked={!!form.archived}
                        onChange={(e) => set('archived', e.target.checked)}
                      />{' '}
                      Archivováno
                    </label>
                  </>
                )}
                {fields.map(([key, label, type]) => (
                  <label key={key} className={type === 'textarea' ? 'lead-wide' : ''}>
                    {label}
                    {type === 'textarea' ? (
                      <Textarea
                        aria-label={label}
                        value={form[key] || ''}
                        maxLength={10000}
                        onChange={(e) => set(key, e.target.value)}
                      />
                    ) : (
                      <Input
                        type={type || 'text'}
                        step={type === 'number' ? 'any' : undefined}
                        required={['name', 'type'].includes(key)}
                        value={form[key] ?? ''}
                        maxLength={type === 'url' ? 2000 : 500}
                        onChange={(e) =>
                          set(
                            key,
                            type === 'number'
                              ? e.target.value === ''
                                ? ['lat', 'lng'].includes(key)
                                  ? null
                                  : 0
                                : Number(e.target.value)
                              : type === 'date'
                                ? e.target.value || null
                                : e.target.value
                          )
                        }
                      />
                    )}
                  </label>
                ))}
              </div>
              <h3>Primární pracovní kontakt</h3>
              <div className="lead-field-grid">
                {contactFields.map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <Input
                      value={form.contact[key] || ''}
                      maxLength={key === 'note' ? 5000 : 254}
                      onChange={(e) => set('contact', { ...form.contact, [key]: e.target.value })}
                    />
                  </label>
                ))}
              </div>
              {item.can_edit && (
                <Button type="submit" disabled={busy}>
                  {busy ? 'Ukládám…' : 'Uložit změny'}
                </Button>
              )}
            </fieldset>
          </form>
          {id !== 'new' && (
            <>
              <h3>Aktivity</h3>
              {item.can_edit && (
                <form onSubmit={addActivity}>
                  <fieldset disabled={busy}>
                    <div className="lead-field-grid">
                      <label>
                        Druh aktivity
                        <select
                          value={activity.kind}
                          onChange={(e) => setActivity({ ...activity, kind: e.target.value })}
                        >
                          {Object.entries({
                            email: 'E-mail',
                            phone: 'Telefonát',
                            meeting: 'Schůzka',
                            note: 'Interní poznámka',
                            status: 'Změna stavu',
                            other: 'Jiná aktivita',
                          }).map(([v, label]) => (
                            <option key={v} value={v}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Datum a čas
                        <Input
                          type="datetime-local"
                          required
                          value={activity.occurred_at}
                          onChange={(e) =>
                            setActivity({ ...activity, occurred_at: e.target.value })
                          }
                        />
                      </label>
                      <label className="lead-wide">
                        Předmět
                        <Input
                          required
                          maxLength={300}
                          value={activity.subject}
                          onChange={(e) => setActivity({ ...activity, subject: e.target.value })}
                        />
                      </label>
                      <label className="lead-wide">
                        Text
                        <Textarea
                          maxLength={10000}
                          value={activity.body}
                          onChange={(e) => setActivity({ ...activity, body: e.target.value })}
                        />
                      </label>
                    </div>
                    <Button type="submit">Přidat aktivitu</Button>
                  </fieldset>
                </form>
              )}
              {!item.activities?.length && <p>Zatím žádné aktivity.</p>}
              {item.activities?.map((a) => (
                <article className="lead-history" key={a.id}>
                  <strong>{a.subject}</strong>
                  <small>
                    {dateText(a.occurred_at)} · {a.actor_name} · {a.kind}
                  </small>
                  <p>{a.body}</p>
                </article>
              ))}
              <h3>Audit změn</h3>
              {!item.audit?.length && <p>Zatím žádné změny.</p>}
              {item.audit?.map((a) => (
                <article className="lead-history" key={a.id}>
                  <strong>{fields.find(([key]) => key === a.field)?.[1] || a.field}</strong>
                  <small>
                    {dateText(a.occurred_at)} · {a.actor_name} · {a.entity}
                  </small>
                  <p>
                    {display(a.old_value)} → {display(a.new_value)}
                  </p>
                </article>
              ))}
            </>
          )}
        </>
      )}
    </section>
  );
}
