import React from 'react'
import ReactDOM from 'react-dom/client'
import '@zhqingit/liquid-glass-react/styles.css'
import './app/global.css'
import './app/luxlunch.css'

import { ThemeProvider } from './app/ThemeProvider'
import { App } from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
