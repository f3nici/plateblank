/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        surface: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#1a2332',
          300: '#151d2b',
          400: '#111827',
          500: '#0d1320',
          600: '#0a0f1a',
          700: '#070b14',
        },
        accent: {
          DEFAULT: '#14b8a6',
          light: '#2dd4bf',
          dark: '#0d9488',
          glow: 'rgba(20, 184, 166, 0.15)',
        },
      },
    },
  },
  plugins: [],
}
