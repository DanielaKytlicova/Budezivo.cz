export const HELP_MANUAL_URL = '/manuals/budezivo-odkazy-a-comgate.pdf';

export const HELP_GUIDES = {
  'web-links': {
    id: 'web-links',
    title: 'Jak vložit rezervaci na web',
    description: 'Vytvoření URL nebo HTML odkazu a jeho bezpečné zveřejnění na webu instituce.',
    audience: 'Správce webu nebo pracovník instituce',
    duration: 'Přibližně 5 minut',
    pdfPage: 3,
    steps: [
      'V Programy nebo Akce otevřete „Generovat URL pro web“.',
      'Vyberte všechny položky, konkrétní program nebo konkrétní akci.',
      'Zkopírujte URL pro tlačítko v editoru webu, případně připravený HTML kód.',
      'Odkaz po zveřejnění vyzkoušejte v anonymním okně a také na mobilu.',
    ],
  },
  comgate: {
    id: 'comgate',
    title: 'Jak založit a propojit Comgate',
    description:
      'Postup registrace, ověření veřejné instituce, vložení údajů a bezpečné otestování plateb.',
    audience: 'Vedení, ekonomické oddělení a správce systému',
    duration: 'Registrace podle schválení Comgate',
    pdfPage: 6,
    optional: true,
    steps: [
      'Připravte údaje instituce, bankovní účet a podpisové oprávnění.',
      'Zaregistrujte instituci u Comgate podle její skutečné právní formy.',
      'Po schválení získejte Merchant ID a Secret pro konkrétní obchod.',
      'V Budeživo zvolte Comgate a údaje vložte pouze do platebního nastavení.',
      'Zkopírujte návratové URL do portálu Comgate a nejprve proveďte test integrace.',
      'Produkční režim zapněte až po smluvním, účetním a technickém ověření.',
    ],
  },
};

export const getHelpGuidePdfUrl = (guide) => `${HELP_MANUAL_URL}#page=${guide.pdfPage}`;
