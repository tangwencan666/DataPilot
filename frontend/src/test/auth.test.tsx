import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AuthGate from '../AuthGate'
vi.mock('../App', () => ({ default: () => <div>Dataset workspace</div> }))
vi.mock('../api/auth', () => ({ authenticate: vi.fn(async () => ({ id: 'u1', email: 'demo@example.com', is_active: true })), currentUser: vi.fn(), logout: vi.fn() }))
describe('authentication UI', () => {
  it('renders labelled login fields', () => { render(<AuthGate />); expect(screen.getByLabelText('Email')).toBeInTheDocument(); expect(screen.getByLabelText('Password')).toBeInTheDocument() })
  it('switches to registration', () => { render(<AuthGate />); fireEvent.click(screen.getByRole('button', { name: 'Need an account?' })); expect(screen.getByRole('heading', { name: 'Create account' })).toBeInTheDocument() })
  it('opens the workspace after successful login', async () => { render(<AuthGate />); fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'demo@example.com' } }); fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } }); fireEvent.click(screen.getByRole('button', { name: 'Log in' })); expect(await screen.findByText('Dataset workspace')).toBeInTheDocument() })
})
