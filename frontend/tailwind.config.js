/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark GitHub palette with macOS refinement
        primary: {
          50: '#f0f3f7',
          100: '#dce4ee',
          200: '#b9c9dd',
          300: '#8fa8c4',
          400: '#6b8caf',
          500: '#4a7099',
          600: '#3d5a7d',
          700: '#2f4461',
          800: '#1f2d3d',
          900: '#0d1117',
        },
        accent: {
          green: '#3fb950',
          blue: '#58a6ff',
          purple: '#a371f7',
          red: '#f85149',
          orange: '#d29922',
        },
        glass: {
          light: 'rgba(255, 255, 255, 0.75)',
          dark: 'rgba(22, 27, 34, 0.85)',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['SF Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.1)',
        'glass-lg': '0 12px 48px 0 rgba(31, 38, 135, 0.15)',
      },
      cursor: {
        'ns-resize': 'ns-resize',
      },
    },
  },
  plugins: [],
}