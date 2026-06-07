import { useState, useCallback, useRef, useEffect } from 'react'
import Map, { Source, Layer, Popup } from 'react-map-gl/maplibre'
import type { MapLayerMouseEvent, MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import type * as GeoJSON from 'geojson'
import type { Field, AnomalyZone, FieldMarker } from '../../types'
import type { LayerType } from '../../store/useAppStore'
import useAppStore from '../../store/useAppStore'
import { API_BASE } from '../../api/client'

const OSM_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: 'raster' as const,
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster' as const, source: 'osm' }],
}

interface Props {
  field: Field | null
  flightId: string | null
  activeLayer: LayerType
  orthoBbox: [number, number, number, number] | null
  anomalies: AnomalyZone[]
  markers?: FieldMarker[]
  markerMode?: boolean
  onAddMarker?: (lat: number, lng: number) => void
}

export default function MapView({
  field, flightId, activeLayer, orthoBbox, anomalies,
  markers = [], markerMode, onAddMarker,
}: Props) {
  const [anomalyPopup, setAnomalyPopup] = useState<{ lng: number; lat: number } | null>(null)
  const [markerPopup, setMarkerPopup] = useState<{ lng: number; lat: number; note: string | null } | null>(null)
  const mapRef = useRef<MapRef>(null)
  const mapLoaded = useRef(false)

  const { zoomToBounds, setZoomToBounds } = useAppStore()

  const fitToBbox = useCallback((bbox: [number, number, number, number]) => {
    if (!mapRef.current) return
    const [west, south, east, north] = bbox
    mapRef.current.fitBounds([[west, south], [east, north]], { padding: 40, duration: 800 })
  }, [])

  useEffect(() => {
    if (!orthoBbox || !mapLoaded.current) return
    fitToBbox(orthoBbox)
  }, [orthoBbox, fitToBbox])

  // Auto-zoom signal from Sidebar when user clicks a field
  useEffect(() => {
    if (!zoomToBounds || !mapLoaded.current) return
    const [[west, south], [east, north]] = zoomToBounds
    mapRef.current?.fitBounds([[west, south], [east, north]], { padding: 60, duration: 800 })
    setZoomToBounds(null)
  }, [zoomToBounds, setZoomToBounds])

  const handleMapLoad = useCallback(() => {
    mapLoaded.current = true
    if (orthoBbox) fitToBbox(orthoBbox)
    if (zoomToBounds) {
      const [[west, south], [east, north]] = zoomToBounds
      mapRef.current?.fitBounds([[west, south], [east, north]], { padding: 60, duration: 800 })
      setZoomToBounds(null)
    }
  }, [orthoBbox, fitToBbox, zoomToBounds, setZoomToBounds])

  const handleMapClick = useCallback((e: MapLayerMouseEvent) => {
    if (markerMode && onAddMarker) {
      onAddMarker(e.lngLat.lat, e.lngLat.lng)
      return
    }
    const feature = e.features?.[0]
    if (!feature) return
    if (feature.layer?.id === 'anomaly-fill') {
      setAnomalyPopup({ lng: e.lngLat.lng, lat: e.lngLat.lat })
    } else if (feature.layer?.id === 'markers-circle') {
      setMarkerPopup({ lng: e.lngLat.lng, lat: e.lngLat.lat, note: feature.properties?.note ?? null })
    }
  }, [markerMode, onAddMarker])

  const initialViewState = {
    longitude: field?.boundary?.coordinates[0][0][0] ?? 30.5,
    latitude: field?.boundary?.coordinates[0][0][1] ?? 50.4,
    zoom: 13,
  }

  const fileKey = activeLayer === 'orthophoto' ? 'orthophoto_preview' : activeLayer
  const imageUrl = flightId && orthoBbox
    ? `${API_BASE}/flights/${flightId}/files/${fileKey}`
    : null
  const imageCoords: [[number, number], [number, number], [number, number], [number, number]] | null = orthoBbox
    ? [
        [orthoBbox[0], orthoBbox[3]],
        [orthoBbox[2], orthoBbox[3]],
        [orthoBbox[2], orthoBbox[1]],
        [orthoBbox[0], orthoBbox[1]],
      ]
    : null

  const anomalyGeoJson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: anomalies.map((z) => ({
      type: 'Feature',
      geometry: z.zone_geom,
      properties: { area_ha: z.area_ha, index_type: z.index_type },
    })),
  }

  const markersGeoJson: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: markers.map((m) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [m.lon, m.lat] },
      properties: { note: m.note, id: m.id },
    })),
  }

  const interactiveLayers = [
    ...(anomalies.length > 0 ? ['anomaly-fill'] : []),
    ...(markers.length > 0 ? ['markers-circle'] : []),
  ]

  const cursor = markerMode ? 'crosshair' : undefined

  return (
    <Map
      ref={mapRef}
      onLoad={handleMapLoad}
      initialViewState={initialViewState}
      style={{ width: '100%', height: '100%', cursor }}
      mapStyle={OSM_STYLE}
      interactiveLayerIds={interactiveLayers}
      onClick={handleMapClick}
    >
      {field?.boundary && (
        <Source id="field-boundary" type="geojson" data={field.boundary}>
          <Layer id="field-line" type="line" paint={{ 'line-color': '#FFD700', 'line-width': 2 }} />
        </Source>
      )}

      {imageUrl && imageCoords && (
        <Source key={activeLayer} id="raster-overlay" type="image" url={imageUrl} coordinates={imageCoords}>
          <Layer id="raster-layer" type="raster" paint={{ 'raster-opacity': 0.85 }} />
        </Source>
      )}

      {anomalies.length > 0 && (
        <Source id="anomalies" type="geojson" data={anomalyGeoJson}>
          <Layer id="anomaly-fill" type="fill" paint={{ 'fill-color': 'rgba(220,50,50,0.15)', 'fill-outline-color': 'rgba(0,0,0,0)' }} />
          <Layer id="anomaly-line" type="line" paint={{ 'line-color': '#e53935', 'line-width': 2 }} />
        </Source>
      )}

      {markers.length > 0 && (
        <Source id="field-markers" type="geojson" data={markersGeoJson}>
          <Layer
            id="markers-circle"
            type="circle"
            paint={{
              'circle-radius': 8,
              'circle-color': '#1976d2',
              'circle-stroke-color': '#fff',
              'circle-stroke-width': 2,
            }}
          />
        </Source>
      )}

      {anomalyPopup && (
        <Popup longitude={anomalyPopup.lng} latitude={anomalyPopup.lat} closeOnClick onClose={() => setAnomalyPopup(null)}>
          <div style={{ fontSize: 13 }}>
            Аномальна зона
          </div>
        </Popup>
      )}

      {markerPopup && (
        <Popup longitude={markerPopup.lng} latitude={markerPopup.lat} closeOnClick onClose={() => setMarkerPopup(null)}>
          <div style={{ fontSize: 13 }}>
            {markerPopup.note || 'Без нотатки'}
          </div>
        </Popup>
      )}
    </Map>
  )
}
