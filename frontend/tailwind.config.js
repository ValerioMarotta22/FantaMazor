/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f14",
        panel: "#121821",
        panel2: "#182130",
        border: "#233040",
        accent: "#3ddc97",
        warn: "#f5a524",
        danger: "#f5455c",
        muted: "#7c8aa0",
      },
    },
  },
  plugins: [],
};
