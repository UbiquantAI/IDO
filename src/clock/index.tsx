/**
 * Clock window main entry point
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('clock-root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
