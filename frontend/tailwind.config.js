/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1D6FD1', dark: '#0C4A93', light: '#EAF3FD' },
      },
    },
  },
  plugins: [],
}
