import React, { useState, useEffect } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { RichTextEditor } from '../../components/ui/rich-text-editor';
import { 
  Mail, 
  Eye, 
  Send, 
  Save, 
  Copy, 
  CheckCircle2, 
  AlertCircle,
  Info,
  Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Available template variables
const TEMPLATE_VARIABLES = [
  { key: 'school_name', label: 'Název školy/skupiny', example: 'Základní škola Příkladová' },
  { key: 'contact_person', label: 'Jméno kontaktní osoby', example: 'Jan Novák' },
  { key: 'email', label: 'E-mail', example: 'jan.novak@skola.cz' },
  { key: 'phone', label: 'Telefon', example: '+420 123 456 789' },
  { key: 'reservation_date', label: 'Datum rezervace', example: '15.03.2025' },
  { key: 'reservation_time', label: 'Čas rezervace', example: '09:00' },
  { key: 'number_of_students', label: 'Počet žáků', example: '25' },
  { key: 'number_of_teachers', label: 'Počet pedagogů', example: '2' },
  { key: 'program_name', label: 'Název programu', example: 'Seznam se s galerií' },
  { key: 'program_duration', label: 'Délka programu (min)', example: '90' },
  { key: 'institution_name', label: 'Název instituce', example: 'Galerie moderního umění' },
  { key: 'special_requirements', label: 'Speciální požadavky', example: 'Bezbariérový přístup' },
];

export const ProgramMailingTab = ({ programId, programName }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [emailConfigured, setEmailConfigured] = useState(false);
  
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [preview, setPreview] = useState({ subject: '', body: '' });
  const [testEmail, setTestEmail] = useState('');
  
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (programId) {
      fetchTemplate();
    }
  }, [programId]);

  const fetchTemplate = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/programs/${programId}/email-template`);
      
      if (response.data.template) {
        setSubject(response.data.template.subject || '');
        setBody(response.data.template.body || '');
      } else {
        // Set default template
        setSubject('Potvrzení rezervace - {{program_name}}');
        setBody(getDefaultTemplate());
      }
      
      setEmailConfigured(response.data.email_service_configured);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to fetch template:', error);
      // Set defaults on error
      setSubject('Potvrzení rezervace - {{program_name}}');
      setBody(getDefaultTemplate());
    } finally {
      setLoading(false);
    }
  };

  const getDefaultTemplate = () => {
    return `<h2>Potvrzení rezervace</h2>

<p>Dobrý den, <strong>{{contact_person}}</strong>,</p>

<p>děkujeme za Vaši rezervaci programu <strong>{{program_name}}</strong> v instituci <strong>{{institution_name}}</strong>.</p>

<h3>Detail rezervace</h3>
<ul>
  <li><strong>Datum:</strong> {{reservation_date}}</li>
  <li><strong>Čas:</strong> {{reservation_time}}</li>
  <li><strong>Škola/Skupina:</strong> {{school_name}}</li>
  <li><strong>Počet žáků:</strong> {{number_of_students}}</li>
  <li><strong>Počet pedagogů:</strong> {{number_of_teachers}}</li>
</ul>

<p>V případě dotazů nás neváhejte kontaktovat.</p>

<p>S pozdravem,<br/>
<strong>{{institution_name}}</strong></p>`;
  };

  const handleSubjectChange = (value) => {
    setSubject(value);
    setHasChanges(true);
  };

  const handleBodyChange = (value) => {
    setBody(value);
    setHasChanges(true);
  };

  const insertVariable = (variable) => {
    const tag = `{{${variable}}}`;
    navigator.clipboard.writeText(tag);
    toast.success(`Proměnná ${tag} zkopírována do schránky`);
  };

  const handleSave = async () => {
    if (!subject.trim() || !body.trim()) {
      toast.error('Vyplňte předmět a tělo e-mailu');
      return;
    }

    try {
      setSaving(true);
      await axios.put(`${API}/programs/${programId}/email-template`, {
        subject,
        body
      });
      toast.success('Šablona byla uložena');
      setHasChanges(false);
    } catch (error) {
      const message = error.response?.data?.detail || 'Nepodařilo se uložit šablonu';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    try {
      const response = await axios.post(`${API}/programs/${programId}/email-template/preview`, {
        subject,
        body
      });
      setPreview(response.data.preview);
      setShowPreview(true);
    } catch (error) {
      toast.error('Nepodařilo se načíst náhled');
    }
  };

  const handleSendTest = async () => {
    if (!testEmail) {
      toast.error('Zadejte e-mailovou adresu');
      return;
    }

    if (!emailConfigured) {
      toast.error('E-mailová služba není nakonfigurována');
      return;
    }

    try {
      setSending(true);
      await axios.post(`${API}/programs/${programId}/email-template/test`, {
        recipient_email: testEmail,
        subject,
        body
      });
      toast.success(`Testovací e-mail odeslán na ${testEmail}`);
    } catch (error) {
      const message = error.response?.data?.detail || 'Nepodařilo se odeslat testovací e-mail';
      toast.error(message);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-slate-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Email Service Status */}
      <Card className={`p-4 ${emailConfigured ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
        <div className="flex items-start gap-3">
          {emailConfigured ? (
            <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
          )}
          <div>
            <p className={`font-medium ${emailConfigured ? 'text-green-800' : 'text-amber-800'}`}>
              {emailConfigured ? 'E-mailová služba je aktivní' : 'E-mailová služba není nakonfigurována'}
            </p>
            <p className={`text-sm ${emailConfigured ? 'text-green-700' : 'text-amber-700'}`}>
              {emailConfigured 
                ? 'E-maily budou automaticky odesílány po vytvoření rezervace.'
                : 'Kontaktujte správce pro nastavení SMTP služby (Resend).'}
            </p>
          </div>
        </div>
      </Card>

      {/* Subject Field */}
      <Card className="p-4 md:p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-slate-600" />
          <h3 className="font-semibold text-slate-900">Předmět e-mailu</h3>
        </div>
        <Input
          value={subject}
          onChange={(e) => handleSubjectChange(e.target.value)}
          placeholder="Potvrzení rezervace - {{program_name}}"
          className="font-mono text-sm"
          data-testid="email-subject-input"
        />
        <p className="text-xs text-gray-500">
          Můžete použít proměnné jako <code className="bg-gray-100 px-1 rounded">{'{{program_name}}'}</code>
        </p>
      </Card>

      {/* Body Editor */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Obsah e-mailu</h3>
        <RichTextEditor
          content={body}
          onChange={handleBodyChange}
          placeholder="Napište obsah e-mailu..."
          data-testid="email-body-editor"
        />
      </Card>

      {/* Variables Helper */}
      <Card className="p-4 md:p-6 space-y-4 bg-blue-50 border-blue-100">
        <div className="flex items-center gap-2">
          <Info className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-slate-900">Dostupné proměnné</h3>
        </div>
        <p className="text-sm text-gray-600">
          Kliknutím zkopírujete proměnnou do schránky. Vložte ji do textu pomocí Ctrl+V.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {TEMPLATE_VARIABLES.map((variable) => (
            <button
              key={variable.key}
              type="button"
              onClick={() => insertVariable(variable.key)}
              className="flex items-center justify-between p-2 bg-white border rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors text-left group"
              title={`Příklad: ${variable.example}`}
              data-testid={`variable-${variable.key}`}
            >
              <div className="min-w-0">
                <p className="text-xs font-mono text-blue-600 truncate">{`{{${variable.key}}}`}</p>
                <p className="text-xs text-gray-500 truncate">{variable.label}</p>
              </div>
              <Copy className="w-4 h-4 text-gray-400 group-hover:text-blue-500 shrink-0 ml-2" />
            </button>
          ))}
        </div>
      </Card>

      {/* Preview Section */}
      {showPreview && (
        <Card className="p-4 md:p-6 space-y-4 border-2 border-slate-300">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">Náhled e-mailu</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowPreview(false)}
            >
              Zavřít
            </Button>
          </div>
          <div className="space-y-3">
            <div>
              <Label className="text-xs text-gray-500">Předmět:</Label>
              <p className="font-medium">{preview.subject}</p>
            </div>
            <div>
              <Label className="text-xs text-gray-500">Obsah:</Label>
              <div 
                className="prose prose-sm max-w-none p-4 bg-gray-50 rounded-lg border"
                dangerouslySetInnerHTML={{ __html: preview.body }}
              />
            </div>
          </div>
        </Card>
      )}

      {/* Test Email Section */}
      <Card className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Testovací odeslání</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <Input
            type="email"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            placeholder="vas@email.cz"
            className="flex-1"
            data-testid="test-email-input"
          />
          <Button
            variant="outline"
            onClick={handleSendTest}
            disabled={sending || !emailConfigured}
            data-testid="send-test-btn"
          >
            {sending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Send className="w-4 h-4 mr-2" />
            )}
            Odeslat test
          </Button>
        </div>
        {!emailConfigured && (
          <p className="text-xs text-amber-600">
            Testovací e-mail nelze odeslat - služba není nakonfigurována
          </p>
        )}
      </Card>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
        <Button
          variant="outline"
          onClick={handlePreview}
          className="flex-1"
          data-testid="preview-email-btn"
        >
          <Eye className="w-4 h-4 mr-2" />
          Náhled
        </Button>
        <Button
          onClick={handleSave}
          disabled={saving || !hasChanges}
          className="flex-1 bg-slate-800 text-white hover:bg-slate-700"
          data-testid="save-template-btn"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          {hasChanges ? 'Uložit změny' : 'Uloženo'}
        </Button>
      </div>
    </div>
  );
};

export default ProgramMailingTab;
