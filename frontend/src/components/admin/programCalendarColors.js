export const PROGRAM_CALENDAR_COLORS = [
  { bg: '#8DA992', border: '#6c8a72', text: '#ffffff' },
  { bg: '#457B56', border: '#2f5d3e', text: '#ffffff' },
  { bg: '#B8E0E0', border: '#5E9E9E', text: '#183F40' },
  { bg: '#E5C877', border: '#bf9f4f', text: '#4d3a0c' },
  { bg: '#EE7D36', border: '#c45c1c', text: '#ffffff' },
  { bg: '#D8C4F0', border: '#9A75BE', text: '#3C2751' },
  { bg: '#DEE9FC', border: '#a8bee0', text: '#1f3461' },
  { bg: '#263FA8', border: '#172a7a', text: '#ffffff' },
];

export const programCalendarKey = (reservation) =>
  String(reservation.program_id || reservation.program_name || '—');

// Kept for backwards-compatible tests/imports. The color map below avoids using
// modulo assignment for distinct programs because modulo can make two programs
// share one visible colour in the same calendar.
export const programCalendarColorIndex = (key) => {
  let hash = 0;
  for (const char of String(key || '—')) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % PROGRAM_CALENDAR_COLORS.length;
};

const generatedProgramColor = (index) => {
  const hue = Math.round((index * 137.508) % 360);
  return {
    bg: `hsl(${hue} 58% 72%)`,
    border: `hsl(${hue} 45% 42%)`,
    text: `hsl(${hue} 42% 18%)`,
  };
};

export const programCalendarColorForPosition = (index) =>
  PROGRAM_CALENDAR_COLORS[index] || generatedProgramColor(index - PROGRAM_CALENDAR_COLORS.length);

export const buildProgramCalendarColorMap = (reservations = []) => {
  const keys = Array.from(new Set(reservations.map(programCalendarKey))).sort();
  return keys.reduce((map, key, index) => {
    map[key] = programCalendarColorForPosition(index);
    return map;
  }, {});
};
