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
      fontFamily: {
        sans: ['var(--font-nunito-sans)', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Neutral families read the :root/.dark CSS variables (globals.css) so
        // the stored theme preference (#64) actually flips light/dark. The
        // .dark values match the previous hardcoded RGBs, so the default dark
        // look is unchanged. NB: the old var(--color-*) names only existed in
        // the Tailwind-v4 @theme block, which v3 ignores — they never resolved.
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Brand colors stay fixed across themes.
        primary: {
          DEFAULT: "rgb(79, 70, 229)",
          foreground: "white",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        // #682. The destructive role needs **two** colours, because its two uses
        // pull opposite ways on a dark background: white must be legible on the
        // fill (needs a dark red), and the text must be legible on the surface
        // (needs a light one). One value cannot do both — red-700 is 6.47:1
        // under white but 3.06:1 on --background; red-400 is 7.16:1 there but
        // leaves white at 2.24:1.
        //
        // So `DEFAULT` follows the theme through `--destructive` (red-700 light,
        // red-400 dark), which carries **every** text shape automatically —
        // `text-destructive`, `text-destructive/90`, and the
        // `data-[variant=destructive]:` and `data-[error=true]:` variants, each
        // of which is a *separate class* a hand-written `.dark` override has to
        // name individually. Missing one of those is the #632 trap, and the
        // pre-PR review on this change caught exactly that in the first cut.
        //
        // `surface` is the fill, theme-fixed at red-700 so white clears AA in
        // both themes. Four call sites use it; everything else wants DEFAULT.
        //
        // The previous value was a literal red-500, which overrode the
        // (theme-aware, and therefore inert) tokens already in globals.css —
        // the #634 trap.
        destructive: {
          // `rgb(<channels> / <alpha-value>)`, not `var(--destructive)`.
          // Tailwind v3 cannot apply an opacity modifier to an opaque
          // `var()`, so the plain form silently stops emitting
          // `bg-destructive/10`, `border-destructive/20`,
          // `text-destructive/90` and `ring-destructive/20` — verified by
          // building the CSS, where all four went to zero rules. The
          // channel form keeps every slash variant working.
          DEFAULT: "rgb(var(--destructive-rgb) / <alpha-value>)",
          foreground: "white",
          surface: "rgb(185, 28, 28)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
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
