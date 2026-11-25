
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

type RecyclerPriceOffer = {
  id: number
  recycler_id: number
  material_category: string
  price_per_kg: number
  minimum_quantity_kg: number | null
  valid_until: string | null
  status: string
  created_at: string | null
}

type Batch = {
  id: number
  batch_code: string
  material_category: string
  total_quantity: number
  total_weight: number | null
  status: string
}

type ComparisonOffer = {
  offer_id: number
  recycler_id: number
  recycler_name: string
  city: string
  material_category: string
  price_per_kg: number
  minimum_quantity_kg: number | null
  batch_weight_kg: number
  estimated_value: number
  valid_until: string | null
}

type Handover = {
  id: number
  batch_id: number
  aggregator_id: number
  recycler_id: number
  price_offer_id: number | null
  agreed_price_per_kg: number | null
  estimated_amount: number | null
  final_amount: number | null
  payment_status: string
  payment_reference: string | null
  paid_at: string | null
  status: string
  dispatched_weight: number | null
  received_weight: number | null
  dispatched_at: string | null
  received_at: string | null
  remarks: string | null
}

type Props = {
  authToken: string
  fullName: string
  role: string
}

function PartnerDashboard({ authToken, fullName, role }: Props) {
  const [requests, setRequests] = useState<CollectionRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [processing, setProcessing] = useState<number | null>(null)

  const [priceOffers, setPriceOffers] = useState<RecyclerPriceOffer[]>([])
  const [offerLoading, setOfferLoading] = useState(false)
  const [offerSubmitting, setOfferSubmitting] = useState(false)

  const [batches, setBatches] = useState<Batch[]>([])
  const [batchLoading, setBatchLoading] = useState(false)

  const [comparisonOffers, setComparisonOffers] = useState<
    Record<number, ComparisonOffer[]>
  >({})
  const [comparingBatch, setComparingBatch] = useState<number | null>(null)

  const [selectedOffers, setSelectedOffers] = useState<
    Record<number, ComparisonOffer>
  >({})

  const [handoverProcessing, setHandoverProcessing] = useState<number | null>(null)

  // Payment tracking
  const [handovers, setHandovers] = useState<Handover[]>([])
  const [handoverLoading, setHandoverLoading] = useState(false)
  const [paymentProcessing, setPaymentProcessing] = useState<number | null>(null)
  const [paymentReferences, setPaymentReferences] = useState<
    Record<number, string>
  >({})

  const [offerForm, setOfferForm] = useState({
    material_category: 'Mixed E-Waste',
    price_per_kg: '',
    minimum_quantity_kg: '',
    valid_until: ''
  })

  const headers = {
    Authorization: `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  }

  // Load collection requests
  const loadRequests = async () => {
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/partner/requests`, {
        headers
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load requests')
      }

      setRequests(data.requests || [])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load requests')
    } finally {
      setLoading(false)
    }
  }

  // Load recycler's published price offers
  const loadPriceOffers = async () => {
    setOfferLoading(true)

    try {
      const response = await fetch(`${API}/recycler/price-offers`, {
        headers
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load price offers')
      }

      setPriceOffers(Array.isArray(data) ? data : data.offers || [])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load price offers')
    } finally {
      setOfferLoading(false)
    }
  }

  // Load aggregator batches
  const loadBatches = async () => {
    setBatchLoading(true)

    try {
      const response = await fetch(`${API}/aggregator/batches`, {
        headers
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load material batches')
      }

      setBatches(Array.isArray(data) ? data : [])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load batches')
    } finally {
      setBatchLoading(false)
    }
  }

  // Load aggregator handovers and payment records
  const loadHandovers = async () => {
    setHandoverLoading(true)

    try {
      const response = await fetch(`${API}/aggregator/handovers`, {
        headers
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load handovers')
      }

      setHandovers(Array.isArray(data) ? data : [])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load handovers')
    } finally {
      setHandoverLoading(false)
    }
  }

  useEffect(() => {
    if (role === 'recycler') {
      loadPriceOffers()
    } else if (role === 'aggregator' || role === 'partner') {
      loadRequests()
      loadBatches()

      if (role === 'aggregator') {
        loadHandovers()
      }
    }
  }, [authToken, role])

  // Publish recycler price offer
  const createPriceOffer = async () => {
    setOfferSubmitting(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/recycler/price-offers`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          material_category: offerForm.material_category,
          price_per_kg: Number(offerForm.price_per_kg),
          minimum_quantity_kg: offerForm.minimum_quantity_kg
            ? Number(offerForm.minimum_quantity_kg)
            : null,
          valid_until: offerForm.valid_until
            ? new Date(offerForm.valid_until).toISOString()
            : null
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to publish offer')
      }

      setMessage('Price offer published successfully!')

      setOfferForm({
        material_category: 'Mixed E-Waste',
        price_per_kg: '',
        minimum_quantity_kg: '',
        valid_until: ''
      })

      await loadPriceOffers()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to publish offer')
    } finally {
      setOfferSubmitting(false)
    }
  }

  // Compare recycler offers for a batch
  const compareOffers = async (batchId: number) => {
    setComparingBatch(batchId)
    setMessage('')

    try {
      const response = await fetch(
        `${API}/aggregator/batches/${batchId}/price-offers`,
        { headers }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to compare offers')
      }

      setComparisonOffers(prev => ({
        ...prev,
        [batchId]: data.offers || []
      }))

      setSelectedOffers(prev => {
        const updated = { ...prev }
        delete updated[batchId]
        return updated
      })

      if (!data.offers?.length) {
        setMessage('No matching recycler offers found for this batch.')
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Comparison failed')
    } finally {
      setComparingBatch(null)
    }
  }

  // Select recycler offer
  const selectOffer = (batchId: number, offer: ComparisonOffer) => {
    setSelectedOffers(prev => ({
      ...prev,
      [batchId]: offer
    }))

    setMessage(`Selected ${offer.recycler_name} at ₹${offer.price_per_kg}/kg`)
  }

  // Create handover with selected recycler price offer
  const createHandover = async (batchId: number, offer: ComparisonOffer) => {
    setHandoverProcessing(batchId)
    setMessage('')

    try {
      const response = await fetch(
        `${API}/aggregator/batches/${batchId}/handover`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            recycler_id: offer.recycler_id,
            price_offer_id: offer.offer_id,
            remarks: `Selected recycler offer at ₹${offer.price_per_kg}/kg. Estimated value ₹${offer.estimated_value}.`
          })
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to create handover')
      }

      setMessage(
        `Handover created successfully! Handover ID: ${data.id ?? 'Created'}`
      )

      setSelectedOffers(prev => {
        const updated = { ...prev }
        delete updated[batchId]
        return updated
      })

      await Promise.all([loadBatches(), loadHandovers()])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Handover failed')
    } finally {
      setHandoverProcessing(null)
    }
  }

  // Record payment after recycler confirms received material
  const markPaymentPaid = async (handoverId: number) => {
    setPaymentProcessing(handoverId)
    setMessage('')

    try {
      const response = await fetch(
        `${API}/aggregator/handovers/${handoverId}/mark-paid`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            payment_reference: paymentReferences[handoverId]?.trim() || null
          })
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to record payment')
      }

      setMessage(`Payment for handover #${handoverId} recorded successfully.`)

      setPaymentReferences(prev => ({
        ...prev,
        [handoverId]: ''
      }))

      await loadHandovers()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Payment update failed')
    } finally {
      setPaymentProcessing(null)
    }
  }

  // Accept or decline collection offer
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
          headers: {
            Authorization: `Bearer ${authToken}`
          }
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Action failed')
      }

      setMessage(data.message)
      await loadRequests()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Action failed')
    } finally {
      setProcessing(null)
    }
  }

  const pending = requests.filter(
    item => item.offer_status === 'Offered'
  ).length

  const accepted = requests.filter(
    item => item.offer_status === 'Accepted'
  ).length

  const declined = requests.filter(
    item => item.offer_status === 'Declined'
  ).length

  const pendingPayments = handovers.filter(
    item => item.status === 'Received' && item.payment_status !== 'Paid'
  ).length

  const completedPayments = handovers.filter(
    item => item.payment_status === 'Paid'
  ).length

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return 'Not available'

    return `₹${Number(amount).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

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

          <h1>
            {role === 'recycler'
              ? 'Recycler Dashboard'
              : role === 'aggregator'
                ? 'Aggregator Dashboard'
                : 'Partner Dashboard'}
          </h1>

          <p>Welcome, {fullName}</p>
        </div>

        <button
          onClick={() => {
            if (role === 'recycler') {
              loadPriceOffers()
            } else {
              loadRequests()
              loadBatches()

              if (role === 'aggregator') {
                loadHandovers()
              }
            }
          }}
          style={buttonStyle}
        >
          Refresh Dashboard
        </button>
      </div>

      {message && (
        <div style={{
          ...panelStyle,
          marginTop: '20px',
          color: '#34d399'
        }}>
          {message}
        </div>
      )}

      {/* RECYCLER DASHBOARD */}
      {role === 'recycler' && (
        <>
          <div style={panelStyle}>
            <h2>Publish Recycler Price Offer</h2>

            <div style={{
              display: 'grid',
              gap: '14px',
              maxWidth: '500px'
            }}>
              <label>
                Material Category
                <select
                  value={offerForm.material_category}
                  onChange={e => setOfferForm({
                    ...offerForm,
                    material_category: e.target.value
                  })}
                  style={inputStyle}
                >
                  <option>Mixed E-Waste</option>
                  <option>Mobile Phones</option>
                  <option>Laptops</option>
                  <option>Computers</option>
                  <option>Printed Circuit Boards</option>
                  <option>Batteries</option>
                  <option>Cables</option>
                </select>
              </label>

              <label>
                Price per kg (₹)
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={offerForm.price_per_kg}
                  onChange={e => setOfferForm({
                    ...offerForm,
                    price_per_kg: e.target.value
                  })}
                  style={inputStyle}
                  placeholder="Example: 35"
                />
              </label>

              <label>
                Minimum Quantity (kg)
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={offerForm.minimum_quantity_kg}
                  onChange={e => setOfferForm({
                    ...offerForm,
                    minimum_quantity_kg: e.target.value
                  })}
                  style={inputStyle}
                  placeholder="Optional"
                />
              </label>

              <label>
                Offer Valid Until
                <input
                  type="datetime-local"
                  value={offerForm.valid_until}
                  onChange={e => setOfferForm({
                    ...offerForm,
                    valid_until: e.target.value
                  })}
                  style={inputStyle}
                />
              </label>

              <button
                onClick={createPriceOffer}
                disabled={
                  offerSubmitting ||
                  !offerForm.price_per_kg ||
                  Number(offerForm.price_per_kg) <= 0
                }
                style={buttonStyle}
              >
                {offerSubmitting ? 'Publishing...' : 'Publish Price Offer'}
              </button>
            </div>
          </div>

          <h2 style={{ marginTop: '30px' }}>My Published Price Offers</h2>

          {offerLoading && <p>Loading price offers...</p>}

          {!offerLoading && priceOffers.length === 0 && (
            <div style={panelStyle}>No price offers published yet.</div>
          )}

          {priceOffers.map(offer => (
            <div key={offer.id} style={{ ...panelStyle, marginTop: '14px' }}>
              <h3>{offer.material_category}</h3>
              <p><b>Price:</b> ₹{offer.price_per_kg}/kg</p>
              <p>
                <b>Minimum quantity:</b>{' '}
                {offer.minimum_quantity_kg ?? 'Not specified'} kg
              </p>
              <p><b>Status:</b> {offer.status}</p>
              <p>
                <b>Valid until:</b>{' '}
                {offer.valid_until
                  ? new Date(offer.valid_until).toLocaleString()
                  : 'No expiry specified'}
              </p>
            </div>
          ))}
        </>
      )}

      {/* AGGREGATOR DASHBOARD */}
      {role === 'aggregator' && (
        <>
          {/* RECYCLER PRICE COMPARISON */}
          <section style={{ marginTop: '32px' }}>
            <h2>Recycler Price Comparison</h2>

            <p style={{ color: '#9ca3af' }}>
              Compare verified recycler offers for your material batches.
            </p>

            {batchLoading && <p>Loading material batches...</p>}

            {!batchLoading && batches.length === 0 && (
              <div style={panelStyle}>
                <h3>No material batches available</h3>
                <p>Create a batch after recording collected material weights.</p>
              </div>
            )}

            {batches.map(batch => (
              <div key={batch.id} style={{
                ...panelStyle,
                marginTop: '18px'
              }}>
                <h3>{batch.batch_code}</h3>

                <p><b>Material:</b> {batch.material_category}</p>
                <p><b>Quantity:</b> {batch.total_quantity}</p>
                <p><b>Weight:</b> {batch.total_weight ?? 'Not recorded'} kg</p>
                <p><b>Status:</b> {batch.status}</p>

                {['Preparing', 'Ready'].includes(batch.status) && (
                  <button
                    disabled={
                      comparingBatch === batch.id ||
                      !batch.total_weight ||
                      batch.total_weight <= 0
                    }
                    onClick={() => compareOffers(batch.id)}
                    style={buttonStyle}
                  >
                    {comparingBatch === batch.id
                      ? 'Comparing...'
                      : 'Compare Recycler Prices'}
                  </button>
                )}

                {comparisonOffers[batch.id] && (
                  <div style={{ marginTop: '20px' }}>
                    <h3>Available Recycler Offers</h3>

                    {comparisonOffers[batch.id].length === 0 && (
                      <p>No matching offers available.</p>
                    )}

                    {comparisonOffers[batch.id].map(offer => {
                      const selected =
                        selectedOffers[batch.id]?.offer_id === offer.offer_id

                      return (
                        <div key={offer.offer_id} style={{
                          ...panelStyle,
                          marginTop: '12px',
                          border: selected
                            ? '2px solid #34d399'
                            : '1px solid #293548'
                        }}>
                          <h3>{offer.recycler_name}</h3>
                          <p><b>Location:</b> {offer.city}</p>
                          <p><b>Price per kg:</b> ₹{offer.price_per_kg}</p>
                          <p><b>Batch weight:</b> {offer.batch_weight_kg} kg</p>
                          <p>
                            <b>Minimum quantity:</b>{' '}
                            {offer.minimum_quantity_kg ?? 'No minimum'} kg
                          </p>

                          <h2 style={{ color: '#34d399' }}>
                            Estimated Value:{' '}
                            {formatCurrency(offer.estimated_value)}
                          </h2>

                          <p>
                            <b>Valid until:</b>{' '}
                            {offer.valid_until
                              ? new Date(offer.valid_until).toLocaleString()
                              : 'No expiry'}
                          </p>

                          <button
                            onClick={() => selectOffer(batch.id, offer)}
                            style={{
                              ...buttonStyle,
                              background: selected ? '#047857' : '#2563eb'
                            }}
                          >
                            {selected ? '✓ Offer Selected' : 'Select This Offer'}
                          </button>

                          {selected && (
                            <button
                              disabled={handoverProcessing === batch.id}
                              onClick={() => createHandover(batch.id, offer)}
                              style={{
                                ...buttonStyle,
                                display: 'block',
                                marginTop: '12px',
                                width: '100%'
                              }}
                            >
                              {handoverProcessing === batch.id
                                ? 'Creating Handover...'
                                : 'Confirm & Create Handover'}
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </section>

          {/* HANDOVER AND PAYMENT TRACKING */}
          <section style={{ marginTop: '40px' }}>
            <h2>Handover & Payment Tracking</h2>

            <p style={{ color: '#9ca3af' }}>
              Track dispatched batches, recycler-confirmed weights, and payment
              records in one place.
            </p>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '16px',
              margin: '20px 0'
            }}>
              <Stat title="Total Handovers" value={handovers.length} />
              <Stat title="Awaiting Payment" value={pendingPayments} />
              <Stat title="Payments Recorded" value={completedPayments} />
            </div>

            {handoverLoading && <p>Loading handover records...</p>}

            {!handoverLoading && handovers.length === 0 && (
              <div style={panelStyle}>
                <h3>No handovers yet</h3>
                <p>
                  Once you confirm a recycler for a material batch, its handover
                  record will appear here.
                </p>
              </div>
            )}

            {handovers.map(handover => (
              <div key={handover.id} style={{
                ...panelStyle,
                marginTop: '16px'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '10px'
                }}>
                  <h3>Handover #{handover.id}</h3>

                  <span style={{
                    background: handover.payment_status === 'Paid'
                      ? '#065f46'
                      : '#78350f',
                    color: '#fff',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '13px'
                  }}>
                    Payment: {handover.payment_status || 'Pending'}
                  </span>
                </div>

                <p><b>Batch ID:</b> {handover.batch_id}</p>
                <p><b>Recycler ID:</b> {handover.recycler_id}</p>
                <p><b>Handover status:</b> {handover.status}</p>

                <div style={{
                  background: '#0b1220',
                  borderRadius: '10px',
                  padding: '16px',
                  marginTop: '14px'
                }}>
                  <h4 style={{ marginTop: 0 }}>Weight & Value Details</h4>

                  <p>
                    <b>Dispatched weight:</b>{' '}
                    {handover.dispatched_weight ?? 'Not recorded'} kg
                  </p>

                  <p>
                    <b>Recycler-confirmed weight:</b>{' '}
                    {handover.received_weight ?? 'Awaiting confirmation'} kg
                  </p>

                  <p>
                    <b>Agreed price:</b>{' '}
                    {handover.agreed_price_per_kg !== null
                      ? `₹${handover.agreed_price_per_kg}/kg`
                      : 'Not available'}
                  </p>

                  <p>
                    <b>Estimated amount:</b>{' '}
                    {formatCurrency(handover.estimated_amount)}
                  </p>

                  <h3 style={{ color: '#34d399' }}>
                    Final payment: {formatCurrency(handover.final_amount)}
                  </h3>

                  <p>
                    <b>Received on:</b>{' '}
                    {handover.received_at
                      ? new Date(handover.received_at).toLocaleString()
                      : 'Awaiting recycler confirmation'}
                  </p>
                </div>

                {handover.payment_status === 'Paid' ? (
                  <div style={{
                    marginTop: '16px',
                    padding: '14px',
                    borderRadius: '8px',
                    background: '#064e3b',
                    border: '1px solid #059669'
                  }}>
                    <h4 style={{ color: '#6ee7b7', marginTop: 0 }}>
                      ✓ Payment Recorded
                    </h4>

                    <p>
                      <b>Amount:</b> {formatCurrency(handover.final_amount)}
                    </p>

                    <p>
                      <b>Payment reference:</b>{' '}
                      {handover.payment_reference || 'Not provided'}
                    </p>

                    <p>
                      <b>Payment date:</b>{' '}
                      {handover.paid_at
                        ? new Date(handover.paid_at).toLocaleString()
                        : 'Not available'}
                    </p>
                  </div>
                ) : handover.status === 'Received' ? (
                  <div style={{ marginTop: '18px' }}>
                    <h4>Record Payment</h4>

                    <p style={{ color: '#9ca3af' }}>
                      Enter the optional transaction reference after completing
                      the payment outside this platform.
                    </p>

                    <label>
                      Transaction Reference (Optional)
                      <input
                        type="text"
                        value={paymentReferences[handover.id] || ''}
                        onChange={e => setPaymentReferences(prev => ({
                          ...prev,
                          [handover.id]: e.target.value
                        }))}
                        placeholder="Enter UPI / bank reference"
                        style={inputStyle}
                      />
                    </label>

                    <button
                      disabled={
                        paymentProcessing === handover.id ||
                        !handover.final_amount ||
                        handover.final_amount <= 0
                      }
                      onClick={() => markPaymentPaid(handover.id)}
                      style={{
                        ...buttonStyle,
                        marginTop: '12px',
                        width: '100%'
                      }}
                    >
                      {paymentProcessing === handover.id
                        ? 'Recording Payment...'
                        : '✓ Mark Payment as Paid'}
                    </button>
                  </div>
                ) : (
                  <p style={{
                    color: '#fbbf24',
                    marginTop: '16px'
                  }}>
                    Payment can be recorded after the recycler confirms receipt
                    of the material.
                  </p>
                )}
              </div>
            ))}
          </section>
        </>
      )}

      {/* COLLECTION REQUESTS */}
      {role !== 'recycler' && (
        <>
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

          {!loading && requests.length === 0 && (
            <div style={panelStyle}>
              <h3>No offers yet</h3>
              <p>New collection offers will appear here.</p>
            </div>
          )}

          {requests.map(item => (
            <div key={item.offer_id} style={{
              ...panelStyle,
              marginTop: '16px'
            }}>
              <h3>{item.device_category} Collection</h3>
              <p><b>Tracking ID:</b> {item.tracking_id}</p>
              <p><b>Quantity:</b> {item.quantity}</p>
              <p><b>Condition:</b> {item.condition}</p>
              <p>
                <b>Location:</b> {item.city}, {item.district}, {item.pincode}
              </p>
              <p><b>Offer status:</b> {item.offer_status}</p>

              {item.offer_status === 'Offered' && (
                <div style={{
                  display: 'flex',
                  gap: '12px',
                  marginTop: '16px'
                }}>
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
        </>
      )}
    </div>
  )
}

function Stat({
  title,
  value
}: {
  title: string
  value: number
}) {
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
  padding: '20px',
  marginBottom: '12px'
}

const buttonStyle: React.CSSProperties = {
  background: '#059669',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  padding: '12px 20px',
  cursor: 'pointer'
}

const inputStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  boxSizing: 'border-box',
  marginTop: '8px',
  padding: '12px',
  borderRadius: '8px',
  border: '1px solid #293548',
  background: '#0b1220',
  color: '#e5e7eb'
}

export default PartnerDashboard
