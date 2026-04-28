import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Header } from '../../components/layout/Header';
import { Card } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Button } from '../../components/ui/button';
import { Loader2, GraduationCap } from 'lucide-react';
import { useTeacherAuth } from '../../context/TeacherAuthContext';
import { toast } from 'sonner';

export const TeacherLoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useTeacherAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');

  const redirectTo = location.state?.from || '/ucitel/ucet';

  const onSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErr('');
    const r = await login(email.trim().toLowerCase(), password);
    setSubmitting(false);
    if (r.ok) {
      toast.success('Vítáme zpět!');
      navigate(redirectTo);
    } else {
      setErr(r.error);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Header />
      <div className="max-w-md mx-auto px-4 py-12">
        <Card className="p-6 md:p-8" data-testid="teacher-login-page">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-[#4A6FA5] flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#2B3E50]">Přihlášení pro učitele</h1>
              <p className="text-sm text-gray-500">Pro rychlejší rezervace a uložené oblíbené programy</p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <Label htmlFor="t-email">E-mail</Label>
              <Input
                id="t-email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                data-testid="teacher-login-email"
              />
            </div>
            <div>
              <Label htmlFor="t-password">Heslo</Label>
              <Input
                id="t-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                data-testid="teacher-login-password"
              />
            </div>
            {err && (
              <p className="text-sm text-red-600" data-testid="teacher-login-error">{err}</p>
            )}
            <Button
              type="submit"
              disabled={submitting}
              className="w-full bg-[#4A6FA5] hover:bg-[#3a5f95] h-11"
              data-testid="teacher-login-submit"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Přihlásit se
            </Button>
          </form>

          <div className="mt-6 text-sm text-center text-gray-600 space-y-1">
            <p>
              Ještě nemáte účet?{' '}
              <Link to="/ucitel/registrace" className="text-[#4A6FA5] hover:underline" data-testid="teacher-register-link">
                Zaregistrujte se
              </Link>
            </p>
            <p className="text-xs text-gray-400 mt-3">
              Rezervovat lze i bez účtu — registrace je dobrovolná a slouží pro vaše pohodlí.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default TeacherLoginPage;
