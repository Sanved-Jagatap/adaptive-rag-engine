import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F2F4EE",
        ink: "#1B1F1B",
        "ink-soft": "#4B524C",
        hairline: "#D7DBD1",
        accent: {
          DEFAULT: "#3B5B63",
          soft: "#E4EAE9",
        },
        signal: {
          high: "#3F7D45",
          "high-soft": "#E4EDE1",
          medium: "#B4802A",
          "medium-soft": "#F3E9D6",
          low: "#A6432A",
          "low-soft": "#F1E0D9",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0px",
        sm: "2px",
      },
      maxWidth: {
        console: "72rem",
      },
    },
  },
  plugins: [],
};

export default config;
