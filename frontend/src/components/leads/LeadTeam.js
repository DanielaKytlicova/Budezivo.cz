import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { leadsApi, allLeads } from '../../services/leadsApi';
import { dateText } from './LeadDetail';

const blank = { username: '', first_name: '', last_name: '', active: true, password: '' };
export default function LeadTeam() {
  const [accounts, setAccounts] = useState([]),
    [items, setItems] = useState([]),
    [form, setForm] = useState(blank),
    [editing, setEditing] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [message, setMessage] = useState('');
  const [selected, setSelected] = useState([]),
    [assignee, setAssignee] = useState('');
  const load = async () => {
    const [team, leads] = await Promise.all([leadsApi('/team'), allLeads()]);
    setAccounts(team);
    setItems(leads);
  };
  useEffect(() => {
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await leadsApi(editing ? `/team/${editing}` : '/team', {
        method: editing ? 'PUT' : 'POST',
        body: { ...form, password: form.password || null },
      });
      setForm(blank);
      setEditing(null);
      await load();
      setMessage('Účet byl uložen. Změna hesla nebo deaktivace ukončila jeho relace.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const assign = async () => {
    setBusy(true);
    setError('');
    try {
      await leadsApi('/assign', {
        method: 'POST',
        body: { lead_ids: selected, assignee_id: assignee || null },
      });
      setSelected([]);
      await load();
      setMessage('Přiřazení bylo uloženo.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="leads-app">
      <h1>Interní tým</h1>
      <p>
        Účty pro interní CRM. Spolupracovníci vidí všechny instituce a upravují pouze přidělené
        leady.
      </p>
      {loading && <p role="status">Načítám tým…</p>}
      {error && (
        <p role="alert" className="lead-error">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      <div className="lead-team-grid">
        <section className="lead-panel">
          <h2>{editing ? 'Upravit účet' : 'Nový spolupracovník'}</h2>
          <form onSubmit={save}>
            <fieldset disabled={busy}>
              {Object.entries({
                username: 'Uživatelské jméno',
                first_name: 'Jméno',
                last_name: 'Příjmení',
                password: editing
                  ? 'Nové heslo (prázdné = beze změny)'
                  : 'Počáteční heslo (alespoň 12 znaků)',
              }).map(([key, label]) => (
                <label key={key}>
                  {label}
                  <Input
                    required={key !== 'password' || !editing}
                    minLength={key === 'password' ? 12 : undefined}
                    maxLength={key === 'password' ? 72 : 80}
                    autoComplete={key === 'password' ? 'new-password' : 'off'}
                    type={key === 'password' ? 'password' : 'text'}
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  />
                </label>
              ))}
              <label className="lead-check">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                />{' '}
                Aktivní účet
              </label>
              <Button type="submit">{busy ? 'Ukládám…' : 'Uložit účet'}</Button>
              {editing && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setEditing(null);
                    setForm(blank);
                  }}
                >
                  Zrušit úpravu
                </Button>
              )}
            </fieldset>
          </form>
        </section>
        <section className="lead-panel">
          <h2>Spolupracovníci</h2>
          {!loading && !accounts.length && <p>Zatím žádné interní účty.</p>}
          {accounts.map((a) => (
            <article key={a.id} className="lead-history">
              <strong>
                {a.first_name} {a.last_name} · {a.username}
              </strong>
              <p>
                {a.active ? 'Aktivní' : 'Neaktivní'} · {a.assigned_count} leadů
              </p>
              <small>Poslední přihlášení: {dateText(a.last_login_at)}</small>
              <Button
                variant="outline"
                onClick={() => {
                  setEditing(a.id);
                  setForm({
                    username: a.username,
                    first_name: a.first_name,
                    last_name: a.last_name,
                    active: a.active,
                    password: '',
                  });
                }}
              >
                Upravit účet / heslo
              </Button>
            </article>
          ))}
        </section>
      </div>
      <section className="lead-panel">
        <h2>Přiřazení leadů</h2>
        <div className="lead-toolbar">
          <label>
            Nový pracovník
            <select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
              <option value="">Nepřiděleno</option>
              {accounts
                .filter((a) => a.active)
                .map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.first_name} {a.last_name}
                  </option>
                ))}
            </select>
          </label>
          <Button disabled={busy || !selected.length} onClick={assign}>
            Přeřadit vybrané ({selected.length})
          </Button>
        </div>
        <div className="lead-assignment-list">
          {items.map((item) => (
            <label className="lead-check" key={item.id}>
              <input
                type="checkbox"
                checked={selected.includes(item.id)}
                onChange={(e) =>
                  setSelected((old) =>
                    e.target.checked ? [...old, item.id] : old.filter((id) => id !== item.id)
                  )
                }
              />
              <span>
                {item.name} ·{' '}
                {accounts.find((a) => a.id === item.assignee_id)?.username || 'Nepřiděleno'}
              </span>
            </label>
          ))}
        </div>
      </section>
    </div>
  );
}
