export const PROGRAM_CALENDAR_COLORS = [
  { bg: '#8DA992', border: '#6c8a72', text: '#ffffff' },
  { bg: '#457B56', border: '#2f5d3e', text: '#ffffff' },
  { bg: '#FCF3D4', border: '#e7d8a3', text: '#5a4b1e' },
  { bg: '#E5C877', border: '#bf9f4f', text: '#4d3a0c' },
  { bg: '#EE7D36', border: '#c45c1c', text: '#ffffff' },
  { bg: '#FCEED8', border: '#e8d6b3', text: '#5a4524' },
  { bg: '#DEE9FC', border: '#a8bee0', text: '#1f3461' },
  { bg: '#263FA8', border: '#172a7a', text: '#ffffff' },
];

export const programCalendarKey = (reservation) =>
  String(reservation.program_id || reservation.program_name || '—');

// Deterministic across pages and integrations: the colour no longer changes
// when filters hide another program or a newly-created program is added.
export const programCalendarColorIndex = (key) => {
  let hash = 0;
  for (const char of String(key || '—')) hash = ((hash * 31) + char.charCodeAt(0)) >>> 0;
  return hash % PROGRAM_CALENDAR_COLORS.length;
};

export const buildProgramCalendarColorMap = (reservations = []) => {
  const keys = Array.from(new Set(reservations.map(programCalendarKey))).sort();
  return keys.reduce((map, key) => {
    map[key] = PROGRAM_CALENDAR_COLORS[programCalendarColorIndex(key)];
    return map;
  }, {});
};
