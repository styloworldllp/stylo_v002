/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#dbe4ff',
          500: '#4263eb',
          600: '#3b5bdb',
          700: '#2f4ac1',
          900: '#1a2f8f',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
