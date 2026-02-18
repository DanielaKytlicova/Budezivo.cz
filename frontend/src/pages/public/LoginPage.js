import React, { useState, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { Header, BudezivoLogo } from '../../components/layout/Header';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Checkbox } from '../../components/ui/checkbox';
import { toast } from 'sonner';
import { Mail, Lock } from 'lucide-react';

export const LoginPage = () => {
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(formData.email, formData.password);
      toast.success('Přihlášení úspěšné');
      navigate('/admin');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Chyba při přihlašování');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      {/* Minimal header - na mobilu pouze ikona loga */}
      <Header minimal={true} />
      
      <div className="flex min-h-[calc(100vh-4rem)]">
        {/* Left Column - Form */}
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-md">
            <div className="text-center mb-8">
              <div className="hidden md:block">
                <BubezivoLogo className="justify-center" />
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-3xl font-bold text-[#2B3E50] mb-2">Přihlášení do systému</h2>
              <p className="text-gray-600">Zadejte své přihlašovací údaje</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
              <div>
                <Label htmlFor="email" className="text-[#2B3E50]">E-mailová adresa</Label>
                <div className="relative mt-2">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    data-testid="login-email-input"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="vas.email@muzeum.cz"
                    required
                    className="pl-10 h-12 rounded-lg border-gray-300"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="password" className="text-[#2B3E50]">Heslo</Label>
                <div className="relative mt-2">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <Input
                    id="password"
                    type="password"
                    data-testid="login-password-input"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="••••••••"
                    required
                    className="pl-10 h-12 rounded-lg border-gray-300"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="remember"
                    checked={rememberMe}
                    onCheckedChange={setRememberMe}
                  />
                  <label htmlFor="remember" className="text-sm text-[#2B3E50] cursor-pointer">
                    Zapamatovat si mě
                  </label>
                </div>
                <Link
                  to="/forgot-password"
                  data-testid="forgot-password-link"
                  className="text-sm text-[#4A6FA5] hover:underline"
                >
                  Zapomenuté heslo?
                </Link>
              </div>

              <Button
                type="submit"
                data-testid="login-submit-button"
                className="w-full bg-[#C4AB86] hover:bg-[#b39975] text-white h-12 rounded-lg"
                disabled={loading}
              >
                {loading ? 'Přihlašování...' : 'Přihlásit se'}
              </Button>
            </form>

            <div className="mt-8 text-center border-t border-gray-200 pt-6">
              <p className="text-sm text-gray-600 mb-4">Ještě nemáte účet?</p>
              <Link to="/register" data-testid="register-link-from-login">
                <Button variant="outline" className="w-full border-2 border-[#4A6FA5] text-[#4A6FA5] hover:bg-[#4A6FA5]/5 h-12 rounded-lg">
                  Registrovat instituci
                </Button>
              </Link>
            </div>

            <p className="mt-6 text-xs text-center text-gray-500">
              Přihlášením souhlasíte s našimi <Link to="/gdpr" className="underline">zásadami ochrany soukromí</Link>
            </p>
          </div>
        </div>

        {/* Right Column - Illustration/Stats */}
        <div className="hidden lg:flex flex-1 bg-white items-center justify-center p-12">
          <div className="max-w-md">
            <div className="mb-12">
              <div className="bg-gray-100 rounded-2xl p-8 shadow-sm">
                <div className="space-y-4">
                  <div className="h-4 bg-[#4A6FA5] rounded w-3/4"></div>
                  <div className="h-4 bg-gray-300 rounded w-1/2"></div>
                  <div className="grid grid-cols-7 gap-2 mt-6">
                    {[...Array(35)].map((_, i) => (
                      <div
                        key={i}
                        className={`aspect-square rounded ${
                          [10, 11, 17, 18].includes(i) ? 'bg-[#84A98C]' : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="text-center">
              <h3 className="text-2xl font-bold text-[#2B3E50] mb-4">Vítejte zpět</h3>
              <p className="text-gray-600 mb-8">
                Spravujte své rezervace přehledně a efektivně. Ušetřete čas pro to, na čem skutečně záleží.
              </p>

              <div className="grid grid-cols-3 gap-6">
                <div>
                  <div className="text-3xl font-bold text-[#4A6FA5]">500+</div>
                  <div className="text-sm text-gray-600">Institucí</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-[#4A6FA5]">10k+</div>
                  <div className="text-sm text-gray-600">Rezervací</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-[#4A6FA5]">95%</div>
                  <div className="text-sm text-gray-600">Spokojenost</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
