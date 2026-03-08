import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import zh from './locales/zh.json'
import es from './locales/es.json'

const STORAGE_KEY = 'i18n_lang'

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    zh: { translation: zh },
    es: { translation: es },
  },
  lng: localStorage.getItem(STORAGE_KEY) || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function changeLanguage(lang: string): void {
  void i18n.changeLanguage(lang)
  localStorage.setItem(STORAGE_KEY, lang)
}

export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
  { code: 'es', label: 'ES' },
] as const

export default i18n
