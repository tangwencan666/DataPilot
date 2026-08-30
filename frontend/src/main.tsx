import React from 'react'
import ReactDOM from 'react-dom/client'
import { Suspense } from 'react'
import AuthGate from './AuthGate'
import { ErrorBoundary } from './ErrorBoundary'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary><Suspense fallback={<main className="auth-shell">Loading workspace…</main>}><AuthGate /></Suspense></ErrorBoundary>
  </React.StrictMode>,
)
