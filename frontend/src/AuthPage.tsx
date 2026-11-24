
import { useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

type LoginRole = 'user' | 'admin' | 'partner'

type AuthResult = {
  access_token: string
  token_type: string
  role: string
  full_name: string
  partner_id: number | null
}

type AuthPageProps = {
  onAuthSuccess: (data: AuthResult) => void
}

function AuthPage({ onAuthSuccess }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loginRole, setLoginRole] = useState<LoginRole>('user')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const endpoint =
        mode === 'login' ? '/auth/login' : '/auth/register'

      const body =
        mode === 'login'
          ? { email, password }
          : { full_name: fullName, email, password }

      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      const data: AuthResult & { detail?: string } = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      // The backend remains the source of truth for account roles.
      if (mode === 'login' && data.role !== loginRole) {
        throw new Error(
          `This account is registered as ${data.role}. Please select the correct login type.`
        )
      }

      onAuthSuccess(data)
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Something went wrong'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand">
          <div className="brand-icon">E</div>
          <div>
            <h2>E-CYCLE</h2>
            <span>VISION INDIA</span>
          </div>
        </div>

        <span className="eyebrow">A SMARTER CIRCULAR FUTURE</span>

        <h1>
          {mode === 'login' ? 'Welcome back' : 'Create your account'}
        </h1>

        <p>
          {mode === 'login'
            ? 'Log in to manage your e-waste journey.'
            : 'Join us in building a responsible e-waste network.'}
        </p>

        <form onSubmit={handleSubmit} className="collection-form">

          {mode === 'login' && (
            <label>
              Login as
              <select
                value={loginRole}
                onChange={(e) =>
                  setLoginRole(e.target.value as LoginRole)
                }
              >
                <option value="user">User</option>
                <option value="partner">Collection Partner</option>
                <option value="admin">Admin</option>
              </select>
            </label>
          )}

          {mode === 'register' && (
            <label>
              Full name
              <input
                required
                minLength={2}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
              />
            </label>
          )}

          <label>
            Email address
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </label>

          <label>
            Password
            <input
              required
              type="password"
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </label>

          <button
            className="primary-button full-width"
            type="submit"
            disabled={loading}
          >
            {loading
              ? 'Please wait...'
              : mode === 'login'
                ? 'Log in →'
                : 'Create account →'}
          </button>
        </form>

        {message && <div className="message-box">{message}</div>}

        <p className="auth-switch">
          {mode === 'login'
            ? "Don't have an account?"
            : 'Already have an account?'}

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setMessage('')
            }}
          >
            {mode === 'login' ? 'Register' : 'Log in'}
          </button>
        </p>
      </div>
    </div>
  )
}

export default AuthPage
