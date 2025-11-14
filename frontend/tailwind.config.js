/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        eve: {
          dark: '#0a0e1a',
          darker: '#050810',
          blue: '#1e3a5f',
          'blue-dark': '#152a45',
          lightblue: '#2d5a8a',
          accent: '#4a9eff',
          gray: '#1a1f2e',
          'gray-dark': '#141821',
        },
      },
    },
  },
  plugins: [],
}

