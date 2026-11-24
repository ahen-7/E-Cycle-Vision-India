
import { useEffect, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

type CollectionRequest = {
  id: number
  offer_id: number
  tracking_id: string
  requester_name: string
  device_category: string
  quantity: number
  condition: string
  state: string
  district: string
  city: string
  pincode: string
  status: string
  offer_status: string
  created_at: string | null
}

type Props = {
  authToken: string
  fullName: string
}

function PartnerDashboard({ authToken, fullName }: Props) {
  const [requests, setRequests] = useState<CollectionRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [processing, setProcessing] = useState<number | null>(null)

  const loadRequests = async () => {
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/partner/requests`, {
        headers: { Authorization: `Bearer ${authToken}` }
      })

      const data = await response.json()

      if (!response.ok) throw new Error(data.detail || 'Unable to load requests')

      setRequests(data.requests || [])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRequests()
  }, [authToken])

  const respondToOffer = async (
    offerId: number,
    decision: 'accept' | 'decline'
  ) => {
    setProcessing(offerId)
    setMessage('')

    try {
      const response = await fetch(
        `${API}/partner/offers/${offerId}/respond?decision=${decision}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${authToken}` }
        }
      )

      const data = await response.json()

      if (!response.ok) throw new Error(data.detail || 'Action failed')

      setMessage(data.message)
      await loadRequests()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Something went wrong')
    } finally {
      setProcessing(null)
    }
  }

  const pending = requests.filter(item => item.offer_status === 'Offered').length
  const accepted = requests.filter(item => item.offer_status === 'Accepted').length
  const declined = requests.filter(item => item.offer_status === 'Declined').length

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0b1220',
      color: '#e5e7eb',
      padding: '32px',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <p style={{ color: '#34d399', letterSpacing: '2px' }}>
            E-CYCLE VISION INDIA
          </p>
          <h1>Partner Dashboard</h1>
          <p>Welcome, {fullName}</p>
        </div>

        <button onClick={loadRequests} style={buttonStyle}>
          Refresh Requests
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '16px',
        margin: '32px 0'
      }}>
        <Stat title="Total Offers" value={requests.length} />
        <Stat title="Awaiting Response" value={pending} />
        <Stat title="Accepted" value={accepted} />
        <Stat title="Declined" value={declined} />
      </div>

      <h2>Collection Offers</h2>

      {loading && <p>Loading offers...</p>}
      {message && <p style={{ color: '#34d399' }}>{message}</p>}

      {!loading && requests.length === 0 && (
        <div style={panelStyle}>
          <h3>No offers yet</h3>
          <p>New collection offers will appear here.</p>
        </div>
      )}

      {!loading && requests.length > 0 && (
        <div style={{ display: 'grid', gap: '16px' }}>
          {requests.map(item => (
            <div key={item.offer_id} style={panelStyle}>
              <h3>{item.device_category} Collection</h3>
              <p><b>Tracking ID:</b> {item.tracking_id}</p>
              <p><b>Quantity:</b> {item.quantity}</p>
              <p><b>Condition:</b> {item.condition}</p>
              <p><b>Location:</b> {item.city}, {item.district}, {item.pincode}</p>
              <p><b>Offer status:</b> {item.offer_status}</p>

              {item.offer_status === 'Offered' && (
                <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                  <button
                    disabled={processing !== null}
                    onClick={() => respondToOffer(item.offer_id, 'accept')}
                    style={buttonStyle}
                  >
                    {processing === item.offer_id ? 'Processing...' : 'Accept'}
                  </button>

                  <button
                    disabled={processing !== null}
                    onClick={() => respondToOffer(item.offer_id, 'decline')}
                    style={{ ...buttonStyle, background: '#dc2626' }}
                  >
                    Decline
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ title, value }: { title: string; value: number }) {
  return (
    <div style={panelStyle}>
      <p style={{ color: '#9ca3af' }}>{title}</p>
      <h2 style={{ color: '#34d399', fontSize: '30px' }}>{value}</h2>
    </div>
  )
}

const panelStyle: React.CSSProperties = {
  background: '#151f30',
  border: '1px solid #293548',
  borderRadius: '12px',
  padding: '20px'
}

const buttonStyle: React.CSSProperties = {
  background: '#059669',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  padding: '12px 20px',
  cursor: 'pointer'
}

export default PartnerDashboard
