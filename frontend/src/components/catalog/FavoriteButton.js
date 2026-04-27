import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Heart } from 'lucide-react';
import { useTeacherAuth } from '../../context/TeacherAuthContext';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Heart toggle that requires teacher auth.
 *
 * - If not authenticated, prompts user to log in (redirect to /ucitel/prihlaseni).
 * - If authenticated, sends POST/DELETE to /api/teacher/favorites and toggles state.
 *
 * `initialFavorited` is optional — if not provided, the component will lazily
 * check via /api/teacher/favorites only on first interaction.
 */
export const FavoriteButton = ({
  programId,
  variant = 'icon',          // 'icon' | 'pill'
  initialFavorited = null,
  onChange,
  className = '',
}) => {
  const navigate = useNavigate();
  const { isAuthenticated, authConfig } = useTeacherAuth();
  const [favorited, setFavorited] = useState(initialFavorited);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setFavorited(initialFavorited);
  }, [initialFavorited]);

  // Lazy-init favorited state for authenticated user when prop is not provided
  useEffect(() => {
    if (!isAuthenticated || favorited !== null) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await axios.get(`${API_URL}/api/teacher/favorites`, authConfig());
        if (!cancelled) {
          setFavorited((data || []).some(f => f.program_id === programId));
        }
      } catch (_e) {
        if (!cancelled) setFavorited(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isAuthenticated, programId, favorited, authConfig]);

  const onClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isAuthenticated) {
      toast('Pro uložení do oblíbených se přihlaste.', {
        action: { label: 'Přihlásit', onClick: () => navigate('/ucitel/prihlaseni') },
      });
      return;
    }
    setLoading(true);
    try {
      if (favorited) {
        await axios.delete(`${API_URL}/api/teacher/favorites/${programId}`, authConfig());
        setFavorited(false);
        onChange && onChange(false);
      } else {
        await axios.post(`${API_URL}/api/teacher/favorites`, { program_id: programId }, authConfig());
        setFavorited(true);
        onChange && onChange(true);
      }
    } catch (_e) {
      toast.error('Operace se nezdařila');
    } finally {
      setLoading(false);
    }
  };

  if (variant === 'pill') {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm transition-colors ${favorited ? 'bg-rose-50 border-rose-200 text-rose-700' : 'bg-white border-gray-200 text-gray-600 hover:border-rose-200 hover:text-rose-600'} ${className}`}
        data-testid={`favorite-pill-${programId}`}
        aria-pressed={!!favorited}
        title={favorited ? 'Odebrat z oblíbených' : 'Přidat do oblíbených'}
      >
        <Heart className={`w-4 h-4 ${favorited ? 'fill-rose-500 text-rose-500' : ''}`} strokeWidth={2} />
        {favorited ? 'V oblíbených' : 'Uložit'}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className={`inline-flex items-center justify-center w-9 h-9 rounded-full transition-colors ${favorited ? 'bg-rose-100 text-rose-600 hover:bg-rose-200' : 'bg-white/90 text-gray-500 hover:text-rose-500 hover:bg-rose-50 shadow-sm'} ${className}`}
      data-testid={`favorite-icon-${programId}`}
      aria-pressed={!!favorited}
      aria-label={favorited ? 'Odebrat z oblíbených' : 'Přidat do oblíbených'}
      title={favorited ? 'Odebrat z oblíbených' : 'Přidat do oblíbených'}
    >
      <Heart className={`w-5 h-5 ${favorited ? 'fill-rose-500 text-rose-500' : ''}`} strokeWidth={2} />
    </button>
  );
};

export default FavoriteButton;
