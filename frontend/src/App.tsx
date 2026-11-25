import { useState } from 'react'
import './App.css'
import AdminDashboard from './AdminDashboard'
import AuthPage from './AuthPage'
import PartnerDashboard from './PartnerDashboard'
import NetworkMap from './NetworkMap';
import LocationPicker from './LocationPicker';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

type CollectionForm = {
  requester_name: string
  requester_type: string
  device_category: string
  quantity: number
  condition: string
  state: string
  district: string
  city: string
  pincode: string
  description: string
}

type PartnerForm = {
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
  authorization_details: string
  latitude: number | null
  longitude: number | null
}

function App() {
  const [authToken, setAuthToken] = useState<string | null>(null)
  const [currentUser, setCurrentUser] = useState<any>(null)

  const handleAuthSuccess = (data: any) => {
    setAuthToken(data.access_token)
    setCurrentUser({
      full_name: data.full_name,
      role: data.role,
      partner_id: data.partner_id
    })
  }

  const [activeTab, setActiveTab] = useState('overview')
  const [trackingId, setTrackingId] = useState('')
  const [trackingData, setTrackingData] = useState<any>(null)
  const [partners, setPartners] = useState<any[]>([])
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const [partnerForm, setPartnerForm] = useState<PartnerForm>({
    organisation_name: '',
    contact_person: '',
    phone: '',
    email: '',
    state: '',
    district: '',
    city: '',
    pincode: '',
    accepted_categories: '',
    capacity: 1,
    organisation_type: 'Local Collection Centre',
    authorization_details: '',
    latitude: null,
    longitude: null
  })

  const [form, setForm] = useState<CollectionForm>({
    requester_name: '',
    requester_type: 'Household',
    device_category: 'Mobile Phone',
    quantity: 1,
    condition: 'Non-working',
    state: '',
    district: '',
    city: '',
    pincode: '',
    description: ''
  })

  const updateForm = (
    field: keyof CollectionForm,
    value: string | number
  ) => {
    setForm((previous) => ({ ...previous, [field]: value }))
  }

  const updatePartnerForm = (
    field: keyof PartnerForm,
    value: string | number | null
  ) => {
    setPartnerForm((previous) => ({ ...previous, [field]: value }))
  }

  const submitPartnerApplication = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    if (
  partnerForm.latitude === null ||
  partnerForm.longitude === null
) {
  setMessage('Please select your organisation location on the map.')
  return
}
    try {
      const response = await fetch(`${API}/partner-applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(partnerForm)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to submit application')
      }

      setMessage(
        `Application submitted successfully! Application ID: ${data.id}. Status: ${data.status}`
      )
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Something went wrong'
      )
    } finally {
      setLoading(false)
    }
  }

  const submitRequest = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/requests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(form)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to submit request')
      }

      setTrackingId(data.tracking_id)
      setMessage(
        `Request submitted successfully! Your tracking ID is ${data.tracking_id}`
      )
      setTrackingData(null)
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Something went wrong'
      )
    } finally {
      setLoading(false)
    }
  }

  // Tracking must call the tracking endpoint, not the partner recommendation endpoint.
  const trackRequest = async () => {
    if (!trackingId.trim()) {
      setMessage('Please enter a tracking ID.')
      return
    }

    setLoading(true)
    setMessage('')
    setTrackingData(null)

    try {
      const response = await fetch(
        `${API}/tracking/${encodeURIComponent(trackingId.trim())}`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`
          }
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Tracking record not found')
      }

      setTrackingData(data)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to retrieve tracking details'
      )
    } finally {
      setLoading(false)
    }
  }

  const loadPartners = async () => {
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/partners`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load partners')
      }

      setPartners(data)
      setActiveTab('partners')
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Unable to load partners'
      )
    } finally {
      setLoading(false)
    }
  }

  const loadRecommendations = async () => {
    if (!trackingId.trim()) {
      setMessage('Please enter a tracking ID first.')
      return
    }

    setLoading(true)
    setMessage('')
    setRecommendations([])

    try {
      const response = await fetch(
        `${API}/partners/recommend/${encodeURIComponent(trackingId.trim())}`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`
          }
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load recommendations')
      }

      setRecommendations(
        Array.isArray(data) ? data : data.recommendations || []
      )
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Unable to load recommendations'
      )
    } finally {
      setLoading(false)
    }
  }

  if (!authToken) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />
  }
  if (
  ['partner', 'aggregator', 'recycler'].includes(
    currentUser?.role ?? ''
  )
) {
  return (
    <PartnerDashboard
      authToken={authToken}
      fullName={currentUser.full_name}
      role={currentUser.role}
    />
  )
}
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">E</div>
          <div>
            <h2>E-CYCLE</h2>
            <span>VISION INDIA</span>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <button
          className={activeTab === 'overview' ? 'nav-item active' : 'nav-item'}
          onClick={() => setActiveTab('overview')}
        >
          ◈ <span>Overview</span>
        </button>

        <button
          className={activeTab === 'collection' ? 'nav-item active' : 'nav-item'}
          onClick={() => setActiveTab('collection')}
        >
          ＋ <span>New Collection</span>
        </button>

        <button
          className={activeTab === 'tracking' ? 'nav-item active' : 'nav-item'}
          onClick={() => setActiveTab('tracking')}
        >
          ◎ <span>Track E-Waste</span>
        </button>
        <button
           className={ activeTab === 'network-map' ? 'nav-item active' : 'nav-item'}
          onClick={() => setActiveTab('network-map')}
        >
          ◎ <span>Network Map</span>
        </button>

        {currentUser?.role === 'user' && (
  <button
    className={
      activeTab === 'partner-register' ? 'nav-item active' : 'nav-item'
    }
    onClick={() => setActiveTab('partner-register')}
  >
    ＋ <span>Join as a Partner</span>
  </button>
)}


        {currentUser?.role === 'admin' && (
          <button
            className={activeTab === 'admin' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('admin')}
          >
            <span>🛡️</span>
            <span>Admin Verification</span>
          </button>
        )}

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <span>Platform interface</span>
          <small>DEMO</small>
        </div>
      </aside>
            {activeTab === 'partners' && (
        <section className="content-panel">
          <span className="eyebrow">COLLECTION NETWORK</span>
          <h2>Partner Coordination</h2>
          <p className="panel-description">
            Explore registered collection partners and their service capabilities.
          </p>

          <div className="partner-summary">
            <div>
              <span>REGISTERED PARTNERS</span>
              <h3>{partners.length}</h3>
            </div>
            <div>
              <span>ACTIVE PARTNERS</span>
              <h3>{partners.filter((p) => p.is_active === 1).length}</h3>
            </div>
          </div>

          <div className="partner-grid">
            {partners.map((partner) => (
              <div className="partner-card" key={partner.id}>
                <div className="partner-card-top">
                  <div className="module-icon">⌘</div>
                  <span className="partner-badge">
                    {partner.is_demo === 1 ? 'DEMO PARTNER' : 'REGISTERED'}
                  </span>
                </div>

                <h3>{partner.partner_name}</h3>
                <p className="partner-location">
                  {partner.city}, {partner.district}, {partner.state}
                </p>

                <div className="partner-details">
                  <div>
                    <span>ACCEPTED CATEGORIES</span>
                    <p>{partner.accepted_categories}</p>
                  </div>
                  <div>
                    <span>HANDLING CAPACITY</span>
                    <p>{partner.capacity} units</p>
                  </div>
                </div>

                <div className="partner-active">
                  <span className="status-dot" />
                  {partner.is_active === 1 ? 'Active' : 'Inactive'}
                </div>
              </div>
            ))}
          </div>

          {partners.length === 0 && (
            <p className="demo-note">No partners are currently registered.</p>
          )}

          <p className="demo-note">
            Demo partner records are illustrative and do not represent verified
            real-world collection services.
          </p>
        </section>
      )}
      {activeTab === 'network-map' && (
         <section className="content-panel">
           <NetworkMap />
         </section>
      )}

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">E-CYCLE VISION / INDIA</span>
            <h1>
              {activeTab === 'overview' && 'Overview'}
              {activeTab === 'collection' && 'Collection Management'}
              {activeTab === 'tracking' && 'E-Waste Tracking'}
              {activeTab === 'partners' && 'Partner Coordination'}
              {activeTab === 'partner-register' && 'Partner Registration'}
              {activeTab === 'admin' && 'Admin Verification'}
              {activeTab === 'network-map' && 'Network Map'}
            </h1>
          </div>

          <div className="topbar-right">
            <span className="live-indicator" />
            <span>DEMO ENVIRONMENT</span>
            <span>{currentUser?.full_name}</span>
            <button
              className="secondary-button"
              onClick={() => {
                setAuthToken(null)
                setCurrentUser(null)
              }}
            >
              Log out
            </button>
          </div>
        </header>

        {activeTab === 'admin' && currentUser?.role === 'admin' && (
          <AdminDashboard authToken={authToken!} />
        )}

        {activeTab === 'overview' && (
          <section>
            <div className="welcome-banner">
              <div>
                <span className="eyebrow">A SMARTER CIRCULAR FUTURE</span>
                <h2>
                  Give electronic waste
                  <br />
                  a responsible next life.
                </h2>
                <p>
                  Coordinate e-waste collection, connect with suitable partners
                  and follow every recorded movement.
                </p>
                <button
                  className="primary-button"
                  onClick={() => setActiveTab('collection')}
                >
                  Start a collection <span>→</span>
                </button>
              </div>

              <div className="banner-art">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <div className="earth">♻</div>
                <span className="art-label">RECYCLE · REUSE · RESTORE</span>
              </div>
            </div>

            <div className="section-heading">
              <div>
                <span className="eyebrow">PLATFORM MODULES</span>
                <h2>Manage your e-waste journey</h2>
              </div>
            </div>

            <div className="module-grid">
              <button
                className="module-card"
                onClick={() => setActiveTab('collection')}
              >
                <div className="module-icon">＋</div>
                <h3>Collection requests</h3>
                <p>
                  Submit household or institutional e-waste for coordinated
                  collection.
                </p>
                <span>CREATE REQUEST ↗</span>
              </button>

              <button
                className="module-card"
                onClick={() => setActiveTab('tracking')}
              >
                <div className="module-icon">◎</div>
                <h3>Traceability</h3>
                <p>
                  Follow recorded collection stages with a unique tracking ID.
                </p>
                <span>TRACK A REQUEST ↗</span>
              </button>

              <button className="module-card" onClick={loadPartners}>
                <div className="module-icon">⌘</div>
                <h3>Partner coordination</h3>
                <p>
                  Explore partner matching based on location, category and
                  capacity.
                </p>
                <span>EXPLORE PARTNERS ↗</span>
              </button>
            </div>

            <p className="demo-note">
              Demonstration platform · Partner and collection records shown
              here are not proof of real-world pickup or recycling.
            </p>
          </section>
        )}

        {activeTab === 'collection' && (
          <section className="content-panel">
            <span className="eyebrow">CONTRIBUTE TO A CIRCULAR ECONOMY</span>
            <h2>Submit a collection request</h2>
            <p className="panel-description">
              Provide the details of your electronic waste to create a
              traceable request.
            </p>

            <form onSubmit={submitRequest} className="collection-form">
              <label>
                Requester name
                <input
                  required
                  minLength={2}
                  value={form.requester_name}
                  onChange={(e) =>
                    updateForm('requester_name', e.target.value)
                  }
                  placeholder="Enter your name"
                />
              </label>

              <label>
                Requester type
                <select
                  value={form.requester_type}
                  onChange={(e) =>
                    updateForm('requester_type', e.target.value)
                  }
                >
                  <option>Household</option>
                  <option>Institution</option>
                  <option>Business</option>
                </select>
              </label>

              <label>
                Device category
                <select
                  value={form.device_category}
                  onChange={(e) =>
                    updateForm('device_category', e.target.value)
                  }
                >
                  <option>Mobile Phone</option>
                  <option>Laptop</option>
                  <option>Television</option>
                  <option>Computer</option>
                  <option>Printer</option>
                  <option>Other</option>
                </select>
              </label>

              <label>
                Quantity
                <input
                  type="number"
                  min="1"
                  required
                  value={form.quantity}
                  onChange={(e) =>
                    updateForm('quantity', Number(e.target.value))
                  }
                />
              </label>

              <label>
                Device condition
                <select
                  value={form.condition}
                  onChange={(e) =>
                    updateForm('condition', e.target.value)
                  }
                >
                  <option>Non-working</option>
                  <option>Working</option>
                  <option>Partially working</option>
                  <option>Damaged</option>
                </select>
              </label>

              <label>
                State
                <input
                  required
                  value={form.state}
                  onChange={(e) => updateForm('state', e.target.value)}
                  placeholder="e.g. Telangana"
                />
              </label>

              <label>
                District
                <input
                  required
                  value={form.district}
                  onChange={(e) => updateForm('district', e.target.value)}
                  placeholder="Enter district"
                />
              </label>

              <label>
                City
                <input
                  required
                  value={form.city}
                  onChange={(e) => updateForm('city', e.target.value)}
                  placeholder="Enter city"
                />
              </label>

              <label>
                PIN code
                <input
                  required
                  pattern="[1-9][0-9]{5}"
                  maxLength={6}
                  value={form.pincode}
                  onChange={(e) => updateForm('pincode', e.target.value)}
                  placeholder="6-digit PIN code"
                />
              </label>

              <label className="full-width">
                Additional description
                <textarea
                  value={form.description}
                  onChange={(e) => updateForm('description', e.target.value)}
                  placeholder="Add any useful details about the devices..."
                />
              </label>

              <button
                className="primary-button full-width"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Submitting...' : 'Submit collection request →'}
              </button>
            </form>

            {message && <div className="message-box">{message}</div>}

            {trackingId && (
              <div className="success-card">
                <span>YOUR TRACKING ID</span>
                <h3>{trackingId}</h3>
                <button
                  className="secondary-button"
                  onClick={() => setActiveTab('tracking')}
                >
                  Track this request →
                </button>
              </div>
            )}
          </section>
        )}
                {activeTab === 'tracking' && (
          <section className="content-panel">
            <span className="eyebrow">TRANSPARENT RECORDS</span>
            <h2>Track your e-waste</h2>
            <p className="panel-description">
              Enter the tracking ID generated when your collection request was submitted.
            </p>

            <div className="tracking-search">
              <input
                value={trackingId}
                onChange={(e) => setTrackingId(e.target.value)}
                placeholder="e.g. ECV-0A6FA67C87"
              />
              <button
                className="primary-button"
                onClick={trackRequest}
                disabled={loading}
              >
                {loading ? 'Searching...' : 'Track →'}
              </button>
            </div>

            <button
              className="primary-button"
              onClick={loadRecommendations}
              disabled={loading}
            >
              {loading ? 'Finding partners...' : 'Find Suitable Partners →'}
            </button>

            {recommendations.length > 0 && (
              <div className="recommendation-section">
                <div className="recommendation-heading">
                  <span className="eyebrow">MATCHING RESULTS</span>
                  <h3>Recommended Collection Partners</h3>
                  <p>
                    {recommendations.length} suitable partner(s) found for your request.
                  </p>
                </div>

                {recommendations.map((partner) => (
                  <div className="recommendation-card" key={partner.partner_id}>
                    <div className="recommendation-top">
                      <div>
                        <span className="partner-badge">
                          {partner.is_demo === 1 ? 'DEMO PARTNER' : 'PARTNER MATCH'}
                        </span>
                        <h3>{partner.partner_name}</h3>
                        <p>
                          {partner.city}, {partner.district}, {partner.state}
                        </p>
                      </div>

                      <div className="match-score">
                        <strong>
                          {partner.match_score ?? partner.matching_score ?? 0}
                        </strong>
                        <span>MATCH SCORE</span>
                      </div>
                    </div>

                    <div className="recommendation-capacity">
                      <span>HANDLING CAPACITY</span>
                      <strong>{partner.capacity} units</strong>
                    </div>

                    <div className="match-reasons">
                      <h4>Why this partner matches</h4>
                      {(partner.match_reasons ?? partner.reasons ?? []).map(
                        (reason: string, index: number) => (
                          <p key={index}>✓ {reason}</p>
                        )
                      )}
                    </div>

                    <p className="assigned-notice">
                      ✓ This partner is recommended based on your location,
                      device category and available capacity.
                      The platform admin will send a collection offer.
                    </p>
                  </div>
                ))}
              </div>
            )}

            {message && <div className="message-box">{message}</div>}

            {trackingData && (
              <div className="tracking-result">
                <div className="tracking-header">
                  <div>
                    <span className="eyebrow">TRACKING ID</span>
                    <h3>{trackingData.tracking_id}</h3>
                  </div>
                  <span className="current-status">
                    {trackingData.current_status}
                  </span>
                </div>

                <h3 className="timeline-title">Request history</h3>
                <div className="timeline">
                  {trackingData.history.map((item: any, index: number) => (
                    <div
                      className="timeline-item"
                      key={`${item.status}-${index}`}
                    >
                      <div className="timeline-marker" />
                      <div>
                        <h4>{item.status}</h4>
                        <p>{item.remarks}</p>
                        <small>
                          {new Date(item.updated_at).toLocaleString()}
                        </small>
                      </div>
                    </div>
                  ))}
                </div>

                <p className="demo-note">
                  This timeline reflects records entered into the demonstration system.
                  It does not independently verify physical collection or recycling.
                </p>
              </div>
            )}
          </section>
        )}

        {activeTab === 'partner-register' && (
          <section className="content-panel">
            <span className="eyebrow">GROW THE COLLECTION NETWORK</span>
            <h2>Join E-Cycle Vision</h2>
            <p className="panel-description">
              Register your collection centre or organisation to connect
              with e-waste collection opportunities.
            </p>

            <form onSubmit={submitPartnerApplication} className="collection-form">
              <label>
                Organisation / Collection Centre Name
                <input
                  required
                  minLength={2}
                  value={partnerForm.organisation_name}
                  onChange={(e) =>
                    updatePartnerForm('organisation_name', e.target.value)
                  }
                  placeholder="Enter organisation name"
                />
              </label>

              <label>
                Contact Person
                <input
                  required
                  value={partnerForm.contact_person}
                  onChange={(e) =>
                    updatePartnerForm('contact_person', e.target.value)
                  }
                  placeholder="Enter contact person"
                />
              </label>

              <label>
                Phone Number
                <input
                  required
                  type="tel"
                  minLength={10}
                  maxLength={15}
                  value={partnerForm.phone}
                  onChange={(e) =>
                    updatePartnerForm('phone', e.target.value)
                  }
                  placeholder="Enter phone number"
                />
              </label>

              <label>
                Email Address
                <input
                  required
                  type="email"
                  value={partnerForm.email}
                  onChange={(e) =>
                    updatePartnerForm('email', e.target.value)
                  }
                  placeholder="Enter email address"
                />
              </label>

              <label>
                Organisation Type
                <select
                  value={partnerForm.organisation_type}
                  onChange={(e) =>
                    updatePartnerForm('organisation_type', e.target.value)
                  }
                >
                  <option>Local Collection Centre</option>
                  <option>Waste Collection Agency</option>
                  <option>Authorized Recycler</option>
                  <option>Refurbisher</option>
                  <option>Other</option>
                </select>
              </label>

              <label>
                Accepted E-Waste Categories
                <input
                  required
                  value={partnerForm.accepted_categories}
                  onChange={(e) =>
                    updatePartnerForm('accepted_categories', e.target.value)
                  }
                  placeholder="e.g. Mobile Phone, Laptop, Television"
                />
              </label>

              <label>
                State
                <input
                  required
                  value={partnerForm.state}
                  onChange={(e) =>
                    updatePartnerForm('state', e.target.value)
                  }
                  placeholder="Enter state"
                />
              </label>

              <label>
                District
                <input
                  required
                  value={partnerForm.district}
                  onChange={(e) =>
                    updatePartnerForm('district', e.target.value)
                  }
                  placeholder="Enter district"
                />
              </label>

              <label>
                City
                <input
                  required
                  value={partnerForm.city}
                  onChange={(e) =>
                    updatePartnerForm('city', e.target.value)
                  }
                  placeholder="Enter city"
                />
              </label>

              <label>
                PIN Code
                <input
                  required
                  pattern="[1-9][0-9]{5}"
                  maxLength={6}
                  value={partnerForm.pincode}
                  onChange={(e) =>
                    updatePartnerForm('pincode', e.target.value)
                  }
                  placeholder="6-digit PIN code"
                />
              </label>
            <div className="full-width">
              <LocationPicker
                latitude={partnerForm.latitude}
                longitude={partnerForm.longitude}
                onLocationSelect={(latitude, longitude) => {
                   updatePartnerForm('latitude', latitude)
                   updatePartnerForm('longitude', longitude)
                  }}
                 />
              </div>

              <label>
                Handling Capacity (units)
                <input
                  required
                  type="number"
                  min="1"
                  value={partnerForm.capacity}
                  onChange={(e) =>
                    updatePartnerForm('capacity', Number(e.target.value))
                  }
                />
              </label>

              <label className="full-width">
                Authorization / Registration Details
                <textarea
                  value={partnerForm.authorization_details}
                  onChange={(e) =>
                    updatePartnerForm('authorization_details', e.target.value)
                  }
                  placeholder="Provide relevant authorization details, if applicable..."
                />
              </label>

              <button
                className="primary-button full-width"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Submitting Application...' : 'Submit Partner Application →'}
              </button>
            </form>

            <p className="demo-note">
              All applications are subject to verification. Registration does not
              automatically grant authorized recycler status or active partner access.
            </p>

            {message && <div className="message-box">{message}</div>}
          </section>
        )}
      </main>
    </div>
  )
}

export default App