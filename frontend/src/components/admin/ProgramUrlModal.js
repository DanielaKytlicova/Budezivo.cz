import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Link as LinkIcon, ExternalLink, Copy, SlidersHorizontal } from 'lucide-react';
import { toast } from 'sonner';

const URL_AGE_OPTIONS = [
  { code: 'MS', label: 'MŠ (3-6 let)' },
  { code: 'ZS1', label: 'I. stupeň ZŠ (7-12 let)' },
  { code: 'ZS2', label: 'II. stupeň ZŠ (12-15 let)' },
  { code: 'SS', label: 'SŠ (14-18 let)' },
  { code: 'GYM', label: 'Gymnázium (14-18 let)' },
];

export const ProgramUrlModal = ({ open, onOpenChange, programs, institutionData }) => {
  const [selectedProgramForUrl, setSelectedProgramForUrl] = useState('all');
  const [urlAgeFilters, setUrlAgeFilters] = useState([]);
  const [urlData, setUrlData] = useState(null);

  const generateUrl = (programId = 'all', ageFilters = []) => {
    if (!institutionData) return;

    const baseUrl = "https://budezivo.cz";
    const previewBase = window.location.origin;
    const institutionId = institutionData.institution_id;
    const institutionName = institutionData.institution_name || 'Vaše instituce';

    const params = new URLSearchParams();
    if (programId !== 'all') params.set('program', programId);
    if (ageFilters.length > 0) params.set('age', ageFilters.join(','));
    const queryStr = params.toString() ? `?${params.toString()}` : '';
    const path = `/booking/${institutionId}${queryStr}`;

    if (programId === 'all') {
      const url = `${baseUrl}${path}`;
      const filterLabel = ageFilters.length > 0 ? ` (${ageFilters.join(', ')})` : '';
      setUrlData({
        url,
        previewUrl: `${previewBase}${path}`,
        program_name: `Všechny programy${filterLabel}`,
        institution_name: institutionName,
        embed_code: `<a href="${url}" target="_blank">Rezervovat program v ${institutionName}</a>`
      });
    } else {
      const program = programs.find(p => p.id === programId);
      const url = `${baseUrl}${path}`;
      setUrlData({
        url,
        previewUrl: `${previewBase}${path}`,
        program_name: program?.name_cs || 'Program',
        institution_name: institutionName,
        embed_code: `<a href="${url}" target="_blank">Rezervovat: ${program?.name_cs || 'Program'}</a>`
      });
    }
  };

  const handleProgramSelectForUrl = (programId) => {
    setSelectedProgramForUrl(programId);
    generateUrl(programId, urlAgeFilters);
  };

  const toggleUrlAgeFilter = (code) => {
    const newFilters = urlAgeFilters.includes(code)
      ? urlAgeFilters.filter(c => c !== code)
      : [...urlAgeFilters, code];
    setUrlAgeFilters(newFilters);
    generateUrl(selectedProgramForUrl, newFilters);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Zkopírováno do schránky');
  };

  const handleOpenChange = (val) => {
    if (!val) {
      setSelectedProgramForUrl('all');
      setUrlAgeFilters([]);
      setUrlData(null);
    }
    onOpenChange(val);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="max-w-lg max-h-[85dvh] sm:max-h-[90vh] flex flex-col p-0 overflow-hidden"
        aria-describedby="url-description"
      >
        <div className="p-4 sm:p-6 pb-0 shrink-0">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <LinkIcon className="w-5 h-5" />
              URL pro vložení na web
            </DialogTitle>
            <p id="url-description" className="text-sm text-gray-500 mt-2">
              Vyberte program a zkopírujte URL pro vložení na webové stránky.
            </p>
          </DialogHeader>
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain px-4 sm:px-6 pb-4 sm:pb-6 -webkit-overflow-scrolling-touch">
          <div className="space-y-4 py-4">
            {/* Výběr programu */}
            <div>
              <Label className="text-sm font-medium text-slate-700 mb-2 block">Vyberte program</Label>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-2">
                <button
                  type="button"
                  onClick={() => handleProgramSelectForUrl('all')}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedProgramForUrl === 'all'
                      ? 'bg-slate-800 text-white'
                      : 'hover:bg-gray-100'
                  }`}
                  data-testid="url-select-all"
                >
                  Všechny programy
                </button>
                {Array.isArray(programs) && programs.filter(p => p.status === 'active').map(program => (
                  <button
                    key={program.id}
                    type="button"
                    onClick={() => handleProgramSelectForUrl(program.id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                      selectedProgramForUrl === program.id
                        ? 'bg-slate-800 text-white'
                        : 'hover:bg-gray-100'
                    }`}
                    data-testid={`url-select-${program.id}`}
                  >
                    {program.name_cs}
                  </button>
                ))}
              </div>
            </div>

            {/* Věkový filtr */}
            <div>
              <Label className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4" />
                Filtr věkové skupiny (volitelné)
              </Label>
              <p className="text-xs text-gray-500 mb-2">Vyberte cílovou skupinu — učitelé uvidí jen relevantní programy</p>
              <div className="flex flex-wrap gap-2">
                {URL_AGE_OPTIONS.map(opt => {
                  const isActive = urlAgeFilters.includes(opt.code);
                  return (
                    <button
                      key={opt.code}
                      type="button"
                      onClick={() => toggleUrlAgeFilter(opt.code)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                        isActive
                          ? 'bg-slate-800 text-white border-slate-800'
                          : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                      }`}
                      data-testid={`url-age-filter-${opt.code}`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Vygenerované URL */}
            {urlData && (
              <>
                <div>
                  <Label className="text-xs text-gray-500">Vybraný program</Label>
                  <p className="font-medium">{urlData.program_name}</p>
                </div>

                <div>
                  <Label className="text-xs text-gray-500">URL pro rezervaci</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      value={urlData.url}
                      readOnly
                      className="flex-1 text-sm font-mono"
                      data-testid="external-url-input"
                    />
                    <Button
                      size="sm"
                      onClick={() => copyToClipboard(urlData.url)}
                      className="bg-slate-800 text-white shrink-0"
                      data-testid="copy-url-btn"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div>
                  <Label className="text-xs text-gray-500">HTML kód pro vložení</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      value={urlData.embed_code}
                      readOnly
                      className="flex-1 text-sm font-mono"
                      data-testid="embed-code-input"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyToClipboard(urlData.embed_code)}
                      className="shrink-0"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t sticky bottom-0 bg-white pb-2">
                  <Button
                    variant="outline"
                    onClick={() => window.open(urlData.previewUrl, '_blank')}
                    className="flex-1"
                    data-testid="preview-url-btn"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Náhled
                  </Button>
                  <Button
                    onClick={() => handleOpenChange(false)}
                    className="flex-1 bg-slate-800 text-white"
                    data-testid="close-url-modal-btn"
                  >
                    Zavřít
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
