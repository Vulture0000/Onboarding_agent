module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
  ],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } },
  plugins: ['react'],
  settings: { react: { version: '18.3' } },
  rules: {
    // Keep the new JSX transform: React is imported implicitly.
    'react/react-in-jsx-scope': 'off',
    'react/jsx-uses-react': 'off',
    // Surface genuinely unused code, but do not fail the build on prop-type
    // noise -- these are plain function components with no propTypes.
    'react/prop-types': 'off',
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
  },
}
