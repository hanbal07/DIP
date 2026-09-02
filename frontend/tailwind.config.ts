import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "0 0% 100%",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "0 0% 100%",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "0 0% 100%",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        sm: "0 1px 2px 0 rgb(15 23 42 / 0.04)",
        DEFAULT: "0 1px 3px 0 rgb(15 23 42 / 0.06), 0 1px 2px -1px rgb(15 23 42 / 0.06)",
        md: "0 4px 6px -1px rgb(15 23 42 / 0.07), 0 2px 4px -2px rgb(15 23 42 / 0.06)",
        lg: "0 10px 15px -3px rgb(15 23 42 / 0.08), 0 4px 6px -4px rgb(15 23 42 / 0.05)",
        xl: "0 20px 25px -5px rgb(15 23 42 / 0.10), 0 8px 10px -6px rgb(15 23 42 / 0.05)",
        brand:
          "0 8px 24px -6px hsl(224 50% 30% / 0.28), 0 4px 10px -4px hsl(224 50% 30% / 0.18)",
        "card-hover":
          "0 12px 24px -8px hsl(224 25% 15% / 0.12), 0 4px 10px -6px hsl(224 25% 15% / 0.08)",
      },
      maxWidth: {
        "screen-3xl": "1920px",
      },
    },
  },
  plugins: [],
};

export default config;