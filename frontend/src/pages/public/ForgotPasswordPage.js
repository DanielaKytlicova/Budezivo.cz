import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { Header } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card } from '../../components/ui/card';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ForgotPasswordPage = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.post(`${API}/auth/forgot-password`, { email });
      setSent(true);
      toast.success(t('common.success'));
    } catch (error) {
      toast.error(t('common.error'));
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
            <h1 className="text-3xl font-bold text-slate-900 mb-2">{t('auth.forgotPassword.title')}</h1>
            <p className="text-muted-foreground">{t('auth.forgotPassword.subtitle')}</p>
          </div>

          {sent ? (
            <div className="text-center py-8">
              <div className="mb-4 text-[#84A98C]">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-slate-700 mb-6">{t('auth.forgotPassword.subtitle')}</p>
              <Link to="/login" data-testid="back-to-login-link">
                <Button className="bg-slate-800 hover:bg-slate-700">
                  {t('auth.forgotPassword.backToLogin')}
                </Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6" data-testid="forgot-password-form">
              <div>
                <Label htmlFor="email">{t('auth.forgotPassword.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  data-testid="forgot-password-email-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="mt-2"
                />
              </div>

              <Button
                type="submit"
                data-testid="forgot-password-submit-button"
                className="w-full bg-slate-800 hover:bg-slate-700"
                disabled={loading}
              >
                {loading ? t('common.loading') : t('auth.forgotPassword.submit')}
              </Button>

              <div className="text-center">
                <Link to="/login" data-testid="back-to-login-link-bottom" className="text-sm text-slate-600 hover:text-slate-900">
                  {t('auth.forgotPassword.backToLogin')}
                </Link>
              </div>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
};
