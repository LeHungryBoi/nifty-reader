/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{rs,html,css}",
    "./*.{rs,html,css}"
  ],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
};