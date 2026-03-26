import React, { useEffect, useState } from 'react';
import { Header } from '../../components/layout/Header';
import { Card } from '../../components/ui/card';
import axios from 'axios';
import { API } from '../../config/api';
import { FileText } from 'lucide-react';

export const VopPage = () => {
  const [vop, setVop] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVop = async () => {
      try {
        const response = await axios.get(`${API}/legal/vop`);
        setVop(response.data);
      } catch (error) {
        console.error('Failed to load VOP:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchVop();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFC]">
        <Header minimal={true} />
        <div className="max-w-3xl mx-auto px-4 py-12 text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-slate-800 mx-auto" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC]" data-testid="vop-page">
      <Header minimal={true} />
      <div className="max-w-3xl mx-auto px-4 py-8 md:py-12">
        <Card className="p-6 md:p-10 bg-white">
          <div className="flex items-center gap-3 mb-8">
            <FileText className="w-6 h-6 text-slate-700" />
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
              {vop?.title || 'Všeobecné obchodní podmínky'}
            </h1>
          </div>

          <p className="text-xs text-gray-400 mb-8">Verze: {vop?.version || 'v1'}</p>

          <div className="space-y-8">
            {vop?.sections?.map((section) => (
              <div key={section.number} className="space-y-3">
                <h2 className="text-lg font-semibold text-slate-800">
                  {section.number}. {section.title}
                </h2>
                {section.content.map((paragraph, idx) => (
                  <p key={idx} className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
                    {paragraph}
                  </p>
                ))}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default VopPage;
