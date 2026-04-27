/**
 * Static lookup of Czech cities → approximate centroid [lat, lng].
 *
 * Covers the top ~70 cities by population + cultural-institution frequency.
 * Fallback for any city not in this list is the center of the Czech Republic
 * (Žďár nad Sázavou area).
 *
 * Data sourced from public domain geographic databases (Wikipedia, GeoNames).
 */
const CZ_CITIES = {
  // Praha a okolí
  'praha': [50.0755, 14.4378],
  'prague': [50.0755, 14.4378],

  // Největší města
  'brno': [49.1951, 16.6068],
  'ostrava': [49.8209, 18.2625],
  'plzeň': [49.7384, 13.3736],
  'plzen': [49.7384, 13.3736],
  'liberec': [50.7671, 15.0562],
  'olomouc': [49.5939, 17.2509],
  'české budějovice': [48.9745, 14.4744],
  'ceske budejovice': [48.9745, 14.4744],
  'hradec králové': [50.2104, 15.8252],
  'hradec kralove': [50.2104, 15.8252],
  'pardubice': [50.0343, 15.7812],
  'ústí nad labem': [50.6607, 14.0323],
  'usti nad labem': [50.6607, 14.0323],
  'zlín': [49.2264, 17.6704],
  'zlin': [49.2264, 17.6704],
  'havířov': [49.7784, 18.4369],
  'havirov': [49.7784, 18.4369],
  'kladno': [50.1477, 14.1028],
  'most': [50.5031, 13.6362],
  'opava': [49.9412, 17.9026],
  'frýdek-místek': [49.6808, 18.3500],
  'frydek-mistek': [49.6808, 18.3500],
  'karviná': [49.8540, 18.5410],
  'karvina': [49.8540, 18.5410],
  'jihlava': [49.3961, 15.5911],
  'teplice': [50.6404, 13.8245],
  'děčín': [50.7821, 14.2148],
  'decin': [50.7821, 14.2148],
  'chomutov': [50.4603, 13.4180],
  'přerov': [49.4551, 17.4509],
  'prerov': [49.4551, 17.4509],
  'jablonec nad nisou': [50.7241, 15.1700],
  'mladá boleslav': [50.4109, 14.9030],
  'mlada boleslav': [50.4109, 14.9030],
  'prostějov': [49.4719, 17.1117],
  'prostejov': [49.4719, 17.1117],
  'třebíč': [49.2150, 15.8794],
  'trebic': [49.2150, 15.8794],
  'třinec': [49.6776, 18.6700],
  'trinec': [49.6776, 18.6700],
  'česká lípa': [50.6854, 14.5388],
  'ceska lipa': [50.6854, 14.5388],
  'tábor': [49.4142, 14.6575],
  'tabor': [49.4142, 14.6575],
  'znojmo': [48.8554, 16.0489],
  'cheb': [50.0796, 12.3705],
  'kolín': [50.0275, 15.2006],
  'kolin': [50.0275, 15.2006],
  'písek': [49.3089, 14.1478],
  'pisek': [49.3089, 14.1478],
  'příbram': [49.6898, 14.0098],
  'pribram': [49.6898, 14.0098],
  'orlová': [49.8453, 18.4303],
  'orlova': [49.8453, 18.4303],
  'trutnov': [50.5614, 15.9125],
  'kroměříž': [49.2981, 17.3928],
  'kromeriz': [49.2981, 17.3928],
  'vsetín': [49.3381, 17.9956],
  'vsetin': [49.3381, 17.9956],
  'šumperk': [49.9650, 16.9697],
  'sumperk': [49.9650, 16.9697],
  'uherské hradiště': [49.0704, 17.4596],
  'uherske hradiste': [49.0704, 17.4596],
  'břeclav': [48.7531, 16.8817],
  'breclav': [48.7531, 16.8817],
  'hodonín': [48.8488, 17.1298],
  'hodonin': [48.8488, 17.1298],
  'český těšín': [49.7467, 18.6262],
  'cesky tesin': [49.7467, 18.6262],
  'beroun': [49.9636, 14.0728],
  'žďár nad sázavou': [49.5641, 15.9398],
  'zdar nad sazavou': [49.5641, 15.9398],
  'litoměřice': [50.5353, 14.1317],
  'litomerice': [50.5353, 14.1317],
  'nymburk': [50.1854, 15.0424],
  'krnov': [50.0875, 17.7058],
  'mělník': [50.3516, 14.4736],
  'melnik': [50.3516, 14.4736],
  'kutná hora': [49.9480, 15.2680],
  'kutna hora': [49.9480, 15.2680],
  'vyškov': [49.2769, 16.9983],
  'vyskov': [49.2769, 16.9983],
  'blansko': [49.3636, 16.6450],
  'jindřichův hradec': [49.1443, 15.0030],
  'jindrichuv hradec': [49.1443, 15.0030],
  'strakonice': [49.2610, 13.9023],
  'klatovy': [49.3958, 13.2954],
  'rakovník': [50.1037, 13.7345],
  'rakovnik': [50.1037, 13.7345],
};

export const CZ_CENTER = [49.8175, 15.4730]; // střed ČR

/**
 * Resolve a city name to approximate [lat, lng].
 * Matching is case-insensitive and diacritics-sensitive first; falls back to
 * the ASCII-folded key if the exact match fails.
 */
export function cityToLatLng(city) {
  if (!city || typeof city !== 'string') return null;
  const raw = city.trim().toLowerCase();
  if (CZ_CITIES[raw]) return CZ_CITIES[raw];

  const ascii = raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // strip diacritics
    .replace(/\s+/g, ' ')
    .trim();
  if (CZ_CITIES[ascii]) return CZ_CITIES[ascii];
  return null;
}

export default CZ_CITIES;
