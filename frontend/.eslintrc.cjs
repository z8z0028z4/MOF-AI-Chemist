module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  ignorePatterns: [
    'dist/',
    'node_modules/',
    'coverage/',
  ],
  plugins: [
    'react-hooks',
    'react-refresh',
  ],
  extends: [
    'eslint:recommended',
  ],
  overrides: [
    {
      files: ['vite.config.js'],
      env: {
        node: true,
      },
    },
  ],
  rules: {
    'no-unused-vars': 'off',
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'off',
    'react-refresh/only-export-components': 'off',
  },
}
