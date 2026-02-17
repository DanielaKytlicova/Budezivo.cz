import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AuthContext } from '../../context/AuthContext';
import { Header } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card } from '../../components/ui/card';
import { toast } from 'sonner';

export const LoginPage = () => {
  const { t } = useTranslation();
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(formData.email, formData.password);
      toast.success(t('common.success'));
      navigate('/admin');
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFCF8]">
      <Header />
      <div className="max-w-md mx-auto px-4 py-16">
        <Card className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">{t('auth.login.title')}</h1>
            <p className="text-muted-foreground">{t('auth.login.subtitle')}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
            <div>
              <Label htmlFor="email">{t('auth.login.email')}</Label>
              <Input
                id="email"
                type="email"
                data-testid="login-email-input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="password">{t('auth.login.password')}</Label>
              <Input
                id="password"
                type="password"
                data-testid="login-password-input"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="mt-2"
              />
            </div>

            <div className="text-right">
              <Link
                to="/forgot-password"
                data-testid="forgot-password-link"
                className="text-sm text-slate-600 hover:text-slate-900"
              >
                {t('auth.login.forgotPassword')}
              </Link>
            </div>

            <Button
              type="submit"
              data-testid="login-submit-button"
              className="w-full bg-slate-800 hover:bg-slate-700"
              disabled={loading}
            >
              {loading ? t('common.loading') : t('auth.login.submit')}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-muted-foreground">{t('auth.login.noAccount')} </span>
            <Link to="/register" data-testid="register-link-from-login" className="text-slate-900 font-medium hover:underline">
              {t('auth.login.register')}
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};
