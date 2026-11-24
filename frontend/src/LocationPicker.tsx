
import {
  MapContainer,
  TileLayer,
  Marker,
  useMapEvents
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './LocationPicker.css';

interface LocationPickerProps {
  latitude: number | null;
  longitude: number | null;
  onLocationSelect: (latitude: number, longitude: number) => void;
}

const selectedIcon = L.divIcon({
  className: 'selected-location-icon',
  html: '<div class="selected-location-pin">📍</div>',
  iconSize: [36, 36],
  iconAnchor: [18, 36]
});

function MapClickHandler({
  onLocationSelect
}: {
  onLocationSelect: (latitude: number, longitude: number) => void;
}) {
  useMapEvents({
    click(event) {
      onLocationSelect(
        Number(event.latlng.lat.toFixed(6)),
        Number(event.latlng.lng.toFixed(6))
      );
    }
  });

  return null;
}

export default function LocationPicker({
  latitude,
  longitude,
  onLocationSelect
}: LocationPickerProps) {
  const hasLocation = latitude !== null && longitude !== null;

  return (
    <div className="location-picker">
      <div className="location-picker-heading">
        <h3>Select Collection Centre Location</h3>
        <p>
          Zoom into your area and click the exact location of your
          organisation on the map.
        </p>
      </div>

      <MapContainer
        center={
          hasLocation
            ? [latitude, longitude]
            : [20.5937, 78.9629]
        }
        zoom={hasLocation ? 15 : 5}
        scrollWheelZoom
        className="location-picker-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapClickHandler onLocationSelect={onLocationSelect} />

        {hasLocation && (
          <Marker
            position={[latitude, longitude]}
            icon={selectedIcon}
          />
        )}
      </MapContainer>

      <div className="selected-location-details">
        {hasLocation ? (
          <>
            <strong>Location selected</strong>
            <p>Latitude: {latitude}</p>
            <p>Longitude: {longitude}</p>
          </>
        ) : (
          <p>Click on the map to select your collection centre.</p>
        )}
      </div>
    </div>
  );
}
