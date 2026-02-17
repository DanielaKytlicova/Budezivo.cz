import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { AuthContext } from '../../context/AuthContext';
import { Header } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';

export const RegisterPage = () => {
  const { t } = useTranslation();
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    institution_name: '',
    institution_type: 'museum',
    country: 'Czech Republic',
    email: '',
    password: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await register(formData);
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
            <h1 className="text-3xl font-bold text-slate-900 mb-2">{t('auth.register.title')}</h1>
            <p className="text-muted-foreground">{t('auth.register.subtitle')}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="register-form">
            <div>
              <Label htmlFor="institution_name">{t('auth.register.institutionName')}</Label>
              <Input
                id="institution_name"
                data-testid="register-institution-name-input"
                value={formData.institution_name}
                onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                required
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="institution_type">{t('auth.register.institutionType')}</Label>
              <Select
                value={formData.institution_type}
                onValueChange={(value) => setFormData({ ...formData, institution_type: value })}
              >
                <SelectTrigger className="mt-2" data-testid="register-institution-type-select">
                  <SelectValue placeholder={t('auth.register.institutionType')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="museum">{t('auth.register.types.museum')}</SelectItem>
                  <SelectItem value="gallery">{t('auth.register.types.gallery')}</SelectItem>
                  <SelectItem value="library">{t('auth.register.types.library')}</SelectItem>
                  <SelectItem value="botanical_garden">{t('auth.register.types.botanical_garden')}</SelectItem>
                  <SelectItem value="other">{t('auth.register.types.other')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="email">{t('auth.register.email')}</Label>
              <Input
                id="email"
                type="email"
                data-testid="register-email-input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="password">{t('auth.register.password')}</Label>
              <Input
                id="password"
                type="password"
                data-testid="register-password-input"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="mt-2"
              />
            </div>

            <Button
              type="submit"
              data-testid="register-submit-button"
              className="w-full bg-[#E9C46A] text-slate-900 hover:bg-[#E9C46A]/90"
              disabled={loading}
            >
              {loading ? t('common.loading') : t('auth.register.submit')}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-muted-foreground">{t('auth.register.hasAccount')} </span>
            <Link to="/login" data-testid="login-link-from-register" className="text-slate-900 font-medium hover:underline">
              {t('auth.register.login')}
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};
