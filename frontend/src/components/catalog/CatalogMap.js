import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { cityToLatLng, CZ_CENTER } from '../../lib/czCities';
import { MapPin, Building2 } from 'lucide-react';

// ─── Fix Leaflet's default icon URLs (webpack breaks the relative paths) ──────
// We inject a custom divIcon so we get pill-shaped markers matching the brand.
// eslint-disable-next-line no-underscore-dangle
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const badgeIcon = (count) => L.divIcon({
  className: 'catalog-city-marker',
  html: `
    <div style="
      background: #4A6FA5;
      color: #fff;
      border: 3px solid #fff;
      border-radius: 999px;
      padding: 4px 12px;
      font-weight: 700;
      font-size: 14px;
      box-shadow: 0 6px 18px rgba(0,0,0,0.25);
      white-space: nowrap;
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    ">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 7-8 13-8 13s-8-6-8-13a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
      ${count}
    </div>
  `,
  iconSize: [60, 30],
  iconAnchor: [30, 30],
  popupAnchor: [0, -30],
});

/**
 * Group programs by their institution city and aggregate counts.
 * Programs whose city cannot be resolved are put into an "Ostatní" bucket
 * shown beneath the map.
 */
function groupByCity(items) {
  const groups = {}; // city → { lat, lng, programs[], institutions: Set }
  const unknown = [];
  for (const p of items) {
    const city = p.institution?.city;
    const ll = cityToLatLng(city);
    if (!ll || !city) {
      unknown.push(p);
      continue;
    }
    if (!groups[city]) {
      groups[city] = { lat: ll[0], lng: ll[1], city, programs: [], institutions: new Set() };
    }
    groups[city].programs.push(p);
    groups[city].institutions.add(p.institution?.name || '—');
  }
  return {
    cityGroups: Object.values(groups).sort((a, b) => b.programs.length - a.programs.length),
    unknown,
  };
}

/**
 * CatalogMap — Leaflet-based map view for the B2B catalog.
 * Pins are aggregated per city; clicking a pin opens a popup listing the
 * institutions (with program counts) so users can jump into the detail view.
 */
export const CatalogMap = ({ items = [], onInstitutionFilter }) => {
  const { cityGroups, unknown } = useMemo(() => groupByCity(items), [items]);

  return (
    <div className="space-y-4" data-testid="catalog-map-view">
      <div
        className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-white"
        style={{ height: 520 }}
      >
        <MapContainer
          center={CZ_CENTER}
          zoom={7}
          scrollWheelZoom
          style={{ height: '100%', width: '100%' }}
          data-testid="catalog-map-container"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {cityGroups.map(grp => (
            <Marker
              key={grp.city}
              position={[grp.lat, grp.lng]}
              icon={badgeIcon(grp.programs.length)}
              eventHandlers={{
                add: (e) => {
                  // Expose city on marker DOM for E2E tests
                  const el = e.target.getElement();
                  if (el) el.setAttribute('data-testid', `map-pin-${grp.city.toLowerCase().replace(/\s+/g, '-')}`);
                },
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                <strong>{grp.city}</strong> · {grp.programs.length} {grp.programs.length === 1 ? 'program' : grp.programs.length < 5 ? 'programy' : 'programů'}
              </Tooltip>
              <Popup maxWidth={320} minWidth={260}>
                <div data-testid={`map-popup-${grp.city.toLowerCase().replace(/\s+/g, '-')}`}>
                  <div className="flex items-center gap-1.5 mb-2 text-sm font-bold text-[#2B3E50]">
                    <MapPin className="w-4 h-4 text-[#4A6FA5]" />
                    {grp.city}
                  </div>
                  <div className="text-xs text-gray-500 mb-3">
                    {grp.programs.length} {grp.programs.length === 1 ? 'program' : grp.programs.length < 5 ? 'programy' : 'programů'} ·{' '}
                    {grp.institutions.size} {grp.institutions.size === 1 ? 'instituce' : grp.institutions.size < 5 ? 'instituce' : 'institucí'}
                  </div>
                  <ul className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                    {grp.programs.slice(0, 10).map(p => (
                      <li key={p.id}>
                        <Link
                          to={`/programy-pro-skoly/p/${p.id}`}
                          className="block text-xs text-[#4A6FA5] hover:underline"
                          data-testid={`map-program-link-${p.id}`}
                        >
                          <span className="font-semibold text-[#2B3E50]">{p.name}</span>
                          <span className="text-gray-500 block">
                            <Building2 className="inline w-3 h-3 mr-0.5" />
                            {p.institution?.name}
                            {p.duration ? ` · ${p.duration} min` : ''}
                          </span>
                        </Link>
                      </li>
                    ))}
                    {grp.programs.length > 10 && (
                      <li className="text-xs text-gray-400 pt-1 border-t border-gray-100">
                        …a dalších {grp.programs.length - 10} programů
                      </li>
                    )}
                  </ul>
                  {onInstitutionFilter && (
                    <button
                      type="button"
                      onClick={() => onInstitutionFilter(grp.city)}
                      className="mt-3 w-full text-xs font-medium text-[#4A6FA5] hover:underline"
                      data-testid={`map-filter-city-${grp.city.toLowerCase().replace(/\s+/g, '-')}`}
                    >
                      Filtrovat katalog na {grp.city} →
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {unknown.length > 0 && (
        <div
          className="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm text-gray-600"
          data-testid="catalog-map-unknown"
        >
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold tracking-wider uppercase text-gray-500">
            <MapPin className="w-3.5 h-3.5" />
            Bez známé polohy ({unknown.length})
          </div>
          <p className="text-xs text-gray-500 mb-2">Tyto programy zatím nemají v katalogu vyplněné město, proto je nezobrazujeme na mapě:</p>
          <ul className="space-y-1 max-h-40 overflow-y-auto">
            {unknown.map(p => (
              <li key={p.id}>
                <Link to={`/programy-pro-skoly/p/${p.id}`} className="text-xs text-[#4A6FA5] hover:underline">
                  {p.name} — {p.institution?.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CatalogMap;
