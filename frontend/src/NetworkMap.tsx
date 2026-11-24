
import { useEffect, useMemo, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './NetworkMap.css';

interface Partner {
  id: number;
  partner_name: string;
  state: string;
  district: string;
  city: string;
  pincode: string;
  latitude: number | null;
  longitude: number | null;
  accepted_categories: string;
  capacity: number;
  is_active: number;
  is_demo: number;
}

interface NetworkMapProps {
  apiBaseUrl?: string;
}

const partnerIcon = L.divIcon({
  className: 'partner-map-icon',
  html: '<div class="map-pin"><span>♻</span></div>',
  iconSize: [36, 42],
  iconAnchor: [18, 42],
  popupAnchor: [0, -38]
});

export default function NetworkMap({
  apiBaseUrl = 'http://127.0.0.1:8000'
}: NetworkMapProps) {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');

  useEffect(() => {
    const loadPartners = async () => {
      try {
        setLoading(true);
        setError('');

        const response = await fetch(`${apiBaseUrl}/partners`);

        if (!response.ok) {
          throw new Error('Unable to load collection partners.');
        }

        const data = await response.json();
        setPartners(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Something went wrong while loading the map.'
        );
      } finally {
        setLoading(false);
      }
    };

    loadPartners();
  }, [apiBaseUrl]);

  const mappedPartners = useMemo(
    () =>
      partners.filter(
        partner =>
          partner.is_active === 1 &&
          typeof partner.latitude === 'number' &&
          typeof partner.longitude === 'number' &&
          Number.isFinite(partner.latitude) &&
          Number.isFinite(partner.longitude) &&
          partner.latitude >= -90 &&
          partner.latitude <= 90 &&
          partner.longitude >= -180 &&
          partner.longitude <= 180
      ),
    [partners]
  );

  const categories = useMemo(() => {
    const all = partners.flatMap(partner =>
      partner.accepted_categories
        .split(',')
        .map(item => item.trim())
        .filter(Boolean)
    );

    return ['All', ...Array.from(new Set(all))];
  }, [partners]);

  const visiblePartners = useMemo(() => {
    return mappedPartners.filter(partner => {
      const searchText =
        `${partner.partner_name} ${partner.city} ${partner.district} ${partner.state}`
          .toLowerCase();

      const matchesSearch = searchText.includes(search.toLowerCase());

      const partnerCategories = partner.accepted_categories
        .split(',')
        .map(item => item.trim().toLowerCase());

      const matchesCategory =
        category === 'All' ||
        partnerCategories.includes(category.toLowerCase());

      return matchesSearch && matchesCategory;
    });
  }, [mappedPartners, search, category]);

  const mapCenter: [number, number] =
    visiblePartners.length > 0
      ? [
          visiblePartners[0].latitude!,
          visiblePartners[0].longitude!
        ]
      : [20.5937, 78.9629];

  return (
    <div className="network-map-page">
      <div className="network-map-heading">
        <div>
          <h2>Collection Network Map</h2>
          <p>
            Explore active e-waste collection partners across India.
          </p>
        </div>

        <div className="network-map-count">
          <strong>{mappedPartners.length}</strong>
          <span>Mapped partners</span>
        </div>
      </div>

      <div className="network-map-filters">
        <input
          type="text"
          placeholder="Search partner, city or state..."
          value={search}
          onChange={event => setSearch(event.target.value)}
        />

        <select
          value={category}
          onChange={event => setCategory(event.target.value)}
        >
          {categories.map(item => (
            <option key={item} value={item}>
              {item === 'All' ? 'All categories' : item}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="network-map-message">
          Loading collection partners...
        </div>
      )}

      {error && (
        <div className="network-map-error">
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="network-map-legend">
            <span className="legend-pin">♻</span>
            <span>Active collection partner</span>
            <span className="demo-label">DEMO</span>
            <span>Demo partner</span>
          </div>

          <div className="network-map-container">
            <MapContainer
              key={`${mapCenter[0]}-${mapCenter[1]}`}
              center={mapCenter}
              zoom={5}
              scrollWheelZoom={true}
              className="network-leaflet-map"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {visiblePartners.map(partner => (
                <Marker
                  key={partner.id}
                  position={[
                    partner.latitude!,
                    partner.longitude!
                  ]}
                  icon={partnerIcon}
                >
                  <Popup>
                    <div className="partner-map-popup">
                      <h3>{partner.partner_name}</h3>

                      {partner.is_demo === 1 && (
                        <span className="popup-demo">
                          DEMO PARTNER
                        </span>
                      )}

                      <p>
                        {partner.city}, {partner.district}
                      </p>
                      <p>
                        {partner.state} - {partner.pincode}
                      </p>
                      <p>
                        <strong>Categories:</strong>{' '}
                        {partner.accepted_categories}
                      </p>
                      <p>
                        <strong>Capacity:</strong> {partner.capacity}
                      </p>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>

          <div className="network-map-footer">
            Showing {visiblePartners.length} of {mappedPartners.length}{' '}
            mapped partners.

            {mappedPartners.length === 0 && (
              <p>
                No partner coordinates are available yet. Partners must
                submit their location before appearing on the map.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
