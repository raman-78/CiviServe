/**
 * Leaflet map for the locator (maps/locator prompt).
 *
 * Public OSM tiles — no key in the browser. Markers are pure data from the API;
 * the map never records the user's position beyond the anchor of the current
 * scan and holds nothing between renders. `CenterMarker` mirrors the shared
 * contract. The caller owns the search circle + attributionNote copy.
 */
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Circle, MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

import { formatDistanceKm } from "@/lib/formatters";
import type { CenterMarker, GeoPoint } from "@/types";

interface CenterMapProps {
  centers: CenterMarker[];
  anchor?: GeoPoint | null;
  radiusKm?: number;
  onSelect?: (id: string) => void;
}

const INDIA_CENTER: [number, number] = [22.85, 79.6569];
const ZOOM_ANCHOR = 10;

// Plain divIcon (no Vite asset hassle): a pin coloured by verification state.
const pin = (name: string, verified: boolean) =>
  L.divIcon({
    className: "center-marker",
    html: `<div class="center-marker-pin${verified ? " center-marker-pin--verified" : ""}" title="${name.replace(/"/g, "&quot;")}"></div>`,
    iconSize: [26, 34],
    iconAnchor: [13, 34],
    popupAnchor: [0, -30],
  });

const userDot = () =>
  L.divIcon({
    className: "center-marker",
    html: '<div class="center-marker-dot"></div>',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

export function CenterMap({ centers, anchor, radiusKm, onSelect }: CenterMapProps) {
  const position: [number, number] =
    anchor?.lat !== undefined && anchor?.lng !== undefined
      ? [anchor.lat, anchor.lng]
      : INDIA_CENTER;

  return (
    <MapContainer
      key={`${position[0].toFixed(4)},${position[1].toFixed(4)}`}
      center={position}
      zoom={ZOOM_ANCHOR}
      scrollWheelZoom
      className="h-[360px] w-full rounded-xl border"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {radiusKm !== undefined && radiusKm > 0 && anchor?.lat !== undefined && anchor?.lng !== undefined ? (
        <Circle
          center={[anchor.lat, anchor.lng]}
          radius={radiusKm * 1000}
          pathOptions={{ color: "#0f766e", fillColor: "#14b8a6", fillOpacity: 0.1, weight: 1 }}
        />
      ) : null}
      {anchor?.lat !== undefined && anchor?.lng !== undefined ? (
        <Marker position={[anchor.lat, anchor.lng]} icon={userDot()} zIndexOffset={1000} />
      ) : null}
      {centers.map((center) => (
        <Marker
          key={center.id}
          position={[center.lat, center.lng]}
          icon={pin(center.name, center.verified)}
        >
          <Popup>
            <div className="space-y-1">
              <p className="text-sm font-semibold">{center.name}</p>
              {center.distanceKm !== undefined ? (
                <p className="text-xs text-muted-foreground">
                  {formatDistanceKm(center.distanceKm)}
                </p>
              ) : null}
              {onSelect ? (
                <button
                  type="button"
                  onClick={() => onSelect(center.id)}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  View details
                </button>
              ) : null}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}