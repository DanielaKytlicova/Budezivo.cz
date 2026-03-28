import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { AuthContext } from '../../context/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import { API } from '../../config/api';
import {
  Calendar,
  BookOpen,
  Clock,
  Link as LinkIcon,
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  Sparkles,
  ArrowRight,
  X
} from 'lucide-react';

const STEPS = [
  {
    id: 'welcome',
    title: 'Vítejte v Bude živo!',
    subtitle: 'Nastavte si systém v pár krocích',
    icon: Sparkles,
  },
  {
    id: 'program',
    title: 'Vytvořte svůj první program',
    subtitle: 'Programy jsou aktivity, které nabízíte školám',
    icon: Calendar,
  },
  {
    id: 'availability',
    title: 'Nastavte dostupnost',
    subtitle: 'Kdy jste k dispozici pro návštěvy?',
    icon: Clock,
  },
  {
    id: 'done',
    title: 'Vše je připraveno!',
    subtitle: 'Můžete začít přijímat rezervace',
    icon: CheckCircle,
  },
];

export const OnboardingWizard = ({ onboardingData, onComplete }) => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [dismissing, setDismissing] = useState(false);

  const step = STEPS[currentStep];
  const hasPrograms = onboardingData?.steps?.has_programs;

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleComplete = async () => {
    setDismissing(true);
    try {
      await axios.post(`${API}/onboarding/complete`);
      toast.success('Onboarding dokončen! Vítejte v systému.');
      onComplete();
    } catch {
      toast.error('Chyba při dokončení onboardingu');
    } finally {
      setDismissing(false);
    }
  };

  const handleSkip = async () => {
    setDismissing(true);
    try {
      await axios.post(`${API}/onboarding/complete`);
      onComplete();
    } catch {
      onComplete();
    }
  };

  const renderStepContent = () => {
    switch (step.id) {
      case 'welcome':
        return <WelcomeStep user={user} onNext={handleNext} />;
      case 'program':
        return (
          <ProgramStep
            hasPrograms={hasPrograms}
            onNext={handleNext}
            onNavigate={() => navigate('/admin/programs')}
          />
        );
      case 'availability':
        return (
          <AvailabilityStep
            onNext={handleNext}
            onNavigate={() => navigate('/admin/availability')}
          />
        );
      case 'done':
        return (
          <DoneStep
            onComplete={handleComplete}
            dismissing={dismissing}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="relative" data-testid="onboarding-wizard">
      {/* Skip button */}
      <button
        onClick={handleSkip}
        className="absolute top-0 right-0 p-2 text-gray-400 hover:text-gray-600 transition-colors"
        data-testid="onboarding-skip"
        title="Přeskočit"
      >
        <X className="w-5 h-5" />
      </button>

      {/* Progress indicator */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                i < currentStep
                  ? 'bg-[#5a7aae] text-white'
                  : i === currentStep
                  ? 'bg-slate-800 text-white ring-4 ring-slate-800/20'
                  : 'bg-gray-100 text-gray-400'
              }`}
              data-testid={`onboarding-step-indicator-${i}`}
            >
              {i < currentStep ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                i + 1
              )}
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`w-12 sm:w-20 h-0.5 mx-1 transition-colors ${
                  i < currentStep ? 'bg-[#5a7aae]' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="min-h-[280px]">
        {renderStepContent()}
      </div>

      {/* Navigation */}
      {step.id !== 'welcome' && step.id !== 'done' && (
        <div className="flex justify-between mt-8 pt-6 border-t">
          <Button
            variant="ghost"
            onClick={handlePrev}
            data-testid="onboarding-prev"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Zpět
          </Button>
          <Button
            onClick={handleNext}
            className="bg-slate-800 text-white hover:bg-slate-700"
            data-testid="onboarding-next"
          >
            Pokračovat
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
};

// ============ Step Components ============

const WelcomeStep = ({ user, onNext }) => (
  <div className="text-center space-y-6" data-testid="onboarding-step-welcome">
    <div className="w-16 h-16 bg-[#5a7aae]/10 rounded-2xl flex items-center justify-center mx-auto">
      <Sparkles className="w-8 h-8 text-[#5a7aae]" />
    </div>
    <div>
      <h2 className="text-2xl font-bold text-slate-900">
        Vítejte, {user?.name || user?.email?.split('@')[0]}!
      </h2>
      <p className="text-gray-500 mt-2 max-w-md mx-auto">
        Za pár minut budete mít vše připraveno pro přijímání online rezervací
        od škol a veřejnosti.
      </p>
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl mx-auto text-left">
      {[
        { icon: Calendar, label: 'Vytvořte program', desc: 'Co nabízíte' },
        { icon: Clock, label: 'Nastavte časy', desc: 'Kdy jste k dispozici' },
        { icon: LinkIcon, label: 'Sdílejte URL', desc: 'Začněte přijímat' },
      ].map((item, i) => (
        <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
          <item.icon className="w-5 h-5 text-[#5a7aae] mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-slate-800">{item.label}</p>
            <p className="text-xs text-gray-400">{item.desc}</p>
          </div>
        </div>
      ))}
    </div>
    <Button
      onClick={onNext}
      className="bg-slate-800 text-white hover:bg-slate-700 px-8"
      data-testid="onboarding-start"
    >
      Začít nastavení
      <ArrowRight className="w-4 h-4 ml-2" />
    </Button>
  </div>
);

const ProgramStep = ({ hasPrograms, onNext, onNavigate }) => (
  <div className="space-y-6" data-testid="onboarding-step-program">
    <div className="flex items-start gap-4">
      <div className="w-12 h-12 bg-[#5a7aae]/10 rounded-xl flex items-center justify-center shrink-0">
        <Calendar className="w-6 h-6 text-[#5a7aae]" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-slate-900">Vytvořte svůj první program</h2>
        <p className="text-gray-500 mt-1">
          Program je aktivita, kterou nabízíte návštěvníkům. Například "Prohlídka galerie",
          "Workshop pro děti" nebo "Historická přednáška".
        </p>
      </div>
    </div>

    {hasPrograms ? (
      <Card className="p-4 bg-green-50 border-green-200">
        <div className="flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <div>
            <p className="font-medium text-green-800">Máte vytvořené programy</p>
            <p className="text-sm text-green-600">Tento krok můžete přeskočit.</p>
          </div>
        </div>
      </Card>
    ) : (
      <Card className="p-5 border-dashed border-2 border-gray-200 hover:border-[#5a7aae] transition-colors cursor-pointer"
        onClick={onNavigate}
        data-testid="onboarding-create-program"
      >
        <div className="text-center space-y-2">
          <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
            <BookOpen className="w-5 h-5 text-gray-400" />
          </div>
          <p className="font-medium text-slate-800">Přejít na tvorbu programu</p>
          <p className="text-sm text-gray-400">Otevře se stránka Programy</p>
        </div>
      </Card>
    )}

    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-sm font-medium text-slate-700 mb-2">Tip: Co zadat do programu?</p>
      <ul className="text-sm text-gray-500 space-y-1">
        <li>- Název a krátký popis</li>
        <li>- Cílová věková skupina (MŠ, ZŠ, SŠ...)</li>
        <li>- Délka trvání a kapacita</li>
        <li>- Dostupné dny a časové bloky</li>
      </ul>
    </div>
  </div>
);

const AvailabilityStep = ({ onNext, onNavigate }) => (
  <div className="space-y-6" data-testid="onboarding-step-availability">
    <div className="flex items-start gap-4">
      <div className="w-12 h-12 bg-[#c5ac87]/20 rounded-xl flex items-center justify-center shrink-0">
        <Clock className="w-6 h-6 text-[#c5ac87]" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-slate-900">Nastavte dostupnost lektorů</h2>
        <p className="text-gray-500 mt-1">
          Definujte, kdy jsou vaši lektoři k dispozici. Můžete nastavit pravidelnou
          dostupnost i jednorázové bloky.
        </p>
      </div>
    </div>

    <Card className="p-5 border-dashed border-2 border-gray-200 hover:border-[#c5ac87] transition-colors cursor-pointer"
      onClick={onNavigate}
      data-testid="onboarding-set-availability"
    >
      <div className="text-center space-y-2">
        <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
          <Clock className="w-5 h-5 text-gray-400" />
        </div>
        <p className="font-medium text-slate-800">Přejít na nastavení dostupnosti</p>
        <p className="text-sm text-gray-400">Otevře se stránka Dostupnost lektorů</p>
      </div>
    </Card>

    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-sm font-medium text-slate-700 mb-2">Tip: Dostupnost pomáhá s plánováním</p>
      <ul className="text-sm text-gray-500 space-y-1">
        <li>- Nastavte pravidelné dny (Po-Pá)</li>
        <li>- Přidejte jednorázové bloky pro speciální akce</li>
        <li>- Systém automaticky kontroluje kolize</li>
      </ul>
    </div>
  </div>
);

const DoneStep = ({ onComplete, dismissing }) => (
  <div className="text-center space-y-6" data-testid="onboarding-step-done">
    <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto">
      <CheckCircle className="w-8 h-8 text-green-600" />
    </div>
    <div>
      <h2 className="text-2xl font-bold text-slate-900">Vše je připraveno!</h2>
      <p className="text-gray-500 mt-2 max-w-md mx-auto">
        Vaše instituce je nastavena a připravena přijímat online rezervace.
        Sdílejte odkaz na rezervační stránku se školami a veřejností.
      </p>
    </div>

    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto">
      <Card className="p-4 text-left">
        <Calendar className="w-5 h-5 text-[#5a7aae] mb-2" />
        <p className="text-sm font-medium text-slate-800">Správa programů</p>
        <p className="text-xs text-gray-400">Přidejte další programy a aktivity</p>
      </Card>
      <Card className="p-4 text-left">
        <BookOpen className="w-5 h-5 text-[#c5ac87] mb-2" />
        <p className="text-sm font-medium text-slate-800">Rezervace</p>
        <p className="text-xs text-gray-400">Spravujte příchozí rezervace</p>
      </Card>
    </div>

    <Button
      onClick={onComplete}
      disabled={dismissing}
      className="bg-slate-800 text-white hover:bg-slate-700 px-8"
      data-testid="onboarding-finish"
    >
      {dismissing ? 'Dokončuji...' : 'Přejít na dashboard'}
      <ArrowRight className="w-4 h-4 ml-2" />
    </Button>
  </div>
);
