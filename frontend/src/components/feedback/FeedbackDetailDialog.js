import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';

export function formatFeedbackAnswer(value, type) {
  if (value == null || (typeof value === 'string' && !value.trim())) return 'Nezodpovězeno';
  if (value === true) return 'Ano';
  if (value === false) return 'Ne';
  if (typeof value === 'number' && (type === 'rating' || type === 'scale')) return `${value} / 5`;
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

function formatDate(value, withTime = false) {
  if (!value) return 'Neuvedeno';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Neuvedeno';
  return new Intl.DateTimeFormat('cs-CZ', {
    dateStyle: 'medium',
    ...(withTime ? { timeStyle: 'short' } : {}),
    timeZone: 'Europe/Prague',
  }).format(date);
}

export default function FeedbackDetailDialog({ feedbackId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setData(null);
    setError(false);
    if (!feedbackId) return;
    const controller = new AbortController();
    axios
      .get(`${process.env.REACT_APP_BACKEND_URL}/api/feedback/submissions/${feedbackId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        signal: controller.signal,
      })
      .then((response) => {
        if (!controller.signal.aborted) {
          if (!Array.isArray(response.data?.question_answers)) {
            setError(true);
          } else {
            setData(response.data);
          }
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [feedbackId, attempt]);

  return (
    <Dialog
      open={Boolean(feedbackId)}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-w-2xl max-h-[85dvh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Detail zpětné vazby</DialogTitle>
          <DialogDescription>Celý dotazník včetně komentáře a vlastních otázek.</DialogDescription>
        </DialogHeader>
        {error ? (
          <div role="alert">
            <p>Detail se nepodařilo načíst nebo k němu nemáte přístup.</p>
            <button
              type="button"
              className="underline mt-2"
              onClick={() => setAttempt((n) => n + 1)}
            >
              Zkusit znovu
            </button>
          </div>
        ) : !data ? (
          <p role="status">Načítání odpovědí…</p>
        ) : (
          <div className="space-y-5 min-w-0 break-words">
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                ['Program', data.program_name || 'Program již není dostupný'],
                ['Škola', data.school_name || 'Neuvedeno'],
                ['Datum návštěvy', formatDate(data.reservation_date)],
                [
                  'Vyplněno',
                  data.submitted_at ? formatDate(data.submitted_at, true) : 'Dosud nevyplněno',
                ],
                ['Celkové hodnocení', formatFeedbackAnswer(data.overall_rating, 'rating')],
                ['Doporučuje', formatFeedbackAnswer(data.would_recommend, 'yesno')],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-sm text-gray-500">{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <section>
              <h3 className="font-semibold mb-2">Dobrovolný komentář</h3>
              <p className="whitespace-pre-wrap">
                {data.additional_comments?.trim() ? data.additional_comments : 'Bez komentáře'}
              </p>
            </section>
            <section className="space-y-3">
              <h3 className="font-semibold">Odpovědi na vlastní otázky</h3>
              {data.questions_version === 'legacy' && (
                <p className="text-sm bg-amber-50 p-3 rounded-lg">
                  U tohoto staršího záznamu nebylo uloženo původní znění otázek. Zobrazujeme
                  dostupné současné znění, které se mohlo změnit. Chybějící znění nelze spolehlivě
                  obnovit.
                </p>
              )}
              {data.question_answers?.length ? (
                data.question_answers.map((question) => (
                  <div key={question.id} className="border rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-1">
                      {question.source === 'program'
                        ? 'Otázka programu'
                        : question.source === 'institution'
                          ? 'Otázka instituce'
                          : 'Nedohledaná otázka'}
                    </p>
                    <h4 className="font-medium whitespace-pre-wrap">{question.question_text}</h4>
                    {question.wording_status === 'missing' && (
                      <p className="text-xs text-gray-500">ID otázky: {question.id}</p>
                    )}
                    <p className="mt-2 whitespace-pre-wrap">
                      {formatFeedbackAnswer(question.answer, question.question_type)}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-gray-500">Žádné zaznamenané odpovědi na vlastní otázky.</p>
              )}
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
