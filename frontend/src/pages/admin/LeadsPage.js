import React, { useCallback, useContext, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Map, Columns3, Plus, Download, Upload, RotateCcw } from 'lucide-react';
import { AuthContext } from '../../context/AuthContext';
import { AdminLayout, BudezivoLogo } from '../../components/layout/AdminLayout';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import LeadMap from '../../components/leads/LeadMap';
import LeadDetail from '../../components/leads/LeadDetail';
import LeadTeam from '../../components/leads/LeadTeam';
import LeadGoals from '../../components/leads/LeadGoals';
import LeadImport from '../../components/leads/LeadImport';
import {
  leadsApi,
  leadLogin,
  clearLeadSession,
  allLeads,
  leadQuery,
  pipelineGroup,
  stageClass,
} from '../../services/leadsApi';
import '../../components/leads/leads.css';

const emptyFilters = {
  q: '',
  type: '',
  region: '',
  cluster: '',
  plan: '',
  stage: '',
  connected: false,
  mine: false,
  assignee: '',
  due: '',
  archived: false,
};
const groups = [
  'Výzkum',
  'K oslovení',
  'V kontaktu',
  'Odloženo / odmítli',
  'Připojeno',
  'Pouze katalog',
];

function Workspace({ actor }) {
  const [metadata, setMetadata] = useState(null),
    [filters, setFilters] = useState(emptyFilters),
    [items, setItems] = useState([]),
    [goals, setGoals] = useState([]),
    [selected, setSelected] = useState(null),
    [view, setView] = useState('map'),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0),
    [exporting, setExporting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([leadsApi('/metadata'), leadsApi('/goals')])
      .then(([m, g]) => {
        if (active) {
          setMetadata(m);
          setGoals(g);
        }
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [revision]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    const timer = setTimeout(
      () =>
        allLeads(filters)
          .then((rows) => {
            if (active) setItems(rows);
          })
          .catch((e) => {
            if (active) {
              setError(e.message);
              setItems([]);
            }
          })
          .finally(() => active && setLoading(false)),
      200
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [filters, revision]);
  const setFilter = (key, value) => setFilters((old) => ({ ...old, [key]: value }));
  const saved = (id) => {
    if (id) setSelected(id);
    setRevision((v) => v + 1);
  };
  const download = async () => {
    setExporting(true);
    setError('');
    try {
      const blob = await leadsApi(`/export?${leadQuery(filters)}`, { download: true });
      const url = URL.createObjectURL(blob),
        link = document.createElement('a');
      link.href = url;
      link.download = 'budezivo-leady.csv';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e.message);
    } finally {
      setExporting(false);
    }
  };
  const card = (item) => (
    <button
      key={item.id}
      className={`lead-card ${selected === item.id ? 'selected' : ''}`}
      onClick={() => setSelected(item.id)}
    >
      <strong>{item.name}</strong>
      <small>
        {item.city} · {item.type_label || item.type} · {item.plan}
      </small>
      <span className={`lead-stage ${stageClass(item.stage)}`}>{item.stage}</span>
      {item.next_action_date && (
        <small>Další krok: {new Date(item.next_action_date).toLocaleDateString('cs-CZ')}</small>
      )}
    </button>
  );
  return (
    <div className="leads-app lead-crm">
      <div className={`lead-workspace ${selected ? 'with-detail' : ''}`}>
        <aside className="lead-sidebar" aria-label="Filtry a instituce">
          <header className="lead-sidebar-header">
            <h1>Leady a instituce</h1>
            <div className="lead-view-switch" role="group" aria-label="Zobrazení institucí">
              <button type="button" aria-pressed={view === 'map'} onClick={() => setView('map')}>
                <Map size={18} aria-hidden="true" /> Mapa
              </button>
              <button
                type="button"
                aria-pressed={view === 'pipeline'}
                onClick={() => setView('pipeline')}
              >
                <Columns3 size={18} aria-hidden="true" /> Pipeline
              </button>
            </div>
            <div className="lead-sidebar-actions">
              <Button onClick={() => setSelected('new')}>
                <Plus size={16} aria-hidden="true" /> Nová instituce
              </Button>
              {actor.superadmin && (
                <Button
                  variant="outline"
                  onClick={download}
                  disabled={exporting}
                  aria-label={exporting ? 'Exportuji CSV' : 'Export CSV'}
                  title="Export CSV"
                >
                  <Download size={16} aria-hidden="true" /> {exporting ? 'Exportuji…' : 'CSV'}
                </Button>
              )}
            </div>
          </header>
          <div className="lead-sidebar-body">
            {actor.superadmin && (
              <Button
                className="lead-import-trigger"
                variant="outline"
                onClick={() => setImportOpen(true)}
              >
                <Upload size={16} aria-hidden="true" /> Import Excel / CSV
              </Button>
            )}
            {error && (
              <div role="alert" className="lead-error">
                {error}{' '}
                <Button variant="outline" onClick={() => saved()}>
                  Zkusit znovu
                </Button>
              </div>
            )}
            <label>
              Hledat instituci, město nebo kontakt
              <Input
                type="search"
                value={filters.q}
                maxLength={200}
                onChange={(e) => setFilter('q', e.target.value)}
                placeholder="Název, město, kontakt…"
              />
            </label>
            {metadata && (
              <>
                <div className="lead-filter-heading">
                  <h2>Filtry</h2>
                  <button
                    type="button"
                    onClick={() => setFilters(emptyFilters)}
                    aria-label="Vymazat filtry"
                  >
                    <RotateCcw size={15} aria-hidden="true" /> Vymazat
                  </button>
                </div>
                <div className="lead-filter-grid">
                  {[
                    ['type', 'Typ', metadata.type],
                    ['region', 'Kraj', metadata.region],
                    ['cluster', 'Klastr', metadata.cluster],
                    ['plan', 'Tarif', ['FREE', 'PRO', 'PRO+', 'ověřit']],
                    ['stage', 'Stav', metadata.stages],
                  ].map(([key, label, options]) => (
                    <label key={key}>
                      {label}
                      <select value={filters[key]} onChange={(e) => setFilter(key, e.target.value)}>
                        <option value="">Vše</option>
                        {options.map((o) => (
                          <option key={o}>{o}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                  <label>
                    Pracovník
                    <select
                      value={filters.assignee}
                      onChange={(e) => setFilter('assignee', e.target.value)}
                    >
                      <option value="">Všichni</option>
                      <option value="unassigned">Nepřiděleno</option>
                      {metadata.accounts.map((a) => (
                        <option value={a.id} key={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Další krok
                    <select value={filters.due} onChange={(e) => setFilter('due', e.target.value)}>
                      <option value="">Kdykoliv</option>
                      <option value="overdue">Po termínu</option>
                      <option value="today">Dnes</option>
                      <option value="planned">Má termín</option>
                    </select>
                  </label>
                </div>
                {[
                  ['connected', 'Pouze připojené'],
                  ['mine', 'Moje leady'],
                  ['archived', 'Archivované'],
                ].map(([key, label]) => (
                  <label className="lead-check" key={key}>
                    <input
                      type="checkbox"
                      checked={filters[key]}
                      onChange={(e) => setFilter(key, e.target.checked)}
                    />
                    {label}
                  </label>
                ))}
              </>
            )}
            <h2 aria-live="polite">
              {loading ? 'Načítám instituce…' : `Instituce (${items.length})`}
            </h2>
            {!loading && !items.length && <p>Filtrům neodpovídá žádná instituce.</p>}
            <div className="lead-list" aria-busy={loading}>
              {!loading && items.map(card)}
            </div>
            <details className="lead-goals-disclosure">
              <summary>Cíle a aktivace</summary>
              <LeadGoals goals={goals} actor={actor} onSaved={() => saved()} />
            </details>
          </div>
        </aside>
        <section
          className="lead-canvas"
          aria-label={view === 'map' ? 'Mapa institucí' : 'Pipeline institucí'}
        >
          {loading ? (
            <p role="status">Načítám přehled…</p>
          ) : view === 'map' ? (
            <>
              <LeadMap items={items} onSelect={setSelected} />
              <div className="lead-legend">
                {[
                  ['new', 'Nový'],
                  ['contacted', 'V kontaktu'],
                  ['declined', 'Odmítli'],
                  ['postponed', 'Odloženo'],
                  ['connected', 'Připojeno'],
                  ['paying', 'Platící'],
                ].map(([key, label]) => (
                  <span className={`lead-stage ${key}`} key={key}>
                    {label}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div
              className="lead-pipeline"
              tabIndex={0}
              aria-label="Sloupce pipeline – posuňte vodorovně"
            >
              {groups.map((group) => (
                <section key={group}>
                  <h2>
                    {group} ({items.filter((x) => pipelineGroup(x.stage) === group).length})
                  </h2>
                  {items.filter((x) => pipelineGroup(x.stage) === group).map(card)}
                </section>
              ))}
            </div>
          )}
        </section>
        {selected && metadata && (
          <LeadDetail
            key={selected}
            id={selected}
            actor={actor}
            metadata={metadata}
            onClose={() => setSelected(null)}
            onSaved={saved}
          />
        )}
      </div>
      {actor.superadmin && importOpen && (
        <LeadImport onClose={() => setImportOpen(false)} onImported={() => saved()} />
      )}
    </div>
  );
}

export default function LeadsPage() {
  const [actor, setActor] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(''),
    [username, setUsername] = useState(''),
    [password, setPassword] = useState(''),
    [busy, setBusy] = useState(false);
  const auth = useContext(AuthContext),
    location = useLocation(),
    navigate = useNavigate();
  const check = useCallback(async () => {
    try {
      setActor(await leadsApi('/me'));
      setError('');
    } catch (e) {
      setActor(null);
      if (e.status !== 401) setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    check();
  }, [check]);
  const login = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await leadLogin(username, password);
      setPassword('');
      await check();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const logout = async () => {
    try {
      await leadsApi('/auth/logout', { method: 'POST' });
    } catch {
      /* local logout still clears credentials */
    }
    clearLeadSession();
    if (actor.superadmin) await auth.logout();
    setActor(null);
    navigate('/admin/leady', { replace: true });
  };
  if (loading)
    return (
      <div className="lead-login" role="status">
        Ověřuji interní přístup…
      </div>
    );
  if (!actor)
    return (
      <main className="leads-app lead-login">
        <section className="lead-panel">
          <BudezivoLogo />
          <h1>Interní Lead Map</h1>
          <p>Přihlášení pro pověřené spolupracovníky Budeživo.</p>
          {error && (
            <p role="alert" className="lead-error">
              {error}
            </p>
          )}
          <form onSubmit={login}>
            <fieldset disabled={busy}>
              <label>
                Uživatelské jméno
                <Input
                  autoComplete="username"
                  required
                  maxLength={80}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>
              <label>
                Heslo
                <Input
                  type="password"
                  autoComplete="current-password"
                  required
                  maxLength={200}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <Button type="submit">{busy ? 'Přihlašuji…' : 'Přihlásit se'}</Button>
            </fieldset>
          </form>
          <p>Účet a nové heslo vám nastaví superadmin.</p>
          <Link className="lead-link" to="/login">
            Přihlášení superadmina
          </Link>
        </section>
      </main>
    );
  const team = location.pathname === '/admin/leady/tym';
  return (
    <AdminLayout crmUser={actor} onCrmLogout={logout}>
      {team ? (
        actor.superadmin ? (
          <LeadTeam />
        ) : (
          <p role="alert">Správa týmu je dostupná pouze superadminovi.</p>
        )
      ) : (
        <Workspace actor={actor} />
      )}
    </AdminLayout>
  );
}
