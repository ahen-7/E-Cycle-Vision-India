
import { useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

type LoginRole = 'user' | 'admin' | 'partner' | 'aggregator' | 'recycler'
type PageMode = 'login' | 'register' | 'apply'

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

type ApplicationForm = {
  organisation_name: string
  contact_person: string
  phone: string
  email: string
  state: string
  district: string
  city: string
  pincode: string
  accepted_categories: string
  capacity: string
  organisation_type: 'aggregator' | 'recycler'
  authorization_details: string
  registration_number: string
}

const initialApplication: ApplicationForm = {
  organisation_name: '',
  contact_person: '',
  phone: '',
  email: '',
  state: '',
  district: '',
  city: '',
  pincode: '',
  accepted_categories: '',
  capacity: '',
  organisation_type: 'aggregator',
  authorization_details: '',
  registration_number: ''
}

function AuthPage({ onAuthSuccess }: AuthPageProps) {
  const [mode, setMode] = useState<PageMode>('login')
  const [loginRole, setLoginRole] = useState<LoginRole>('user')

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const [application, setApplication] =
    useState<ApplicationForm>(initialApplication)
  const [document, setDocument] = useState<File | null>(null)

  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const updateApplication = (
    field: keyof ApplicationForm,
    value: string
  ) => {
    setApplication(previous => ({
      ...previous,
      [field]: value
    }))
  }

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      if (mode === 'apply') {
        if (!document) {
          throw new Error('Please upload your organisation supporting document.')
        }

        const applicationBody = {
          ...application,
          capacity: Number(application.capacity),
          accepted_categories: application.accepted_categories
            .split(',')
            .map(category => category.trim())
            .filter(Boolean)
            .join(', ')
        }

        // Step 1: Submit organisation application.
        const applicationResponse = await fetch(
          `${API}/partner-applications`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(applicationBody)
          }
        )

        const applicationData = await applicationResponse.json()

        if (!applicationResponse.ok) {
          throw new Error(
            applicationData.detail || 'Could not submit application.'
          )
        }

        const applicationId = applicationData.id

        if (!applicationId) {
          throw new Error(
            'Application submitted, but the server did not return an application ID.'
          )
        }

        // Step 2: Upload supporting document.
        const formData = new FormData()
        formData.append('file', document)

        const uploadResponse = await fetch(
          `${API}/partner-applications/${applicationId}/upload-document`,
          {
            method: 'POST',
            body: formData
          }
        )

        const uploadData = await uploadResponse.json()

        if (!uploadResponse.ok) {
          throw new Error(
            uploadData.detail ||
            'Application was created, but document upload failed. Please contact the administrator.'
          )
        }

        setMessage(
          `Application submitted successfully! Your application ID is ${applicationId}. Status: Pending Verification. You can log in after admin approval.`
        )

        setDocument(null)
        setApplication(initialApplication)
        return
      }

      // Existing login and user registration flow.
      const endpoint =
        mode === 'login' ? '/auth/login' : '/auth/register'

      const body =
        mode === 'login'
          ? { email, password }
          : { full_name: fullName, email, password }

      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      const data: AuthResult & { detail?: string } =
        await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      if (mode === 'login' && data.role !== loginRole) {
        throw new Error(
          `This account is registered as ${data.role}. Please select the correct login type.`
        )
      }

      onAuthSuccess(data)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Something went wrong'
      )
    } finally {
      setLoading(false)
    }
  }

  const changeMode = (newMode: PageMode) => {
    setMode(newMode)
    setMessage('')
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
          {mode === 'login'
            ? 'Welcome back'
            : mode === 'register'
              ? 'Create your account'
              : 'Organisation Application'}
        </h1>

        <p>
          {mode === 'login'
            ? 'Log in to manage your e-waste journey.'
            : mode === 'register'
              ? 'Join us in building a responsible e-waste network.'
              : 'Apply to join our verified e-waste network.'}
        </p>

        <form onSubmit={handleSubmit} className="collection-form">

          {/* LOGIN */}
          {mode === 'login' && (
            <label>
              Login as
              <select
                value={loginRole}
                onChange={e =>
                  setLoginRole(e.target.value as LoginRole)
                }
              >
                <option value="user">User</option>
                <option value="partner">Collection Partner (Legacy)</option>
                <option value="aggregator">Aggregator</option>
                <option value="recycler">Recycler</option>
                <option value="admin">Admin</option>
              </select>
            </label>
          )}

          {/* USER REGISTRATION */}
          {mode === 'register' && (
            <label>
              Full name
              <input
                required
                minLength={2}
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="Enter your full name"
              />
            </label>
          )}

          {/* LOGIN AND USER REGISTRATION */}
          {mode !== 'apply' && (
            <>
              <label>
                Email address
                <input
                  required
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
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
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                />
              </label>
            </>
          )}

          {/* ORGANISATION APPLICATION */}
          {mode === 'apply' && (
            <>
              <label>
                Organisation type
                <select
                  value={application.organisation_type}
                  onChange={e =>
                    updateApplication(
                      'organisation_type',
                      e.target.value
                    )
                  }
                >
                  <option value="aggregator">Aggregator</option>
                  <option value="recycler">Recycler</option>
                </select>
              </label>

              <label>
                Organisation name
                <input
                  required
                  minLength={2}
                  value={application.organisation_name}
                  onChange={e =>
                    updateApplication('organisation_name', e.target.value)
                  }
                  placeholder="Enter organisation name"
                />
              </label>

              <label>
                Contact person
                <input
                  required
                  minLength={2}
                  value={application.contact_person}
                  onChange={e =>
                    updateApplication('contact_person', e.target.value)
                  }
                  placeholder="Enter contact person's name"
                />
              </label>

              <label>
                Phone number
                <input
                  required
                  type="tel"
                  minLength={10}
                  maxLength={15}
                  value={application.phone}
                  onChange={e =>
                    updateApplication('phone', e.target.value)
                  }
                  placeholder="Enter phone number"
                />
              </label>

              <label>
                Email address
                <input
                  required
                  type="email"
                  value={application.email}
                  onChange={e =>
                    updateApplication('email', e.target.value)
                  }
                  placeholder="Organisation email"
                />
              </label>

              <label>
                State
                <input
                  required
                  value={application.state}
                  onChange={e =>
                    updateApplication('state', e.target.value)
                  }
                  placeholder="Enter state"
                />
              </label>

              <label>
                District
                <input
                  required
                  value={application.district}
                  onChange={e =>
                    updateApplication('district', e.target.value)
                  }
                  placeholder="Enter district"
                />
              </label>

              <label>
                City
                <input
                  required
                  value={application.city}
                  onChange={e =>
                    updateApplication('city', e.target.value)
                  }
                  placeholder="Enter city"
                />
              </label>

              <label>
                PIN code
                <input
                  required
                  inputMode="numeric"
                  pattern="[1-9][0-9]{5}"
                  maxLength={6}
                  value={application.pincode}
                  onChange={e =>
                    updateApplication('pincode', e.target.value)
                  }
                  placeholder="6-digit PIN code"
                />
              </label>

              <label>
                Accepted e-waste categories
                <input
                  required
                  value={application.accepted_categories}
                  onChange={e =>
                    updateApplication(
                      'accepted_categories',
                      e.target.value
                    )
                  }
                  placeholder="Example: Laptops, Mobiles, Batteries"
                />
                <small>Separate multiple categories with commas.</small>
              </label>

              <label>
                {application.organisation_type === 'aggregator'
                  ? 'Collection capacity (kg)'
                  : 'Processing capacity (kg)'}
                <input
                  required
                  type="number"
                  min="1"
                  step="1"
                  value={application.capacity}
                  onChange={e =>
                    updateApplication('capacity', e.target.value)
                  }
                  placeholder="Enter capacity in kg"
                />
              </label>

              <label>
                Registration number (optional)
                <input
                  value={application.registration_number}
                  onChange={e =>
                    updateApplication(
                      'registration_number',
                      e.target.value
                    )
                  }
                  placeholder="Enter registration number"
                />
              </label>

              <label>
                Authorisation details (optional)
                <textarea
                  value={application.authorization_details}
                  onChange={e =>
                    updateApplication(
                      'authorization_details',
                      e.target.value
                    )
                  }
                  placeholder="Enter relevant authorisation details"
                />
              </label>

              <label>
                Supporting document
                <input
                  required
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e =>
                    setDocument(e.target.files?.[0] || null)
                  }
                />
                <small>
                  Upload your organisation's supporting or registration document.
                </small>
              </label>
            </>
          )}

          <button
            className="primary-button full-width"
            type="submit"
            disabled={loading}
          >
            {loading
              ? 'Please wait...'
              : mode === 'login'
                ? 'Log in →'
                : mode === 'register'
                  ? 'Create account →'
                  : 'Submit Application →'}
          </button>
        </form>

        {message && (
          <div className="message-box">
            {message}
          </div>
        )}

        <div className="auth-switch">
          {mode === 'login' && (
            <>
              <p>
                Don't have a user account?
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => changeMode('register')}
                >
                  Register
                </button>
              </p>

              <p>
                Are you an organisation?
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => changeMode('apply')}
                >
                  Apply here
                </button>
              </p>
            </>
          )}

          {mode === 'register' && (
            <p>
              Already have an account?
              <button
                type="button"
                className="secondary-button"
                onClick={() => changeMode('login')}
              >
                Log in
              </button>
            </p>
          )}

          {mode === 'apply' && (
            <p>
              Already have an account?
              <button
                type="button"
                className="secondary-button"
                onClick={() => changeMode('login')}
              >
                Back to login
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default AuthPage
