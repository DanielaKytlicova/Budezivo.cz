import React from 'react';
import { Card } from '../ui/card';
import { Input } from '../ui/input';
import { Switch } from '../ui/switch';
import { Plus, Trash2, Star, MessageSquare, Lock } from 'lucide-react';
import { toast } from 'sonner';

export const ProgramFeedbackTab = ({ formData, setFormData, isPro }) => {
  const questionTypes = [
    { value: 'text', label: 'Textová odpověď' },
    { value: 'scale', label: 'Škála 1-5' },
    { value: 'yesno', label: 'Ano / Ne' },
  ];

  const addQuestion = () => {
    if (formData.feedback_questions.length >= 5) {
      toast.error('Maximální počet otázek je 5');
      return;
    }
    setFormData(prev => ({
      ...prev,
      feedback_questions: [
        ...prev.feedback_questions,
        { id: Date.now().toString(), question: '', type: 'text' }
      ]
    }));
  };

  const updateQuestion = (id, field, value) => {
    setFormData(prev => ({
      ...prev,
      feedback_questions: prev.feedback_questions.map(q =>
        q.id === id ? { ...q, [field]: value } : q
      )
    }));
  };

  const removeQuestion = (id) => {
    setFormData(prev => ({
      ...prev,
      feedback_questions: prev.feedback_questions.filter(q => q.id !== id)
    }));
  };

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Výchozí zpětná vazba */}
      <Card className="p-4 md:p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-slate-900">Zpětná vazba</h3>
            <p className="text-sm text-gray-500 mt-1">Povolit sběr zpětné vazby po dokončení programu</p>
          </div>
          <Switch
            checked={formData.feedback_enabled}
            onCheckedChange={(checked) => setFormData(prev => ({ ...prev, feedback_enabled: checked }))}
            data-testid="feedback-enabled-toggle"
          />
        </div>

        {formData.feedback_enabled && (
          <div className="border-t border-gray-100 pt-4 mt-4">
            <h4 className="text-sm font-medium text-slate-700 mb-3">Výchozí zpětná vazba (vždy přítomná)</h4>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <Star className="w-4 h-4 text-amber-500" />
                <span className="text-sm text-slate-700">Hodnocení hvězdičkami (1-5)</span>
                <span className="ml-auto text-xs text-gray-400">povinné</span>
              </div>
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <MessageSquare className="w-4 h-4 text-blue-500" />
                <span className="text-sm text-slate-700">Doporučuji / Nedoporučuji</span>
                <span className="ml-auto text-xs text-gray-400">povinné</span>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Individuální otázky - PRO */}
      {formData.feedback_enabled && (
        <Card className="p-4 md:p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                Individuální otázky
                {!isPro && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">PRO</span>}
              </h3>
              <p className="text-sm text-gray-500 mt-1">Vlastní otázky specifické pro tento program (max 5)</p>
            </div>
          </div>

          {!isPro ? (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
              <Lock className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600 mb-2">Individuální otázky jsou dostupné v PRO verzi</p>
              <button
                type="button"
                onClick={() => window.location.href = '/admin/settings'}
                className="text-sm text-slate-800 underline hover:text-slate-600"
              >
                Aktivovat PRO verzi
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {formData.feedback_questions.map((q, index) => (
                <div key={q.id} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg" data-testid={`feedback-question-${index}`}>
                  <span className="text-xs text-gray-400 mt-2 font-mono w-5 shrink-0">{index + 1}.</span>
                  <div className="flex-1 space-y-2">
                    <Input
                      value={q.question}
                      onChange={(e) => updateQuestion(q.id, 'question', e.target.value)}
                      placeholder="Zadejte otázku..."
                      className="text-sm"
                      data-testid={`feedback-question-input-${index}`}
                    />
                    <select
                      value={q.type}
                      onChange={(e) => updateQuestion(q.id, 'type', e.target.value)}
                      className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white w-full md:w-auto"
                      data-testid={`feedback-question-type-${index}`}
                    >
                      {questionTypes.map(t => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeQuestion(q.id)}
                    className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded shrink-0"
                    data-testid={`feedback-question-remove-${index}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}

              {formData.feedback_questions.length < 5 && (
                <button
                  type="button"
                  onClick={addQuestion}
                  className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-800 px-3 py-2 border border-dashed border-gray-300 rounded-lg hover:border-gray-400 w-full justify-center"
                  data-testid="feedback-add-question-btn"
                >
                  <Plus className="w-4 h-4" />
                  Přidat otázku ({formData.feedback_questions.length}/5)
                </button>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
