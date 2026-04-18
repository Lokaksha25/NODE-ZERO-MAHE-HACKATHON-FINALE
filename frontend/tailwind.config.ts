import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
    "./src/lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dusk: {
          50: "#f3f4f8",
          100: "#d4d8e2",
          200: "#aab2c4",
          300: "#7d8aa6",
          400: "#596884",
          500: "#3e4f6a",
          600: "#2f3d53",
          700: "#232f3f",
          800: "#1a2330",
          900: "#111823"
        },
        ember: "#ff8a3d",
        moss: "#2d965d",
        amber: "#e3a008",
        coral: "#e14c4c"
      },
      boxShadow: {
        glass: "0 14px 40px rgba(17, 24, 35, 0.35)",
      },
      backgroundImage: {
        "mesh-atmos": "radial-gradient(circle at 15% 20%, rgba(255,138,61,0.22), transparent 35%), radial-gradient(circle at 80% 10%, rgba(45,150,93,0.24), transparent 30%), radial-gradient(circle at 20% 90%, rgba(225,76,76,0.18), transparent 30%), linear-gradient(135deg, #111823 0%, #1a2330 42%, #2f3d53 100%)"
      }
    }
  },
  plugins: [],
};

export default config;
