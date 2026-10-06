import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextVitals,
  ...nextTypescript,
  {
    ignores: [".next/**", "node_modules/**", "src/traffic_sim/**", "public/vendor/**", "build/**", ".venv/**", "archive/**"],
  },
];

export default eslintConfig;
