import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        kesha: {
          page: "var(--color-page)",
          card: "var(--color-card)",
          "card-hover": "var(--color-card-hover)",
          border: "var(--color-border)",
          "text-primary": "var(--color-text-primary)",
          "text-secondary": "var(--color-text-secondary)",
          "text-tertiary": "var(--color-text-tertiary)",
          accent: "var(--color-accent)",
          "accent-bg": "var(--color-accent-bg)",
          "accent-border": "var(--color-accent-border)",
          income: "var(--color-income)",
          "income-bg": "var(--color-income-bg)",
          "income-border": "var(--color-income-border)",
          expense: "var(--color-expense)",
          "expense-bg": "var(--color-expense-bg)",
          "expense-border": "var(--color-expense-border)",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
