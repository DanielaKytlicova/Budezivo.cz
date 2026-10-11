import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { stageClass } from '../../services/leadsApi';

const types = {
  museum: ['◆', '#28618c'],
  gallery: ['▣', '#7550a8'],
  library: ['▤', '#26765b'],
  botanical: ['✿', '#287341'],
  science: ['✹', '#8c5c0a'],
  visitor: ['●', '#a94e28'],
  theatre: ['◒', '#a5394a'],
  zoo: ['◈', '#246e53'],
  eco: ['♧', '#48752c'],
  education: ['★', '#805b0c'],
  cinema: ['▶', '#a23f74'],
};

export default function LeadMap({ items, onSelect }) {
  const element = useRef(null),
    map = useRef(null),
    layer = useRef(null),
    select = useRef(onSelect);
  useEffect(() => {
    select.current = onSelect;
  }, [onSelect]);
  useEffect(() => {
    map.current = L.map(element.current).setView([50.35, 14.7], 8);
    const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map.current);
    tiles.on('tileerror', () => {
      if (element.current) element.current.dataset.tileError = 'true';
    });
    layer.current = L.layerGroup().addTo(map.current);
    const resize = new ResizeObserver(() => map.current?.invalidateSize());
    resize.observe(element.current);
    return () => {
      resize.disconnect();
      map.current.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    if (!map.current) return;
    const draw = () => {
      layer.current.clearLayers();
      // Group overlapping screen positions at every zoom; cluster popup offers every lead.
      const groups = new Map();
      items
        .filter((x) => x.lat != null && x.lng != null)
        .forEach((item) => {
          const point = map.current.project([item.lat, item.lng]);
          const key = `${Math.round(point.x / 42)}:${Math.round(point.y / 42)}`;
          if (!groups.has(key)) groups.set(key, []);
          groups.get(key).push(item);
        });
      groups.forEach((group) => {
        const item = group[0],
          [symbol, color] = types[item.type] || ['●', '#46586b'];
        const icon = L.divIcon({
          className: 'lead-marker-wrap',
          html: `<span class="lead-marker ${stageClass(item.stage)}" style="--lead-color:${color}">${group.length > 1 ? group.length : symbol}</span>`,
          iconSize: [36, 36],
        });
        const marker = L.marker([item.lat, item.lng], {
          icon,
          title:
            group.length > 1
              ? `${group.length} institucí – otevřít seznam`
              : `${item.name} – ${item.stage}`,
          keyboard: true,
        }).addTo(layer.current);
        if (group.length === 1) marker.on('click', () => select.current(item.id));
        else {
          const list = document.createElement('div');
          list.className = 'lead-cluster-list';
          group.forEach((row) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = `${row.name} · ${row.stage}`;
            button.onclick = () => select.current(row.id);
            list.appendChild(button);
          });
          marker.bindPopup(list);
        }
      });
    };
    draw();
    map.current.on('zoomend', draw);
    return () => map.current?.off('zoomend', draw);
  }, [items]);
  return (
    <div className="lead-map-box">
      <div ref={element} className="lead-map" aria-label="Mapa institucí" />
      <p className="lead-map-warning">
        Poloha může být přibližná. Při nedostupnosti mapového podkladu použijte seznam institucí.
      </p>
    </div>
  );
}
