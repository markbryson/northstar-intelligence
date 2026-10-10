/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        panel: "#0d1b2e",
        cyan: "#6ee7d8",
        amber: "#ffbe71",
      },
      boxShadow: {
        soft: "0 20px 60px rgba(2, 8, 23, 0.2)",
      },
    },
  },
  plugins: [],
};
