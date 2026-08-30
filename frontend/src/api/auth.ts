import { apiRequest, authToken } from './client'

export interface User { id: string; email: string; is_active: boolean }
interface TokenResponse { access_token: string; token_type: string; expires_in: number; user: User }

export async function authenticate(mode: 'login' | 'register', email: string, password: string): Promise<User> {
  const result = await apiRequest<TokenResponse>(`/auth/${mode}`, { method: 'POST', body: JSON.stringify({ email, password }) })
  authToken.set(result.access_token)
  return result.user
}
export const currentUser = () => apiRequest<User>('/auth/me')
export const logout = () => authToken.clear()
