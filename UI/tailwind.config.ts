import type { Config } from "tailwindcss";

export default <Partial<Config>>{
  darkMode: "class",
  plugins: [require("@tailwindcss/typography")],
};
