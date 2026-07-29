/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        express: {
          yellow: '#FACC15',
          gold: '#EAB308',
          dark: '#0F172A',
          card: '#1E293B',
          accent: '#3B82F6',
          danger: '#EF4444',
          success: '#10B981',
          muted: '#64748B',
        }
      },
      fontFamily: {
        sans: ['Golos Text', 'Inter', 'sans-serif'],
        display: ['Bebas Neue', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
