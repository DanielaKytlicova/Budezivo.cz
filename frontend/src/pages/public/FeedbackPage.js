/**
 * FeedbackPage - Veřejná stránka pro vyplnění zpětné vazby
 * Přístupná přes unikátní token v URL
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Star, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Star Rating Component
const StarRating = ({ value, onChange, size = 'lg' }) => {
  const [hover, setHover] = useState(0);
  const starSize = size === 'lg' ? 'w-10 h-10' : 'w-6 h-6';
  
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHover(star)}
          onMouseLeave={() => setHover(0)}
          className="focus:outline-none transition-transform hover:scale-110"
          data-testid={`star-rating-${star}`}
        >
          <Star
            className={`${starSize} ${
              star <= (hover || value)
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-gray-300'
            }`}
          />
        </button>
      ))}
    </div>
  );
};

// Yes/No Button Component
const YesNoButtons = ({ value, onChange }) => (
  <div className="flex gap-3">
    <button
      type="button"
      onClick={() => onChange(true)}
      className={`px-6 py-3 rounded-lg font-medium transition-all ${
        value === true
          ? 'bg-green-500 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
      data-testid="yesno-yes"
    >
      Ano
    </button>
    <button
      type="button"
      onClick={() => onChange(false)}
      className={`px-6 py-3 rounded-lg font-medium transition-all ${
        value === false
          ? 'bg-red-500 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
      data-testid="yesno-no"
    >
      Ne
    </button>
  </div>
);

export default function FeedbackPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  const [formData, setFormData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [overallRating, setOverallRating] = useState(0);
  const [wouldRecommend, setWouldRecommend] = useState(null);
  const [additionalComments, setAdditionalComments] = useState('');
  
  useEffect(() => {
    const fetchFormData = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/feedback/public/${token}`);
        setFormData(response.data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching feedback form:', err);
        setError(err.response?.data?.detail || 'Formulář nebyl nalezen nebo již není platný.');
        setLoading(false);
      }
    };
    
    if (token) {
      fetchFormData();
    }
  }, [token]);
  
  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    
    try {
      await axios.post(`${API_URL}/api/feedback/public/${token}`, {
        answers,
        overall_rating: overallRating || null,
        would_recommend: wouldRecommend,
        additional_comments: additionalComments || null
      });
      
      setSuccess(true);
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError(err.response?.data?.detail || 'Nepodařilo se odeslat zpětnou vazbu.');
    } finally {
      setSubmitting(false);
    }
  };
  
  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#5a7aae]" />
      </div>
    );
  }
  
  // Error State
  if (error && !formData) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Chyba</h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }
  
  // Success State
  if (success) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h1 className="text-2xl font-semibold text-gray-900 mb-2">Dekujeme!</h1>
          <p className="text-gray-600 mb-6">
            Vaše zpětná vazba byla úspěšně odeslána. Děkujeme, že jste si našli čas.
          </p>
          <Button
            onClick={() => navigate('/')}
            className="bg-[#5a7aae] hover:bg-[#4a6a9e]"
          >
            Zpět na hlavní stránku
          </Button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-[#F8F9FA] py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-t-xl shadow-lg p-6 border-b">
          <div className="text-center">
            {formData.institution_logo && (
              <img
                src={formData.institution_logo}
                alt={formData.institution_name}
                className="h-12 mx-auto mb-4"
              />
            )}
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Zpětná vazba
            </h1>
            <p className="text-gray-600">
              {formData.institution_name}
            </p>
          </div>
          
          {/* Reservation Info */}
          <div className="mt-6 bg-gray-50 rounded-lg p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Program:</span>
                <p className="font-medium text-gray-900">{formData.program_name}</p>
              </div>
              <div>
                <span className="text-gray-500">Datum:</span>
                <p className="font-medium text-gray-900">{formData.reservation_date}</p>
              </div>
              <div className="col-span-2">
                <span className="text-gray-500">Škola:</span>
                <p className="font-medium text-gray-900">{formData.school_name}</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-b-xl shadow-lg p-6">
          {/* Overall Rating */}
          <div className="mb-8">
            <Label className="text-base font-medium text-gray-900 mb-3 block">
              Jak hodnotíte program celkově? *
            </Label>
            <div className="flex items-center gap-4">
              <StarRating value={overallRating} onChange={setOverallRating} />
              {overallRating > 0 && (
                <span className="text-lg font-medium text-gray-700">
                  {overallRating}/5
                </span>
              )}
            </div>
          </div>
          
          {/* Would Recommend */}
          <div className="mb-8">
            <Label className="text-base font-medium text-gray-900 mb-3 block">
              Doporučili byste program dalším školám? *
            </Label>
            <YesNoButtons value={wouldRecommend} onChange={setWouldRecommend} />
          </div>
          
          {/* Dynamic Questions */}
          {formData.questions && formData.questions.map((question) => (
            <div key={question.id} className="mb-8">
              <Label className="text-base font-medium text-gray-900 mb-3 block">
                {question.question_text}
                {question.is_required && ' *'}
              </Label>
              
              {(question.question_type === 'rating' || question.question_type === 'scale') && (
                <StarRating
                  value={answers[question.id] || 0}
                  onChange={(val) => handleAnswerChange(question.id, val)}
                  size="md"
                />
              )}
              
              {question.question_type === 'yesno' && (
                <YesNoButtons
                  value={answers[question.id]}
                  onChange={(val) => handleAnswerChange(question.id, val)}
                />
              )}
              
              {question.question_type === 'text' && (
                <Textarea
                  value={answers[question.id] || ''}
                  onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                  placeholder="Vaše odpověď..."
                  rows={3}
                />
              )}
            </div>
          ))}
          
          {/* Additional Comments */}
          <div className="mb-8">
            <Label className="text-base font-medium text-gray-900 mb-3 block">
              Další komentáře nebo návrhy na zlepšení
            </Label>
            <Textarea
              value={additionalComments}
              onChange={(e) => setAdditionalComments(e.target.value)}
              placeholder="Zde můžete napsat cokoliv dalšího..."
              rows={4}
              data-testid="additional-comments"
            />
          </div>
          
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}
          
          {/* Submit Button */}
          <Button
            type="submit"
            disabled={submitting || overallRating === 0 || wouldRecommend === null}
            className="w-full bg-[#5a7aae] hover:bg-[#4a6a9e] h-12 text-base"
            data-testid="submit-feedback"
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Odesílám...
              </>
            ) : (
              'Odeslat zpětnou vazbu'
            )}
          </Button>
          
          <p className="text-center text-sm text-gray-500 mt-4">
            Vaše odpovědi jsou anonymní a pomohou nám zlepšit naše programy.
          </p>
        </form>
      </div>
    </div>
  );
}
