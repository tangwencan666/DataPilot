import { FormEvent, useEffect, useState } from 'react'
import App from './App'
import { authenticate, currentUser, logout, User } from './api/auth'
import { authToken } from './api/client'

export default function AuthGate() {
  const [user, setUser] = useState<User | null>(null)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(authToken.get()))
  useEffect(() => { if (authToken.get()) currentUser().then(setUser).catch(() => authToken.clear()).finally(() => setLoading(false)) }, [])
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setLoading(true)
    try { setUser(await authenticate(mode, email, password)) } catch (err) { setError(err instanceof Error ? err.message : 'Authentication failed') } finally { setLoading(false) }
  }
  if (loading && !user) return <main className="auth-shell"><p>Loading DataPilot…</p></main>
  if (!user) return <main className="auth-shell"><form className="auth-card" onSubmit={submit}><p className="eyebrow">DATAPILOT</p><h1>{mode === 'login' ? 'Welcome back' : 'Create account'}</h1>{error && <p className="error" role="alert">{error}</p>}<label>Email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label><label>Password<input type="password" required minLength={8} maxLength={128} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={e => setPassword(e.target.value)} /></label><button type="submit">{mode === 'login' ? 'Log in' : 'Register'}</button><button type="button" className="back" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Need an account?' : 'Already registered?'}</button></form></main>
  return <><div className="session-bar"><span>{user.email}</span><button type="button" onClick={() => { logout(); setUser(null) }}>Log out</button></div><App /></>
}
