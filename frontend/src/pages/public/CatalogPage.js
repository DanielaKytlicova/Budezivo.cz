import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams, useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Header } from '../../components/layout/Header';
import { Footer } from '../../components/layout/Footer';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Search, MapPin, Clock, Users, Sparkles, Filter, X, Flame, Plus } from 'lucide-react';
import { slugify, AGE_SLUGS, AGE_SLUG_LABELS } from '../../lib/slugify';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const SORTS = [
  { value: 'popular', label: 'Nejoblíbenější' },
  { value: 'newest',  label: 'Nejnovější' },
];

export default function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const { slug: pathSlug } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0, facets: { cities: [], categories: [], age_groups: [] } });
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(params.get('q') || '');

  // Discover sections (popular + newest) — only fetched/shown when no filter is active
  const [popular, setPopular] = useState([]);
  const [newest, setNewest] = useState([]);
  const [discoverLoading, setDiscoverLoading] = useState(false);

  // Resolve SEO slug from URL path → resolved filter once facets are loaded.
  const resolvedSlug = useMemo(() => {
    if (!pathSlug) return null;
    const s = pathSlug.toLowerCase();
    if (AGE_SLUGS.includes(s)) {
      return { type: 'age', value: s, label: AGE_SLUG_LABELS[s] };
    }
    const cityMatch = (data.facets.cities || []).find(c => slugify(c) === s);
    if (cityMatch) return { type: 'city', value: cityMatch, label: cityMatch };
    const catMatch = (data.facets.categories || []).find(c => slugify(c) === s);
    if (catMatch) return { type: 'category', value: catMatch, label: catMatch };
    return { type: 'unknown', value: s, label: s };
  }, [pathSlug, data.facets.cities, data.facets.categories]);

  const filters = useMemo(() => {
    const base = {
      city:     params.get('city')     || '',
      age:      params.get('age')      || '',
      category: params.get('category') || '',
      q:        params.get('q')        || '',
      sort:     params.get('sort')     || 'popular',
    };
    // Slug overrides corresponding filter only when query param is empty
    if (resolvedSlug && resolvedSlug.type !== 'unknown') {
      if (resolvedSlug.type === 'age'      && !base.age)      base.age      = resolvedSlug.value;
      if (resolvedSlug.type === 'city'     && !base.city)     base.city     = resolvedSlug.value;
      if (resolvedSlug.type === 'category' && !base.category) base.category = resolvedSlug.value;
    }
    return base;
  }, [params, resolvedSlug]);

  // True when user did not narrow further than (optional) slug — show inspirational sections
  const hasUserFilter = !!(params.get('city') || params.get('age') || params.get('category') || params.get('q'));
  const showDiscover = !pathSlug && !hasUserFilter;

  useEffect(() => { setQ(filters.q); }, [filters.q]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) search.set(k, v); });
    axios.get(`${API}/public/catalog?${search.toString()}`)
      .then(r => { if (!cancelled) setData(r.data); })
      .catch(() => { if (!cancelled) setData({ items: [], total: 0, facets: { cities: [], categories: [], age_groups: [] } }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters]);

  // Fetch discover sections (only when none of the user filters are active and no slug)
  useEffect(() => {
    if (!showDiscover) { setPopular([]); setNewest([]); return; }
    let cancelled = false;
    setDiscoverLoading(true);
    Promise.all([
      axios.get(`${API}/public/catalog?sort=popular&limit=4`).then(r => r.data.items || []),
      axios.get(`${API}/public/catalog?sort=newest&limit=4`).then(r => r.data.items || []),
    ]).then(([pop, nw]) => {
      if (cancelled) return;
      setPopular(pop);
      setNewest(nw);
    }).catch(() => {
      if (!cancelled) { setPopular([]); setNewest([]); }
    }).finally(() => { if (!cancelled) setDiscoverLoading(false); });
    return () => { cancelled = true; };
  }, [showDiscover]);

  const updateFilter = (key, value) => {
    // Any user-driven filter change leaves slug routes — push to /programy-pro-skoly with query
    const next = new URLSearchParams(pathSlug ? new URLSearchParams() : params);
    // Preserve existing slug-applied filters as query when leaving slug page
    if (pathSlug && resolvedSlug && resolvedSlug.type !== 'unknown') {
      const k = resolvedSlug.type;
      if (filters[k] && filters[k] !== value) next.set(k, filters[k]);
    }
    if (value) next.set(key, value); else next.delete(key);
    if (pathSlug) {
      navigate(`/programy-pro-skoly?${next.toString()}`);
    } else {
      setParams(next, { replace: false });
    }
  };

  const clearFilters = () => {
    if (pathSlug) navigate('/programy-pro-skoly');
    else setParams(new URLSearchParams(), { replace: false });
  };
  const submitSearch = (e) => { e.preventDefault(); updateFilter('q', q.trim()); };

  const activeChips = Object.entries(filters).filter(([k, v]) => v && k !== 'sort');

  // Slug-aware H1
  const slugTitle = resolvedSlug && resolvedSlug.type !== 'unknown'
    ? (resolvedSlug.type === 'city'
        ? `Programy v lokalitě ${resolvedSlug.label}`
        : resolvedSlug.type === 'age'
          ? `Programy pro ${resolvedSlug.label}`
          : `Programy v zaměření „${resolvedSlug.label}"`)
    : null;

  return (
    <div className="min-h-screen bg-[#F8F9FA]" data-testid="catalog-page">
      <Header />

      {/* HERO */}
      <section className="bg-gradient-to-br from-[#4A6FA5] via-[#5979ad] to-[#6889bb] text-white py-16 md:py-20">
        <div className="max-w-6xl mx-auto px-6 md:px-8">
          <p className="text-xs font-semibold tracking-[0.2em] uppercase text-[#C4AB86] mb-3" data-testid="catalog-eyebrow">
            Katalog programů pro školy
          </p>
          <h1 className="text-3xl md:text-5xl font-bold leading-tight mb-4" data-testid="catalog-title">
            {slugTitle || 'Najděte program pro svou třídu'}
          </h1>
          <p className="text-base md:text-lg text-white/85 max-w-2xl mb-8">
            Inspirace z muzeí, galerií, knihoven a kulturních center. Vyberte si, rezervujte termín — bez registrace.
          </p>

          {/* Search bar */}
          <form onSubmit={submitSearch} className="flex flex-col sm:flex-row gap-3 max-w-3xl" data-testid="catalog-search-form">
            <div className="flex-1 relative">
              <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Hledat program podle názvu nebo tématu..."
                className="h-12 pl-12 bg-white text-slate-900 border-0 rounded-lg"
                data-testid="catalog-search-input"
              />
            </div>
            <Button
              type="submit"
              size="lg"
              className="h-12 px-8 bg-[#C4AB86] text-white hover:bg-[#b39975] rounded-lg"
              data-testid="catalog-search-submit"
            >
              Hledat
            </Button>
          </form>
        </div>
      </section>

      {/* DISCOVER — Popular & Newest (only when no filter / no slug) */}
      {showDiscover && (popular.length > 0 || newest.length > 0 || discoverLoading) && (
        <section className="pt-10 pb-2" data-testid="catalog-discover">
          <div className="max-w-6xl mx-auto px-6 md:px-8 space-y-12">
            <DiscoverRow
              testid="discover-popular"
              icon={<Flame className="w-5 h-5 text-[#E87A2B]" />}
              eyebrow="Nejoblíbenější"
              title="Co školy nejvíc vybírají"
              items={popular}
              loading={discoverLoading}
              emptyText="Zatím není dost dat o oblíbenosti."
            />
            <DiscoverRow
              testid="discover-newest"
              icon={<Plus className="w-5 h-5 text-[#4A6FA5]" />}
              eyebrow="Novinky"
              title="Nově přidané programy"
              items={newest}
              loading={discoverLoading}
              emptyText="Žádné nové programy."
            />
          </div>
        </section>
      )}

      {/* FILTERS + LIST */}
      <section className="py-10">
        <div className="max-w-6xl mx-auto px-6 md:px-8">
          {/* Filter row */}
          <div className="grid grid-cols-1 md:grid-cols-[200px_200px_220px_1fr] gap-3 mb-6" data-testid="catalog-filters">
            {/* City */}
            <select
              value={filters.city}
              onChange={(e) => updateFilter('city', e.target.value)}
              className="h-11 px-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#4A6FA5]/30"
              data-testid="filter-city"
            >
              <option value="">Všechna města</option>
              {data.facets.cities.map(c => <option key={c} value={c}>{c}</option>)}
            </select>

            {/* Age group */}
            <select
              value={filters.age}
              onChange={(e) => updateFilter('age', e.target.value)}
              className="h-11 px-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#4A6FA5]/30"
              data-testid="filter-age"
            >
              <option value="">Všechny věky</option>
              {data.facets.age_groups.map(a => <option key={a.slug} value={a.slug}>{a.label}</option>)}
            </select>

            {/* Category */}
            <select
              value={filters.category}
              onChange={(e) => updateFilter('category', e.target.value)}
              className="h-11 px-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#4A6FA5]/30"
              data-testid="filter-category"
            >
              <option value="">Všechna zaměření</option>
              {data.facets.categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>

            {/* Sort */}
            <select
              value={filters.sort}
              onChange={(e) => updateFilter('sort', e.target.value)}
              className="h-11 px-3 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#4A6FA5]/30 md:ml-auto md:w-56"
              data-testid="filter-sort"
            >
              {SORTS.map(s => <option key={s.value} value={s.value}>Řadit: {s.label}</option>)}
            </select>
          </div>

          {/* Active chips */}
          {activeChips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mb-6" data-testid="active-filters">
              <span className="text-sm text-slate-500 inline-flex items-center gap-1.5">
                <Filter className="w-4 h-4" /> Aktivní filtry:
              </span>
              {activeChips.map(([k, v]) => (
                <button
                  key={k}
                  onClick={() => updateFilter(k, '')}
                  className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#EEF2F9] text-[#4A6FA5] text-sm rounded-full hover:bg-[#dde5f3] transition"
                  data-testid={`active-filter-${k}`}
                >
                  {v} <X className="w-3.5 h-3.5" />
                </button>
              ))}
              <button onClick={clearFilters} className="text-sm text-slate-500 underline hover:text-slate-700 ml-2" data-testid="clear-filters">
                Vymazat vše
              </button>
            </div>
          )}

          {/* Section heading when discover sections are visible above */}
          {showDiscover && (
            <div className="mb-6" data-testid="catalog-all-heading">
              <p className="text-xs font-semibold tracking-[0.2em] uppercase text-[#C4AB86] mb-2">Všechny programy</p>
              <h2 className="text-2xl md:text-3xl font-bold text-slate-900">Procházet katalog</h2>
            </div>
          )}

          {/* Results count */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-500" data-testid="catalog-count">
              {loading ? 'Načítání...' : `${data.total} ${data.total === 1 ? 'program' : (data.total >= 2 && data.total <= 4 ? 'programy' : 'programů')}`}
            </p>
          </div>

          {/* Grid */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <Card key={i} className="p-0 overflow-hidden bg-white">
                  <div className="h-40 bg-slate-100 animate-pulse" />
                  <div className="p-5 space-y-2">
                    <div className="h-4 bg-slate-100 rounded w-3/4 animate-pulse" />
                    <div className="h-3 bg-slate-100 rounded w-1/2 animate-pulse" />
                  </div>
                </Card>
              ))}
            </div>
          ) : data.items.length === 0 ? (
            <Card className="p-10 text-center bg-white border border-dashed" data-testid="catalog-empty">
              <Sparkles className="w-10 h-10 text-[#C4AB86] mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-slate-800 mb-1">Žádné programy nenalezeny</h3>
              <p className="text-sm text-slate-500 mb-4">Zkuste zmírnit filtry nebo hledat jinak.</p>
              <Button onClick={clearFilters} variant="outline" data-testid="catalog-empty-clear">Vymazat filtry</Button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="catalog-grid">
              {data.items.map((p) => <ProgramCard key={p.id} p={p} />)}
            </div>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
}

const ProgramCard = ({ p }) => (
  <Link
    to={`/programy-pro-skoly/p/${p.id}`}
    className="group block"
    data-testid={`catalog-card-${p.id}`}
  >
    <Card className="overflow-hidden bg-white border border-slate-100 hover:border-[#4A6FA5]/30 hover:shadow-lg transition-all duration-300 h-full">
      {/* Image */}
      <div className="relative h-44 bg-gradient-to-br from-[#EEF2F9] to-[#F8F9FA] overflow-hidden">
        {p.image_url ? (
          <img src={p.image_url} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Sparkles className="w-12 h-12 text-[#4A6FA5]/30" />
          </div>
        )}
        {p.age_labels?.length > 0 && (
          <div className="absolute top-3 left-3 flex flex-wrap gap-1.5">
            {p.age_labels.slice(0, 2).map(a => (
              <Badge key={a} className="bg-white/95 text-[#4A6FA5] hover:bg-white border-0 backdrop-blur-sm">
                {a}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-5 flex flex-col gap-2">
        <h3 className="text-lg font-semibold text-slate-900 line-clamp-2 group-hover:text-[#4A6FA5] transition-colors">
          {p.name}
        </h3>
        <p className="text-sm text-slate-500 line-clamp-1">
          {p.institution.name}
        </p>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500 mt-1">
          {p.institution.city && (
            <span className="inline-flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{p.institution.city}</span>
          )}
          <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{p.duration} min</span>
          {p.max_capacity && (
            <span className="inline-flex items-center gap-1"><Users className="w-3.5 h-3.5" />do {p.max_capacity}</span>
          )}
        </div>

        {p.categories?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {p.categories.slice(0, 3).map(c => (
              <span key={c} className="px-2 py-0.5 text-[11px] rounded-full bg-[#F1F4FA] text-[#4A6FA5] border border-[#E1E8F2]">
                {c}
              </span>
            ))}
          </div>
        )}

        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            {p.reservation_count > 0 && `${p.reservation_count} rezervací`}
          </span>
          <span className="text-sm font-medium text-[#4A6FA5] group-hover:underline">
            Zobrazit detail →
          </span>
        </div>
      </div>
    </Card>
  </Link>
);


const DiscoverRow = ({ testid, icon, eyebrow, title, items, loading, emptyText }) => (
  <div data-testid={testid}>
    <div className="flex items-end justify-between mb-5">
      <div>
        <div className="flex items-center gap-2 text-xs font-semibold tracking-[0.2em] uppercase text-slate-500 mb-1">
          {icon}
          <span>{eyebrow}</span>
        </div>
        <h2 className="text-xl md:text-2xl font-bold text-slate-900">{title}</h2>
      </div>
    </div>
    {loading ? (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="overflow-hidden bg-white">
            <div className="h-32 bg-slate-100 animate-pulse" />
            <div className="p-4 space-y-2">
              <div className="h-3 bg-slate-100 rounded w-3/4 animate-pulse" />
              <div className="h-3 bg-slate-100 rounded w-1/2 animate-pulse" />
            </div>
          </Card>
        ))}
      </div>
    ) : items.length === 0 ? (
      <p className="text-sm text-slate-500">{emptyText}</p>
    ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {items.map(p => <CompactProgramCard key={p.id} p={p} />)}
      </div>
    )}
  </div>
);

const CompactProgramCard = ({ p }) => (
  <Link
    to={`/programy-pro-skoly/p/${p.id}`}
    className="group block"
    data-testid={`discover-card-${p.id}`}
  >
    <Card className="overflow-hidden bg-white border border-slate-100 hover:border-[#4A6FA5]/30 hover:shadow-md transition-all h-full">
      <div className="relative h-32 bg-gradient-to-br from-[#EEF2F9] to-[#F8F9FA] overflow-hidden">
        {p.image_url ? (
          <img src={p.image_url} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-[#4A6FA5]/30" />
          </div>
        )}
        {p.age_labels?.[0] && (
          <Badge className="absolute top-2 left-2 bg-white/95 text-[#4A6FA5] hover:bg-white border-0 text-[11px] backdrop-blur-sm">
            {p.age_labels[0]}
          </Badge>
        )}
      </div>
      <div className="p-4">
        <h3 className="text-sm font-semibold text-slate-900 line-clamp-2 group-hover:text-[#4A6FA5] mb-1">
          {p.name}
        </h3>
        <p className="text-xs text-slate-500 line-clamp-1">{p.institution.name}</p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400 mt-2">
          {p.institution.city && (
            <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" />{p.institution.city}</span>
          )}
          <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" />{p.duration} min</span>
        </div>
      </div>
    </Card>
  </Link>
);
