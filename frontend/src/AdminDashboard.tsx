
import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

type Application = {
  id: number
  organisation_name: string
  contact_person: string
  phone: string
  email: string
  state: string
  district: string
  city: string
  pincode: string
  accepted_categories: string
  capacity: number
  organisation_type: string
  registration_number: string | null
  document_filename: string | null
  status: string
  verification_notes: string | null
  created_at: string
}

type VerificationChecks = {
  documentReviewed: boolean
  authorizationChecked: boolean
}

type OrganisationCredentials = {
  application_id: number
  partner_id: number
  organisation_role: string
  email: string
  temporary_password: string
}

type AdminDashboardProps = {
  authToken: string
}

export default function AdminDashboard({ authToken }: AdminDashboardProps) {
  const [applications, setApplications] = useState<Application[]>([])
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [checks, setChecks] = useState<Record<number, VerificationChecks>>({})
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [credentials, setCredentials] =
    useState<OrganisationCredentials | null>(null)
  const [credentialLoading, setCredentialLoading] = useState<number | null>(null)

  const authHeaders = {
    Authorization: `Bearer ${authToken}`
  }

  const loadApplications = async () => {
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(
        `${API}/admin/partner-applications`,
        { headers: authHeaders }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load applications')
      }

      setApplications(data)
      setMessage(`Loaded ${data.length} applications successfully.`)
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Something went wrong'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (authToken) {
      loadApplications()
    }
  }, [authToken])

  const viewDocument = async (applicationId: number) => {
    try {
      const response = await fetch(
        `${API}/admin/partner-applications/${applicationId}/document`,
        { headers: authHeaders }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Unable to open document')
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Document error'
      )
    }
  }

  const updateCheck = (
    applicationId: number,
    field: keyof VerificationChecks,
    value: boolean
  ) => {
    setChecks(previous => ({
      ...previous,
      [applicationId]: {
        documentReviewed:
          previous[applicationId]?.documentReviewed || false,
        authorizationChecked:
          previous[applicationId]?.authorizationChecked || false,
        [field]: value
      }
    }))
  }

  const copyCredentials = async () => {
    if (!credentials) return

    const text = [
      `Application ID: ${credentials.application_id}`,
      `Partner ID: ${credentials.partner_id}`,
      `Organisation Role: ${credentials.organisation_role}`,
      `Email: ${credentials.email}`,
      `Temporary Password: ${credentials.temporary_password}`
    ].join('\n')

    try {
      await navigator.clipboard.writeText(text)
      setMessage('Login credentials copied successfully.')
    } catch {
      setMessage('Unable to copy automatically. Please copy the credentials manually.')
    }
  }

  const regenerateCredentials = async (applicationId: number) => {
    if (!window.confirm(
      'Regenerate login credentials? The existing password will stop working.'
    )) {
      return
    }

    try {
      setCredentialLoading(applicationId)
      setCredentials(null)
      setMessage('')

      const response = await fetch(
        `${API}/admin/partner-applications/${applicationId}/regenerate-credentials`,
        {
          method: 'POST',
          headers: authHeaders
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to regenerate credentials')
      }

      setCredentials({
        application_id: data.application_id,
        partner_id: data.partner_id,
        organisation_role: data.organisation_role,
        email: data.email,
        temporary_password: data.temporary_password
      })

      setMessage('New organisation login credentials generated successfully.')
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Credential generation failed'
      )
    } finally {
      setCredentialLoading(null)
    }
  }

  const reviewApplication = async (
    applicationId: number,
    action: 'approve' | 'reject'
  ) => {
    const note = notes[applicationId]?.trim()
    const applicationChecks = checks[applicationId]

    if (!note) {
      setMessage('Please enter verification notes or a rejection reason.')
      return
    }

    if (action === 'approve') {
      if (note.length < 20) {
        setMessage(
          'Approval requires at least 20 characters of verification notes.'
        )
        return
      }

      if (!applicationChecks?.documentReviewed) {
        setMessage('Please confirm that you reviewed the supporting document.')
        return
      }

      if (!applicationChecks?.authorizationChecked) {
        setMessage(
          'Please confirm that you checked the applicable registration or authorization details.'
        )
        return
      }
    }

    if (!window.confirm(`Are you sure you want to ${action} this application?`)) {
      return
    }

    try {
      setLoading(true)
      setCredentials(null)

      const parameter = action === 'approve' ? 'notes' : 'reason'

      const response = await fetch(
        `${API}/admin/partner-applications/${applicationId}/${action}?${parameter}=${encodeURIComponent(note)}`,
        {
          method: 'POST',
          headers: authHeaders
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Review failed')
      }

      if (
        action === 'approve' &&
        data.temporary_password &&
        data.email
      ) {
        setCredentials({
          application_id: data.application_id,
          partner_id: data.partner_id,
          organisation_role: data.organisation_role,
          email: data.email,
          temporary_password: data.temporary_password
        })
      }

      setMessage(
        action === 'approve' && data.temporary_password
          ? 'Application approved. Organisation login credentials are displayed below.'
          : data.message || `Application ${action}d successfully.`
      )

      await loadApplications()
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Review failed'
      )
    } finally {
      setLoading(false)
    }
  }

  const pending = applications.filter(
    app => app.status === 'Pending Verification'
  )

  return (
    <section
      className="admin-dashboard"
      style={{
        padding: '32px',
        color: '#e5eee9',
        width: '100%',
        maxWidth: 'none',
        minWidth: 0,
        boxSizing: 'border-box',
        gridColumn: '1 / -1'
      }}
    >
      <span style={{ color: '#58c99a', letterSpacing: '2px' }}>
        ADMIN CONTROL CENTRE
      </span>

      <h1>Partner Verification</h1>

      <p style={{ color: '#9aaca3' }}>
        Review organisation details and supporting documents before activation.
      </p>

      <div style={{
        background: '#142b25',
        padding: '20px',
        borderRadius: '12px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <strong>Admin Authentication</strong>
          <p style={{ color: '#9aaca3', marginBottom: 0 }}>
            Securely connected using your admin account.
          </p>
        </div>

        <button onClick={loadApplications} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh Applications ↻'}
        </button>
      </div>

      {message && (
        <p style={{
          padding: '12px',
          background: '#203b32',
          borderRadius: '8px'
        }}>
          {message}
        </p>
      )}

      {credentials && (
        <div style={{
          background: '#142b25',
          border: '1px solid #58c99a',
          borderRadius: '12px',
          padding: '22px',
          marginBottom: '24px'
        }}>
          <h2 style={{ color: '#58c99a' }}>
            Organisation Login Credentials
          </h2>

          <p>Application ID: {credentials.application_id}</p>
          <p>Partner ID: {credentials.partner_id}</p>
          <p>Organisation Role: {credentials.organisation_role}</p>
          <p>Email: {credentials.email}</p>

          <div style={{
            background: '#0c1e18',
            padding: '12px',
            borderRadius: '8px',
            marginTop: '12px'
          }}>
            <p style={{ marginTop: 0 }}>Temporary Password:</p>
            <strong style={{
              color: '#58c99a',
              wordBreak: 'break-all'
            }}>
              {credentials.temporary_password}
            </strong>
          </div>

          <p style={{ color: '#e6bd78', fontSize: '13px' }}>
            Save these credentials securely now. This temporary password
            will not be displayed again after you leave this screen.
            Share it only with the authorised organisation contact.
          </p>

          <button
            onClick={copyCredentials}
            style={{ marginRight: '10px' }}
          >
            Copy All Credentials
          </button>

          <button
            onClick={() => setCredentials(null)}
          >
            Close
          </button>
        </div>
      )}

      <div style={{
        display: 'flex',
        gap: '24px',
        marginBottom: '24px',
        flexWrap: 'wrap'
      }}>
        <div>
          <h2>{applications.length}</h2>
          <span>Total Applications</span>
        </div>

        <div>
          <h2>{pending.length}</h2>
          <span>Pending Verification</span>
        </div>

        <div>
          <h2>{applications.filter(a => a.status === 'Approved').length}</h2>
          <span>Approved</span>
        </div>

        <div>
          <h2>{applications.filter(a => a.status === 'Rejected').length}</h2>
          <span>Rejected</span>
        </div>
      </div>

      {applications.length === 0 && !loading && (
        <p style={{ color: '#9aaca3' }}>
          No partner applications found.
        </p>
      )}

      {applications.map(app => {
        const applicationChecks = checks[app.id] || {
          documentReviewed: false,
          authorizationChecked: false
        }

        const note = notes[app.id]?.trim() || ''

        const canApprove =
          applicationChecks.documentReviewed &&
          applicationChecks.authorizationChecked &&
          note.length >= 20 &&
          !!app.document_filename

        return (
          <article
            key={app.id}
            style={{
              background: '#142b25',
              border: '1px solid #315344',
              borderRadius: '12px',
              padding: '22px',
              marginBottom: '18px'
            }}
          >
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: '12px',
              flexWrap: 'wrap'
            }}>
              <div>
                <h2>{app.organisation_name}</h2>
                <p>Application #{app.id}</p>
              </div>

              <strong>{app.status}</strong>
            </div>

            <p><b>Contact:</b> {app.contact_person}</p>
            <p><b>Phone:</b> {app.phone}</p>
            <p><b>Email:</b> {app.email}</p>
            <p><b>Type:</b> {app.organisation_type}</p>
            <p>
              <b>Location:</b> {app.city}, {app.district}, {app.state} - {app.pincode}
            </p>
            <p><b>Categories:</b> {app.accepted_categories}</p>
            <p><b>Capacity:</b> {app.capacity} units</p>
            <p>
              <b>Registration Number:</b>{' '}
              {app.registration_number || 'Not provided'}
            </p>

            <button
              onClick={() => viewDocument(app.id)}
              disabled={!app.document_filename}
            >
              {app.document_filename
                ? 'View Submitted Document'
                : 'No Document Uploaded'}
            </button>

            {app.status === 'Approved' && (
              <div style={{ marginTop: '18px' }}>
                <button
                  onClick={() => regenerateCredentials(app.id)}
                  disabled={
                    credentialLoading !== null || loading
                  }
                >
                  {credentialLoading === app.id
                    ? 'Generating Credentials...'
                    : 'Regenerate Login Credentials'}
                </button>

                <p style={{
                  color: '#9aaca3',
                  fontSize: '13px'
                }}>
                  Generates a new password for this existing organisation account.
                  The previous password will stop working.
                </p>
              </div>
            )}

            {app.status === 'Pending Verification' && (
              <div style={{ marginTop: '24px' }}>
                <h3>Verification Checklist</h3>

                <p style={{ color: '#9aaca3' }}>
                  Complete both checks after manually reviewing the organisation's details.
                </p>

                <label style={{
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'center',
                  marginBottom: '14px',
                  cursor: 'pointer'
                }}>
                  <input
                    type="checkbox"
                    checked={applicationChecks.documentReviewed}
                    disabled={!app.document_filename}
                    onChange={e => updateCheck(
                      app.id,
                      'documentReviewed',
                      e.target.checked
                    )}
                  />
                  Supporting document has been opened and reviewed.
                </label>

                <label style={{
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'center',
                  marginBottom: '20px',
                  cursor: 'pointer'
                }}>
                  <input
                    type="checkbox"
                    checked={applicationChecks.authorizationChecked}
                    onChange={e => updateCheck(
                      app.id,
                      'authorizationChecked',
                      e.target.checked
                    )}
                  />
                  Applicable registration / authorization details have been checked.
                </label>

                <p style={{ color: '#9aaca3', fontSize: '13px' }}>
                  Check the requirements applicable to this organisation type.
                  Do not treat a collection centre as an authorized recycler
                  without the relevant evidence.
                </p>

                <label>Verification Notes / Rejection Reason</label>

                <textarea
                  value={notes[app.id] || ''}
                  onChange={e => setNotes(previous => ({
                    ...previous,
                    [app.id]: e.target.value
                  }))}
                  placeholder="Record the documents checked, registration details verified, and your observations..."
                  rows={3}
                  style={{
                    display: 'block',
                    width: '100%',
                    marginTop: '10px',
                    padding: '12px',
                    borderRadius: '8px',
                    boxSizing: 'border-box'
                  }}
                />

                <p style={{ color: '#9aaca3', fontSize: '13px' }}>
                  Approval notes: {note.length}/20 minimum characters
                </p>

                <div style={{
                  display: 'flex',
                  gap: '12px',
                  marginTop: '14px',
                  flexWrap: 'wrap'
                }}>
                  <button
                    onClick={() => reviewApplication(app.id, 'approve')}
                    disabled={!canApprove || loading}
                    title={!canApprove
                      ? 'Complete both checks and enter at least 20 characters of notes'
                      : 'Approve application'}
                  >
                    Approve Application
                  </button>

                  <button
                    onClick={() => reviewApplication(app.id, 'reject')}
                    disabled={loading}
                  >
                    Reject Application
                  </button>
                </div>

                {!canApprove && (
                  <p style={{ color: '#e6bd78', fontSize: '13px' }}>
                    Approval is locked until the checklist and notes requirements are complete.
                  </p>
                )}
              </div>
            )}

            {app.verification_notes && (
              <p><b>Admin Notes:</b> {app.verification_notes}</p>
            )}
          </article>
        )
      })}
    </section>
  )
}
