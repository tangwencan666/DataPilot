const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'datapilot_access_token'

export const authToken = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string, public requestId?: string) {
    super(message)
  }
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  const token = authToken.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options?.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401) authToken.clear()
    const message = response.status === 429 ? '请求过于频繁，请稍后再试。' : body.detail ?? (response.status >= 500 ? '服务暂时不可用。' : '请求失败')
    throw new ApiError(message, response.status, body.code, response.headers.get('X-Request-ID') ?? body.request_id)
  }
  return body as T
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const headers = new Headers()
  const token = authToken.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE}${path}`, { headers })
  if (!response.ok) throw new ApiError('Export failed', response.status)
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url)
}
