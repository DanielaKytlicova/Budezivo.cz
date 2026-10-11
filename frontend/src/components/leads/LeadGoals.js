import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { leadsApi } from '../../services/leadsApi';

export default function LeadGoals({ goals, actor, onSaved }) {
  const [edit, setEdit] = useState(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const { id, name, metric, target, deadline, cluster } = edit;
      await leadsApi(id ? `/goals/${id}` : '/goals', {
        method: id ? 'PUT' : 'POST',
        body: { name, metric, target: Number(target), deadline, cluster: cluster || null },
      });
      setEdit(null);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="lead-panel">
      <div className="lead-toolbar">
        <h2>Cíle a aktivace</h2>
        {actor.superadmin && (
          <Button
            variant="outline"
            onClick={() =>
              setEdit({
                name: '',
                metric: 'connected',
                target: 1,
                deadline: '2027-01-31',
                cluster: '',
              })
            }
          >
            Nový cíl
          </Button>
        )}
      </div>
      <div className="lead-goals">
        {goals.map((g) => (
          <article key={g.id}>
            <strong>{g.name}</strong>
            <p>
              {g.current} / {g.target} · {g.percent} %
            </p>
            <progress value={g.current} max={g.target} aria-label={g.name} />
            <small>
              Do {new Date(g.deadline).toLocaleDateString('cs-CZ')}
              {g.cluster && ` · ${g.cluster}`}
            </small>
            {actor.superadmin && (
              <button className="lead-link" onClick={() => setEdit(g)}>
                Upravit cíl
              </button>
            )}
          </article>
        ))}
      </div>
      <p className="text-xs text-slate-600">
        Připojené = tři stavy „Připojeno“. Platící = „Připojeno – platící“. Programy = ověřené počty
        u připojených institucí. Archivované záznamy se nezapočítávají.
      </p>
      {error && (
        <p role="alert" className="lead-error">
          {error}
        </p>
      )}
      {edit && (
        <form onSubmit={save}>
          <fieldset disabled={busy}>
            <div className="lead-field-grid">
              <label>
                Název
                <Input
                  required
                  maxLength={200}
                  value={edit.name}
                  onChange={(e) => setEdit({ ...edit, name: e.target.value })}
                />
              </label>
              <label>
                Metrika
                <select
                  value={edit.metric}
                  onChange={(e) => setEdit({ ...edit, metric: e.target.value })}
                >
                  <option value="connected">Připojené instituce</option>
                  <option value="paying">Platící instituce</option>
                  <option value="programs">Programy v katalogu</option>
                </select>
              </label>
              <label>
                Cílové číslo
                <Input
                  type="number"
                  min="1"
                  required
                  value={edit.target}
                  onChange={(e) => setEdit({ ...edit, target: e.target.value })}
                />
              </label>
              <label>
                Termín
                <Input
                  type="date"
                  required
                  value={edit.deadline}
                  onChange={(e) => setEdit({ ...edit, deadline: e.target.value })}
                />
              </label>
              <label>
                Klastr (prázdný = všechny)
                <Input
                  maxLength={150}
                  value={edit.cluster || ''}
                  onChange={(e) => setEdit({ ...edit, cluster: e.target.value })}
                />
              </label>
            </div>
            <Button type="submit">Uložit cíl</Button>
            <Button type="button" variant="outline" onClick={() => setEdit(null)}>
              Zrušit
            </Button>
          </fieldset>
        </form>
      )}
    </section>
  );
}
