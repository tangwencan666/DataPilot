import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest, authToken } from '../api/client'
describe('API client', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('uses the same-origin API proxy by default', async () => { const mock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })); await apiRequest('/health'); expect(mock).toHaveBeenCalledWith('/api/v1/health', expect.any(Object)) })
  it('adds the bearer token', async () => { authToken.set('token'); const mock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })); await apiRequest('/health'); expect(new Headers(mock.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer token') })
  it('normalizes rate limit errors', async () => { vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ code: 'RATE_LIMIT_EXCEEDED' }), { status: 429 })); await expect(apiRequest('/datasets')).rejects.toMatchObject({ status: 429, code: 'RATE_LIMIT_EXCEEDED' }) })
  it('clears expired authentication', async () => { authToken.set('expired'); vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 401 })); await expect(apiRequest('/datasets')).rejects.toBeInstanceOf(ApiError); expect(authToken.get()).toBeNull() })
})
