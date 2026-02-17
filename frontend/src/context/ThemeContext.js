import React, { createContext, useState } from 'react';

export const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [themeSettings, setThemeSettings] = useState(null);

  const applyTheme = (settings) => {
    if (!settings) return;

    const root = document.documentElement;
    root.style.setProperty('--theme-primary', settings.primary_color);
    root.style.setProperty('--theme-secondary', settings.secondary_color);
    root.style.setProperty('--theme-accent', settings.accent_color);

    setThemeSettings(settings);
  };

  return (
    <ThemeContext.Provider value={{ themeSettings, applyTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
