import { API } from '../config/api';

const key = 'budezivo_crm_session';
let refreshing = null;
const readSession = () => {
  try {
    return JSON.parse(sessionStorage.getItem(key) || 'null');
  } catch {
    return null;
  }
};
export const clearLeadSession = () => sessionStorage.removeItem(key);

async function parse(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(
      typeof body.detail === 'string'
        ? body.detail
        : 'Zkontrolujte vyplněné údaje a zkuste to znovu.'
    );
    error.status = response.status;
    throw error;
  }
  return response;
}

export async function leadLogin(username, password) {
  const response = await parse(
    await fetch(`${API}/leads/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'omit',
    })
  );
  const session = await response.json();
  sessionStorage.setItem(key, JSON.stringify(session));
  return session.user;
}

export async function leadsApi(path = '', options = {}, retry = true) {
  const session = readSession();
  const token = session?.token || localStorage.getItem('token');
  const response = await fetch(`${API}/leads${path}`, {
    ...options,
    credentials: session ? 'omit' : 'include',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.status === 401 && session?.refresh_token && retry) {
    if (!refreshing) {
      refreshing = (async () => {
        const refreshed = await parse(
          await fetch(`${API}/leads/auth/refresh`, {
            method: 'POST',
            credentials: 'omit',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: session.refresh_token }),
          })
        );
        sessionStorage.setItem(key, JSON.stringify(await refreshed.json()));
      })()
        .catch((error) => {
          clearLeadSession();
          throw error;
        })
        .finally(() => {
          refreshing = null;
        });
    }
    await refreshing;
    return leadsApi(path, options, false);
  }
  await parse(response);
  return options.download ? response.blob() : response.json();
}

export const leadQuery = (filters) =>
  new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== false)
  ).toString();
export async function allLeads(filters = {}) {
  let items = [],
    total = 0;
  do {
    const page = await leadsApi(`?${leadQuery({ ...filters, offset: items.length, limit: 500 })}`);
    items = items.concat(page.items);
    total = page.total;
    if (!page.items.length) break;
  } while (items.length < total);
  return items;
}
export const pipelineGroup = (stage) => {
  if (stage.startsWith('Připojeno')) return 'Připojeno';
  if (['Odmítli', 'Rozhodnutí odloženo'].includes(stage)) return 'Odloženo / odmítli';
  if (stage === 'Neobchodní / pouze katalog') return 'Pouze katalog';
  if (stage === 'Připraveno k oslovení') return 'K oslovení';
  if (stage === 'Dosud neosloveno' || stage === 'Výzkum / ověřit') return 'Výzkum';
  return 'V kontaktu';
};
export const stageClass = (stage) =>
  stage === 'Připojeno – platící'
    ? 'paying'
    : stage.startsWith('Připojeno')
      ? 'connected'
      : stage === 'Odmítli'
        ? 'declined'
        : stage === 'Rozhodnutí odloženo'
          ? 'postponed'
          : pipelineGroup(stage) === 'V kontaktu'
            ? 'contacted'
            : 'new';
