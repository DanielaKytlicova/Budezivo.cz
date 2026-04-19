import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API } from '../config/api';

/**
 * Hook for frontend feature gating.
 * Loads plan status from backend and provides hasAccess() checker.
 * 
 * Usage:
 *   const { hasAccess, planData, showUpgrade } = usePlanFeatures();
 *   if (!hasAccess('mailing')) showUpgrade('mailing');
 */
export const usePlanFeatures = () => {
  const [planData, setPlanData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgradeFeature, setUpgradeFeature] = useState(null);

  const fetchPlan = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/plan/status`, { withCredentials: true });
      setPlanData(res.data);
    } catch {
      setPlanData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlan(); }, [fetchPlan]);

  const hasAccess = useCallback((featureKey) => {
    if (!planData?.features) return true; // If not loaded, allow (backend will enforce)
    const feature = planData.features[featureKey];
    return feature?.has_access ?? true;
  }, [planData]);

  const getFeatureInfo = useCallback((featureKey) => {
    if (!planData?.features) return null;
    return planData.features[featureKey] || null;
  }, [planData]);

  const showUpgrade = useCallback((featureKey) => {
    setUpgradeFeature(featureKey);
  }, []);

  const hideUpgrade = useCallback(() => {
    setUpgradeFeature(null);
  }, []);

  return {
    planData,
    loading,
    hasAccess,
    getFeatureInfo,
    upgradeFeature,
    showUpgrade,
    hideUpgrade,
    refreshPlan: fetchPlan,
  };
};

export default usePlanFeatures;
