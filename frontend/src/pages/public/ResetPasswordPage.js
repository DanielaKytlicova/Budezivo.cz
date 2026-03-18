import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Header } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card } from '../../components/ui/card';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';
import { Eye, EyeOff, CheckCircle, XCircle } from 'lucide-react';

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: '',
  });

  const token = searchParams.get('token');
  const email = searchParams.get('email');

  useEffect(() => {
    if (!token || !email) {
      setError('Neplatný odkaz pro obnovu hesla. Chybí token nebo e-mail.');
    }
  }, [token, email]);

  const validatePassword = (password) => {
    const minLength = password.length >= 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    return { minLength, hasUpper, hasLower, hasNumber, isValid: minLength && hasUpper && hasLower && hasNumber };
  };

  const passwordValidation = validatePassword(formData.password);
  const passwordsMatch = formData.password === formData.confirmPassword && formData.confirmPassword !== '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!passwordValidation.isValid) {
      toast.error('Heslo nesplňuje požadavky');
      return;
    }
    
    if (!passwordsMatch) {
      toast.error('Hesla se neshodují');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await axios.post(`${API}/auth/reset-password`, {
        token,
        email,
        new_password: formData.password,
      });
      setSuccess(true);
      toast.success('Heslo bylo úspěšně změněno');
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Nepodařilo se změnit heslo. Odkaz může být neplatný nebo vypršel.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const PasswordRequirement = ({ met, text }) => (
    <div className={`flex items-center gap-2 text-sm ${met ? 'text-green-600' : 'text-gray-500'}`}>
      {met ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
      {text}
    </div>
  );

  if (success) {
    return (
      <div className="min-h-screen bg-[#FDFCF8]">
        <Header />
        <div className="max-w-md mx-auto px-4 py-16">
          <Card className="p-8">
            <div className="text-center py-8">
              <div className="mb-4 text-green-500">
                <CheckCircle className="w-16 h-16 mx-auto" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mb-2">Heslo změněno</h1>
              <p className="text-gray-600 mb-6">
                Vaše heslo bylo úspěšně změněno. Nyní se můžete přihlásit s novým heslem.
              </p>
              <Link to="/login">
                <Button className="bg-slate-800 hover:bg-slate-700" data-testid="go-to-login">
                  Přejít na přihlášení
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (error && (!token || !email)) {
    return (
      <div className="min-h-screen bg-[#FDFCF8]">
        <Header />
        <div className="max-w-md mx-auto px-4 py-16">
          <Card className="p-8">
            <div className="text-center py-8">
              <div className="mb-4 text-red-500">
                <XCircle className="w-16 h-16 mx-auto" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mb-2">Neplatný odkaz</h1>
              <p className="text-gray-600 mb-6">{error}</p>
              <Link to="/forgot-password">
                <Button className="bg-slate-800 hover:bg-slate-700">
                  Požádat o nový odkaz
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      <Header />
      <div className="max-w-md mx-auto px-4 py-16">
        <Card className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Nastavit nové heslo</h1>
            <p className="text-muted-foreground">Zadejte nové heslo pro váš účet</p>
            {email && (
              <p className="text-sm text-gray-500 mt-2">
                Pro: <strong>{email}</strong>
              </p>
            )}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="reset-password-form">
            <div>
              <Label htmlFor="password">Nové heslo</Label>
              <div className="relative mt-2">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  data-testid="new-password-input"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              
              <div className="mt-3 space-y-1">
                <PasswordRequirement met={passwordValidation.minLength} text="Minimálně 8 znaků" />
                <PasswordRequirement met={passwordValidation.hasUpper} text="Alespoň jedno velké písmeno" />
                <PasswordRequirement met={passwordValidation.hasLower} text="Alespoň jedno malé písmeno" />
                <PasswordRequirement met={passwordValidation.hasNumber} text="Alespoň jedna číslice" />
              </div>
            </div>

            <div>
              <Label htmlFor="confirmPassword">Potvrdit heslo</Label>
              <div className="relative mt-2">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  data-testid="confirm-password-input"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  required
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {formData.confirmPassword && (
                <p className={`mt-2 text-sm ${passwordsMatch ? 'text-green-600' : 'text-red-600'}`}>
                  {passwordsMatch ? '✓ Hesla se shodují' : '✗ Hesla se neshodují'}
                </p>
              )}
            </div>

            <Button
              type="submit"
              data-testid="reset-password-submit"
              className="w-full bg-slate-800 hover:bg-slate-700"
              disabled={loading || !passwordValidation.isValid || !passwordsMatch}
            >
              {loading ? 'Ukládám...' : 'Nastavit nové heslo'}
            </Button>

            <div className="text-center">
              <Link to="/login" className="text-sm text-slate-600 hover:text-slate-900">
                Zpět na přihlášení
              </Link>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
