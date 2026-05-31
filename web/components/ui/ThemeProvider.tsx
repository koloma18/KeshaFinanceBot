'use client';

import { useEffect } from 'react';

// Inline script to prevent flash of wrong theme — injected in <head>
export const ThemeScript = `
  (function() {
    try {
      var stored = localStorage.getItem('theme');
      if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      } else if (stored === 'light') {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
    } catch(e) {}
  })();
`;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
