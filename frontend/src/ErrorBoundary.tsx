import { Component, ErrorInfo, ReactNode } from 'react'
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('UI boundary', error, info.componentStack) }
  render() { return this.state.failed ? <main className="auth-shell"><div className="auth-card"><h1>Something went wrong</h1><p>The workspace could not be rendered safely.</p><button onClick={() => location.reload()}>Reload</button></div></main> : this.props.children }
}
