import js from "@eslint/js";
import globals from "globals";

const jsxUsesVars = {
  meta: { schema: [] },
  create(context) {
    return {
      JSXOpeningElement(node) {
        let nameNode = node.name;
        while (nameNode.type === "JSXMemberExpression") {
          nameNode = nameNode.object;
        }
        if (nameNode.type === "JSXIdentifier") {
          context.sourceCode.markVariableAsUsed(nameNode.name, node);
        } else if (nameNode.type === "JSXNamespacedName") {
          context.sourceCode.markVariableAsUsed(nameNode.namespace.name, node);
        }
      },
    };
  },
};

export default [
  { ignores: ["dist/**", "node_modules/**"] },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-undef": "off",
      "guardrail/jsx-uses-vars": "error",
    },
    plugins: {
      guardrail: { rules: { "jsx-uses-vars": jsxUsesVars } },
    },
  },
];
