/* eslint-env jest */
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import FeedbackDetailDialog, { formatFeedbackAnswer } from './FeedbackDetailDialog';

jest.mock('axios');
jest.mock('../ui/dialog', () => ({
  Dialog: ({ open, children }) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }) => <div>{children}</div>,
  DialogHeader: ({ children }) => <div>{children}</div>,
  DialogTitle: ({ children }) => <h2>{children}</h2>,
  DialogDescription: ({ children }) => <p>{children}</p>,
}));

global.IS_REACT_ACT_ENVIRONMENT = true;
let container;
let root;
const detail = {
  program_name: 'Program',
  school_name: 'Škola',
  reservation_date: '2026-10-23',
  submitted_at: '2026-10-23T08:00:00Z',
  overall_rating: 4,
  would_recommend: false,
  additional_comments: 'Celý komentář\nDruhý řádek <script>test</script>',
  questions_version: 'snapshot',
  question_answers: [
    {
      id: 'q',
      question_text: 'Doporučili byste?',
      question_type: 'yesno',
      answer: false,
      source: 'institution',
    },
    {
      id: 'p',
      question_text: 'Co změnit?',
      question_type: 'text',
      answer: 'Více času\nna dílnu',
      source: 'program',
    },
    { id: 'empty', question_text: 'Volitelné', question_type: 'text', answer: null },
  ],
};
beforeEach(() => {
  jest.clearAllMocks();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  localStorage.setItem('token', 'test-only');
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  localStorage.clear();
});
const show = async (id = 'one') => {
  await act(async () => root.render(<FeedbackDetailDialog feedbackId={id} onClose={() => {}} />));
};

test('renders complete comments and both question sources, false is not unanswered', async () => {
  axios.get.mockResolvedValue({ data: detail });
  await show();
  expect(container.textContent).toContain(detail.additional_comments);
  expect(container.textContent).toContain('Více času\nna dílnu');
  expect(container.textContent).toContain('Otázka programu');
  expect(container.textContent).toContain('Otázka instituce');
  expect(container.textContent).toContain('Nezodpovězeno');
  expect(container.querySelector('script')).toBeNull();
  expect(formatFeedbackAnswer(false, 'yesno')).toBe('Ne');
  expect(formatFeedbackAnswer(true, 'yesno')).toBe('Ano');
  expect(formatFeedbackAnswer(0, 'unknown')).toBe('0');
  expect(formatFeedbackAnswer(' ', 'text')).toBe('Nezodpovězeno');
  expect(formatFeedbackAnswer(4, 'rating')).toBe('4 / 5');
  expect(axios.get.mock.calls[0][1].headers.Authorization).toBe('Bearer test-only');
});

test('legacy warning and missing question preserve the answer', async () => {
  axios.get.mockResolvedValue({
    data: {
      ...detail,
      questions_version: 'legacy',
      question_answers: [
        {
          id: 'deleted',
          question_text: 'Původní znění otázky není dostupné',
          answer: 'Uložená odpověď',
          wording_status: 'missing',
        },
      ],
    },
  });
  await show();
  expect(container.textContent).toContain('současné znění');
  expect(container.textContent).toContain('ID otázky: deleted');
  expect(container.textContent).toContain('Uložená odpověď');
});

test('failure is visible and can be retried', async () => {
  axios.get.mockRejectedValueOnce(new Error('unavailable')).mockResolvedValueOnce({ data: detail });
  await show();
  expect(container.querySelector('[role="alert"]')).not.toBeNull();
  await act(async () => container.querySelector('button').click());
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(container.textContent).toContain('Doporučili byste?');
});

test('late response cannot replace a subsequently opened feedback', async () => {
  let finishFirst;
  axios.get
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finishFirst = resolve;
        })
    )
    .mockResolvedValueOnce({ data: { ...detail, program_name: 'Druhý program' } });
  await show('one');
  const firstSignal = axios.get.mock.calls[0][1].signal;
  await show('two');
  await act(async () => finishFirst({ data: { ...detail, program_name: 'Starý program' } }));
  expect(firstSignal.aborted).toBe(true);
  expect(container.textContent).toContain('Druhý program');
  expect(container.textContent).not.toContain('Starý program');
});

test('closed dialog does not request any personal data', async () => {
  await show(null);
  expect(axios.get).not.toHaveBeenCalled();
  expect(container.textContent).toBe('');
});

test('old backend response is not presented as an empty questionnaire', async () => {
  axios.get.mockResolvedValue({ data: { answers: { q: 'Still stored' } } });
  await show();
  expect(container.querySelector('[role="alert"]')).not.toBeNull();
  expect(container.textContent).not.toContain('Žádné zaznamenané odpovědi');
});
