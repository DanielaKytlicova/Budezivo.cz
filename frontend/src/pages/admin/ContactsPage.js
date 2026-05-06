import React, { useState, useMemo } from 'react';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import {
  Search, Plus, Mail, Phone, User, Calendar, ShieldCheck, ShieldX,
  X, Edit2, Save, Tag, Sparkles, Filter, Download, ChevronRight,
} from 'lucide-react';

/**
 * Wireframe / mockup of the Contacts management page.
 *
 * Backend integration is intentionally deferred to milestone M1 — this page
 * currently runs on a hard-coded MOCK dataset so the user can validate the
 * layout, filter UX, and detail panel before we cut DB migrations.
 *
 * IMPORTANT: every visible string is in Czech (user's preferred language).
 * The data shape mirrors the planned `contacts` and `contact_links` tables
 * so the move from mock → real is a 1:1 swap of `MOCK_CONTACTS` for an API
 * fetch.
 */

const CONTACT_TYPES = [
  { value: 'skola', label: 'Škola' },
  { value: 'pedagog', label: 'Pedagog' },
  { value: 'rodic', label: 'Rodič' },
  { value: 'verejnost', label: 'Veřejnost' },
  { value: 'odborna_verejnost', label: 'Odborná veřejnost' },
  { value: 'jine', label: 'Jiný' },
];

const CONTACT_SOURCES = [
  { value: 'skolni_rezervace', label: 'Školní rezervace' },
  { value: 'jednorazova_akce', label: 'Jednorázová akce' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'kurz', label: 'Kurz' },
  { value: 'primestsky_tabor', label: 'Příměstský tábor' },
  { value: 'baby_herna', label: 'Baby herna' },
  { value: 'rucne', label: 'Ručně přidáno' },
];

const MOCK_CONTACTS = [
  {
    id: 'c-001',
    first_name: 'Mgr. Tereza', last_name: 'Kolářová',
    email: 'kolarova@gymvidenska.cz', phone: '+420 602 111 222',
    type: 'pedagog', source: 'skolni_rezervace',
    marketing_consent: true,
    school_name: 'Gymnázium Vídeňská', school_type: 'SS',
    note: 'Učí dějiny umění, zajímá ji moderna 20. století.',
    created_at: '2026-01-15', last_activity: '2026-04-16',
    links: [
      { type: 'skolni_rezervace', label: 'Komentovaná prohlídka výstavy', date: '2026-04-16', status: 'dokoncen' },
      { type: 'skolni_rezervace', label: 'Experimentální ateliér', date: '2026-04-16', status: 'dokoncen' },
      { type: 'workshop', label: 'Workshop tisku — pedagogové', date: '2026-02-20', status: 'ucastnil_se' },
    ],
  },
  {
    id: 'c-002',
    first_name: 'Mgr. Daniel', last_name: 'Hruška',
    email: 'hruska@horackenamesti.cz', phone: '+420 723 555 888',
    type: 'pedagog', source: 'skolni_rezervace',
    marketing_consent: false,
    school_name: 'ZŠ Horácké náměstí', school_type: 'ZS',
    note: '',
    created_at: '2026-02-08', last_activity: '2026-04-02',
    links: [
      { type: 'skolni_rezervace', label: 'Moderna v galerii — II. stupeň ZŠ', date: '2026-04-02', status: 'dokoncen' },
    ],
  },
  {
    id: 'c-003',
    first_name: 'Jana', last_name: 'Procházková',
    email: 'prochazkova@email.cz', phone: '+420 608 444 333',
    type: 'rodic', source: 'primestsky_tabor',
    marketing_consent: true,
    school_name: null, school_type: null,
    note: '2 děti — Jakub (7 let), Eliška (5 let). Účastnila se táborů 2024 i 2025.',
    created_at: '2025-06-12', last_activity: '2026-03-22',
    links: [
      { type: 'primestsky_tabor', label: 'Letní tábor 2025 — týden 2', date: '2025-07-21', status: 'zaplaceno' },
      { type: 'primestsky_tabor', label: 'Velikonoční tábor 2026', date: '2026-03-22', status: 'zaplaceno' },
    ],
  },
  {
    id: 'c-004',
    first_name: 'PaedDr. Karel', last_name: 'Malý',
    email: 'maly@gymvidenska.cz', phone: '+420 605 999 111',
    type: 'pedagog', source: 'skolni_rezervace',
    marketing_consent: null, // unknown — predates the opt-in checkbox
    school_name: 'Gymnázium Vídeňská', school_type: 'SS',
    note: '',
    created_at: '2025-09-04', last_activity: '2026-04-17',
    links: [
      { type: 'skolni_rezervace', label: 'Moderna v galerii — SŠ', date: '2026-04-17', status: 'dokoncen' },
    ],
  },
  {
    id: 'c-005',
    first_name: 'Petra', last_name: 'Nováková',
    email: 'p.novakova@gmail.com', phone: '+420 776 222 444',
    type: 'rodic', source: 'baby_herna',
    marketing_consent: true,
    school_name: null, school_type: null,
    note: '',
    created_at: '2026-02-01', last_activity: '2026-04-25',
    links: [
      { type: 'baby_herna', label: 'Baby herna — středa dopoledne', date: '2026-04-25', status: 'ucastnil_se' },
      { type: 'baby_herna', label: 'Baby herna — středa dopoledne', date: '2026-04-18', status: 'ucastnil_se' },
      { type: 'baby_herna', label: 'Baby herna — středa dopoledne', date: '2026-04-11', status: 'ucastnil_se' },
    ],
  },
  {
    id: 'c-006',
    first_name: 'Mgr. Anna', last_name: 'Dvořáková',
    email: 'dvorakova@gymslovan.cz', phone: '+420 731 808 909',
    type: 'pedagog', source: 'skolni_rezervace',
    marketing_consent: true,
    school_name: 'Gymnázium Slovanské náměstí', school_type: 'SS',
    note: 'Sociálně-kulturní antropologie, programy o identitě.',
    created_at: '2025-11-03', last_activity: '2026-04-16',
    links: [
      { type: 'skolni_rezervace', label: 'Experimentální ateliér', date: '2026-04-02', status: 'dokoncen' },
      { type: 'skolni_rezervace', label: 'Experimentální ateliér', date: '2026-04-03', status: 'dokoncen' },
      { type: 'skolni_rezervace', label: 'Experimentální ateliér', date: '2026-04-16', status: 'dokoncen' },
    ],
  },
  {
    id: 'c-007',
    first_name: 'Tomáš', last_name: 'Veselý',
    email: 'tomas.vesely@cesnet.cz', phone: '',
    type: 'odborna_verejnost', source: 'workshop',
    marketing_consent: true,
    school_name: null, school_type: null,
    note: 'Kurátor — zajímá ho výzkumná spolupráce.',
    created_at: '2026-01-30', last_activity: '2026-02-20',
    links: [
      { type: 'workshop', label: 'Workshop tisku — pedagogové', date: '2026-02-20', status: 'ucastnil_se' },
    ],
  },
  {
    id: 'c-008',
    first_name: 'Bc. Klára', last_name: 'Nováková',
    email: 'novakova@zsuvoz.cz', phone: '+420 602 333 555',
    type: 'pedagog', source: 'skolni_rezervace',
    marketing_consent: false,
    school_name: 'ZŠ Úvoz', school_type: 'ZS',
    note: '',
    created_at: '2026-01-22', last_activity: '2026-04-03',
    links: [
      { type: 'skolni_rezervace', label: 'Barvy kolem nás — I. stupeň ZŠ', date: '2026-04-03', status: 'dokoncen' },
      { type: 'skolni_rezervace', label: 'Barvy kolem nás — MŠ', date: '2026-04-03', status: 'dokoncen' },
    ],
  },
  {
    id: 'c-009',
    first_name: 'Markéta', last_name: 'Horáková',
    email: 'm.horakova@email.cz', phone: '+420 728 111 222',
    type: 'verejnost', source: 'jednorazova_akce',
    marketing_consent: true,
    school_name: null, school_type: null,
    note: '',
    created_at: '2026-03-10', last_activity: '2026-03-15',
    links: [
      { type: 'jednorazova_akce', label: 'Vernisáž výstavy „Krajiny snů"', date: '2026-03-15', status: 'ucastnil_se' },
    ],
  },
];

function typeLabel(value) {
  return CONTACT_TYPES.find(t => t.value === value)?.label || value;
}
function sourceLabel(value) {
  return CONTACT_SOURCES.find(s => s.value === value)?.label || value;
}

function ConsentBadge({ consent }) {
  if (consent === true) {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 gap-1">
        <ShieldCheck className="w-3 h-3" /> Souhlas
      </Badge>
    );
  }
  if (consent === false) {
    return (
      <Badge variant="outline" className="gap-1 text-rose-600 border-rose-200">
        <ShieldX className="w-3 h-3" /> Bez souhlasu
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1 text-slate-500">
      <ShieldX className="w-3 h-3" /> Neznámé
    </Badge>
  );
}

const ContactsPage = () => {
  const [contacts] = useState(MOCK_CONTACTS);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [consentFilter, setConsentFilter] = useState('all');
  const [selectedId, setSelectedId] = useState(null);

  const filtered = useMemo(() => {
    return contacts.filter(c => {
      if (typeFilter !== 'all' && c.type !== typeFilter) return false;
      if (sourceFilter !== 'all' && c.source !== sourceFilter) return false;
      if (consentFilter === 'yes' && c.marketing_consent !== true) return false;
      if (consentFilter === 'no' && c.marketing_consent !== false) return false;
      if (consentFilter === 'unknown' && c.marketing_consent !== null) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const fullName = `${c.first_name} ${c.last_name}`.toLowerCase();
        if (
          !fullName.includes(q) &&
          !(c.email || '').toLowerCase().includes(q) &&
          !(c.phone || '').toLowerCase().includes(q) &&
          !(c.school_name || '').toLowerCase().includes(q)
        ) return false;
      }
      return true;
    });
  }, [contacts, typeFilter, sourceFilter, consentFilter, searchQuery]);

  const stats = useMemo(() => ({
    total: contacts.length,
    withConsent: contacts.filter(c => c.marketing_consent === true).length,
    schools: contacts.filter(c => c.type === 'pedagog' || c.type === 'skola').length,
    public: contacts.filter(c => c.type === 'rodic' || c.type === 'verejnost').length,
  }), [contacts]);

  const selected = contacts.find(c => c.id === selectedId) || null;

  return (
    <AdminLayout>
      <div className="space-y-4 md:space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">Kontakty</h1>
            <p className="text-sm text-slate-500 mt-1">
              Centrální přehled kontaktů z rezervací a přihlášek na akce.
              Slouží jako základ pro cílený mailing.
            </p>
            <div className="inline-flex items-center gap-2 mt-3 px-3 py-1 rounded-full bg-amber-50 border border-amber-200">
              <Sparkles className="w-3.5 h-3.5 text-amber-600" />
              <span className="text-xs text-amber-800 font-medium">
                Wireframe — zatím s ukázkovými daty. Po vašem schválení napojíme na DB.
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" data-testid="contacts-export-btn">
              <Download className="w-4 h-4 mr-2" /> Export CSV
            </Button>
            <Button className="bg-slate-800 text-white hover:bg-slate-700" data-testid="contacts-add-btn">
              <Plus className="w-4 h-4 mr-2" /> Přidat kontakt
            </Button>
          </div>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Celkem kontaktů</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1" data-testid="stat-total">{stats.total}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">S marketing. souhlasem</p>
            <p className="text-2xl font-semibold text-emerald-700 mt-1" data-testid="stat-consent">{stats.withConsent}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Pedagogové / Školy</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1" data-testid="stat-schools">{stats.schools}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Veřejnost / Rodiče</p>
            <p className="text-2xl font-semibold text-slate-900 mt-1" data-testid="stat-public">{stats.public}</p>
          </Card>
        </div>

        {/* Filters */}
        <Card className="p-3 md:p-4">
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Hledat podle jména, e-mailu, telefonu, školy..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9"
                data-testid="contacts-search"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[170px]" data-testid="filter-type">
                  <Filter className="w-3.5 h-3.5 mr-1.5" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny typy</SelectItem>
                  {CONTACT_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={sourceFilter} onValueChange={setSourceFilter}>
                <SelectTrigger className="w-[180px]" data-testid="filter-source">
                  <Tag className="w-3.5 h-3.5 mr-1.5" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny zdroje</SelectItem>
                  {CONTACT_SOURCES.map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={consentFilter} onValueChange={setConsentFilter}>
                <SelectTrigger className="w-[180px]" data-testid="filter-consent">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Všechny souhlasy</SelectItem>
                  <SelectItem value="yes">Pouze se souhlasem</SelectItem>
                  <SelectItem value="no">Bez souhlasu</SelectItem>
                  <SelectItem value="unknown">Neznámý</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-2.5" data-testid="contacts-result-count">
            Zobrazeno {filtered.length} z {contacts.length}
          </p>
        </Card>

        {/* Table */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="contacts-table">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Jméno</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">E-mail / telefon</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Typ</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Zdroj</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Marketing souhlas</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Poslední aktivita</th>
                  <th className="px-4 py-3 text-right font-semibold text-slate-600">Akce</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-400" data-testid="contacts-empty">
                      Žádné kontakty neodpovídají vašim filtrům.
                    </td>
                  </tr>
                )}
                {filtered.map(c => (
                  <tr
                    key={c.id}
                    onClick={() => setSelectedId(c.id)}
                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                    data-testid={`contact-row-${c.id}`}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">
                        {c.first_name} {c.last_name}
                      </div>
                      {c.school_name && (
                        <div className="text-xs text-slate-500 mt-0.5">{c.school_name}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-slate-700">{c.email}</div>
                      {c.phone && <div className="text-xs text-slate-500 mt-0.5">{c.phone}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline" className="font-normal">{typeLabel(c.type)}</Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-xs">
                      {sourceLabel(c.source)}
                    </td>
                    <td className="px-4 py-3">
                      <ConsentBadge consent={c.marketing_consent} />
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-xs">
                      {c.last_activity}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ChevronRight className="w-4 h-4 text-slate-400 inline" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Detail panel — slide-in from right */}
      {selected && <ContactDetailPanel contact={selected} onClose={() => setSelectedId(null)} />}
    </AdminLayout>
  );
};

function ContactDetailPanel({ contact, onClose }) {
  const [editingNote, setEditingNote] = useState(false);
  const [note, setNote] = useState(contact.note || '');
  const [type, setType] = useState(contact.type);

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
        data-testid="contact-detail-backdrop"
      />
      <div
        className="fixed top-0 right-0 bottom-0 w-full sm:max-w-md bg-white shadow-2xl z-50 overflow-y-auto"
        data-testid="contact-detail-panel"
      >
        <div className="sticky top-0 bg-white border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Detail kontaktu</h2>
            <p className="text-xs text-slate-500 mt-0.5">ID: {contact.id}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-slate-100 transition-colors"
            data-testid="contact-detail-close"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="p-5 space-y-6">
          {/* Identita */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Identita</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-slate-400" />
                <span className="font-medium text-slate-900">{contact.first_name} {contact.last_name}</span>
              </div>
              {contact.school_name && (
                <div className="text-slate-600 pl-6">{contact.school_name}</div>
              )}
            </div>
          </section>

          {/* Kontakt */}
          <section>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Kontaktní údaje</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-slate-400" />
                <a href={`mailto:${contact.email}`} className="text-blue-600 hover:underline">{contact.email}</a>
              </div>
              {contact.phone && (
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4 text-slate-400" />
                  <a href={`tel:${contact.phone}`} className="text-slate-700">{contact.phone}</a>
                </div>
              )}
            </div>
          </section>

          {/* Typ + souhlas */}
          <section className="grid grid-cols-2 gap-3">
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Typ</h3>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger data-testid="detail-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONTACT_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Marketing</h3>
              <div className="pt-1.5">
                <ConsentBadge consent={contact.marketing_consent} />
              </div>
            </div>
          </section>

          {/* Poznámka */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Poznámka</h3>
              {!editingNote ? (
                <button
                  onClick={() => setEditingNote(true)}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                  data-testid="detail-note-edit"
                >
                  <Edit2 className="w-3 h-3" /> Upravit
                </button>
              ) : (
                <button
                  onClick={() => setEditingNote(false)}
                  className="text-xs text-emerald-600 hover:underline flex items-center gap-1"
                  data-testid="detail-note-save"
                >
                  <Save className="w-3 h-3" /> Uložit
                </button>
              )}
            </div>
            {editingNote ? (
              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                className="w-full p-2 border border-slate-200 rounded text-sm min-h-[80px]"
                data-testid="detail-note-textarea"
              />
            ) : (
              <p className="text-sm text-slate-700 italic">
                {note || <span className="text-slate-400 not-italic">Bez poznámky</span>}
              </p>
            )}
          </section>

          {/* Historie */}
          <section>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Historie vazeb ({contact.links.length})
            </h3>
            <ol className="space-y-3" data-testid="detail-links-list">
              {contact.links.map((l, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm border-l-2 border-slate-200 pl-3">
                  <Calendar className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{l.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {l.date} · {sourceLabel(l.type)} · <span className="font-medium">{l.status}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {/* Meta */}
          <section className="pt-3 border-t border-slate-100 text-xs text-slate-400 space-y-0.5">
            <p>Vytvořeno: {contact.created_at}</p>
            <p>Poslední aktivita: {contact.last_activity}</p>
          </section>
        </div>
      </div>
    </>
  );
}

export default ContactsPage;
