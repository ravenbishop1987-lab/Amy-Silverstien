/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#FDFCFA',
          100: '#FAF9F7',
          200: '#F5F3EF',
          300: '#EDE9E3',
        },
        sage: {
          100: '#D4E6D4',
          200: '#B8D4B8',
          300: '#9EC09E',
          400: '#8FAF8F',
          500: '#7A9E7A',
          600: '#668B66',
          700: '#527852',
        },
        blush: {
          100: '#FCECEA',
          200: '#F9D5CF',
          300: '#F4B8B0',
          400: '#EE9A8F',
        },
        charcoal: {
          800: '#2D2D2D',
          900: '#1A1A1A',
        },
      },
      fontFamily: {
        serif: ['Lora', 'Georgia', 'serif'],
        sans: ['DM Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        soft: '0 2px 15px rgba(0,0,0,0.06)',
        card: '0 4px 20px rgba(0,0,0,0.08)',
        glow: '0 0 20px rgba(143, 175, 143, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'typing': 'typing 1.2s steps(3, end) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
}
