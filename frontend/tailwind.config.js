import tailwindcssAnimate from "tailwindcss-animate";
import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
const config = {
  darkMode: ["class"],
  content: [
    './src/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/app/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "var(--color-border)",
        input: "var(--color-input)",
        ring: "var(--color-ring)",
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        primary: {
          DEFAULT: "rgb(79, 70, 229)",
          foreground: "white",
        },
        secondary: {
          DEFAULT: "rgb(30, 41, 59)",
          foreground: "rgb(248, 250, 252)",
        },
        destructive: {
          DEFAULT: "rgb(239, 68, 68)",
          foreground: "white",
        },
        muted: {
          DEFAULT: "rgb(39, 39, 42)",
          foreground: "rgb(161, 161, 170)",
        },
        accent: {
          DEFAULT: "rgb(39, 39, 42)",
          foreground: "white",
        },
        popover: {
          DEFAULT: "rgb(24, 24, 27)",
          foreground: "rgb(250, 250, 250)",
        },
        card: {
          DEFAULT: "rgb(24, 24, 27)",
          foreground: "rgb(250, 250, 250)",
        },
      },
      borderRadius: {
        lg: "0.5rem",
        md: "calc(0.5rem - 2px)",
        sm: "calc(0.5rem - 4px)",
      },
    },
  },
  plugins: [tailwindcssAnimate, typography],
};

export default config;