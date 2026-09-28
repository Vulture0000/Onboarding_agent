/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0a0e1a',
        panel: '#111827',
        card: '#1a2234',
        edge: '#263049',
        accent: '#6366f1',
        accent2: '#8b5cf6',
      },
    },
  },
  plugins: [],
}
