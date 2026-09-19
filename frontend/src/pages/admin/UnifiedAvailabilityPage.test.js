/* eslint-env jest */
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import { toast } from 'sonner';
import { UnifiedAvailabilityPage } from './UnifiedAvailabilityPage';
import { AuthContext } from '../../context/AuthContext';

// CRA's Jest runner does not inherit the webpack @ alias.
jest.mock('@/lib/utils', () => jest.requireActual('../../lib/utils'), { virtual: true });
jest.mock('axios');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../../components/layout/AdminLayout', () => ({
  AdminLayout: ({ children }) => <div>{children}</div>,
}));
jest.mock('./LecturerAvailabilityPage', () => ({
  LecturerAvailabilityPage: ({ onViewToggle }) => (
    <button data-testid="personal-calendar" onClick={() => onViewToggle('program')}>
      Programová
    </button>
  ),
}));
jest.mock('../../components/ui/select', () => ({
  Select: ({ value, onValueChange, children }) => (
    <select
      data-testid="program-select"
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
    >
      {children}
    </select>
  ),
  SelectTrigger: () => null,
  SelectValue: () => null,
  SelectContent: ({ children }) => <>{children}</>,
  SelectItem: ({ value, children }) => <option value={value}>{children}</option>,
}));
jest.mock('../../components/ui/dialog', () => ({
  Dialog: ({ open, children }) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }) => <div>{children}</div>,
  DialogHeader: ({ children }) => <div>{children}</div>,
  DialogTitle: ({ children }) => <h2>{children}</h2>,
}));

global.IS_REACT_ACT_ENVIRONMENT = true;
let container;
let root;
let records;
const programs = [
  {
    id: 'other-program',
    name_cs: 'Jiný program',
    status: 'active',
    available_days: ['tuesday'],
    time_blocks: ['09:00-10:30'],
  },
  {
    id: 'mucha-program',
    name_cs: 'Nej z nej: Alfonse Muchy',
    status: 'active',
    available_days: ['tuesday'],
    time_blocks: ['09:00-10:30'],
  },
];
const click = async (selector) => {
  await act(async () => container.querySelector(selector).click());
};
const input = async (selector, value) => {
  await act(async () => {
    const element = container.querySelector(selector);
    const prototype =
      element.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value);
    element.dispatchEvent(
      new Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })
    );
  });
};
const submit = async () => {
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  );
};

beforeEach(async () => {
  jest.clearAllMocks();
  records = [];
  axios.get.mockImplementation(async (url) => {
    if (url.endsWith('/programs')) return { data: programs };
    if (url.endsWith('/one-offs'))
      return { data: records.filter((r) => url.includes(r.program_id)) };
    if (url.includes('/slots?date='))
      return {
        data: {
          slots: records
            .filter((r) => url.includes(r.program_id) && url.endsWith(r.date))
            .map((r) => ({ time: `${r.start_time}-${r.end_time}`, status: 'available' })),
        },
      };
    return { data: [] };
  });
  axios.post.mockImplementation(async (url, data) => {
    const record = { id: 'saved-slot', program_id: 'mucha-program', ...data };
    records.push(record);
    return { data: record };
  });
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () =>
    root.render(
      <AuthContext.Provider value={{ user: { role: 'admin' } }}>
        <UnifiedAvailabilityPage embedded />
      </AuthContext.Provider>
    )
  );
  await click('[data-testid="personal-calendar"]');
  await input('[data-testid="program-select"]', 'mucha-program');
  await click('[data-testid="program-add-oneoff-btn"]');
  await input('#program-one-off-date', '2026-09-22');
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});

test('saves to selected program, keeps program calendar and shows target week and summary', async () => {
  await submit();
  expect(axios.post).toHaveBeenCalledWith(
    expect.stringContaining('/program/mucha-program/one-offs'),
    {
      date: '2026-09-22',
      start_time: '13:30',
      end_time: '15:00',
    }
  );
  expect(container.querySelector('[data-testid="personal-calendar"]')).toBeNull();
  expect(container.querySelector('[data-testid="program-select"]').value).toBe('mucha-program');
  expect(container.querySelector('form')).toBeNull();
  expect(container.querySelector('[data-testid="program-one-off-summary"]').textContent).toContain(
    '2026-09-22 · 13:30–15:00'
  );
  expect(axios.get).toHaveBeenCalledWith(
    expect.stringContaining('/program/mucha-program/slots?date=2026-09-22')
  );
  expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Alfonse Muchy'));
});

test('API failure retains date, selected program and dialog without success toast', async () => {
  axios.post.mockRejectedValueOnce({
    response: { data: { detail: 'Termín musí být v období konání programu' } },
  });
  await submit();
  expect(container.querySelector('#program-one-off-date').value).toBe('2026-09-22');
  expect(container.querySelector('[data-testid="program-select"]').value).toBe('mucha-program');
  expect(container.textContent).toContain('Termín musí být v období konání programu');
  expect(toast.success).not.toHaveBeenCalled();
});

test('invalid time does not send a request', async () => {
  await input('#program-one-off-end', '12:00');
  await submit();
  expect(axios.post).not.toHaveBeenCalled();
  expect(container.textContent).toContain('Konec musí být později než začátek');
});

test('in-flight save disables repeated submissions', async () => {
  let finish;
  axios.post.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  await submit();
  expect(container.querySelector('[data-testid="program-one-off-submit"]').disabled).toBe(true);
  await submit();
  expect(axios.post).toHaveBeenCalledTimes(1);
  await act(async () =>
    finish({
      data: {
        id: 'saved-slot',
        program_id: 'mucha-program',
        date: '2026-09-22',
        start_time: '13:30',
        end_time: '15:00',
      },
    })
  );
});
