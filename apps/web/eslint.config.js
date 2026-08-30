import js from '@eslint/js'
import globals from 'globals'
import tseslint from 'typescript-eslint'
import vue from 'eslint-plugin-vue'

export default tseslint.config({ ignores:['dist/**','test-results/**'] }, js.configs.recommended, ...tseslint.configs.recommended, ...vue.configs['flat/recommended'], {
  files: ['**/*.{ts,vue}'], languageOptions: { globals: globals.browser, parserOptions: { parser: tseslint.parser } },
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/max-attributes-per-line': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/html-self-closing': 'off',
    'vue/attributes-order': 'off'
  }
}, { files:['e2e/server.mjs'], languageOptions:{ globals:globals.node } })
