import type * as GeoJSON from 'geojson'

export type FlightStatus =
  | 'uploaded'
  | 'odm_queued'
  | 'odm_processing'
  | 'odm_done'
  | 'odm_failed'
  | 'indices_done'

export interface Field {
  id: string
  name: string
  area_ha: number | null
  boundary: GeoJSON.Polygon | null
  created_at: string
}

export interface IndexMap {
  id: string
  index_type: 'NDVI' | 'NDRE' | 'EVI'
  file_path: string
  min_value: number | null
  max_value: number | null
  mean_value: number | null
  created_at: string
}

export interface Flight {
  id: string
  field_id: string
  flown_at: string
  status: FlightStatus
  raw_path: string | null
  notes: string | null
  created_at: string
  index_maps: IndexMap[]
  has_dsm: boolean
}

export interface IndexRecommendation {
  index_type: string
  category: string
  color: string
  recommendation: string
  is_proxy: boolean
}

export interface FieldMarker {
  id: string
  field_id: string
  lat: number
  lon: number
  note: string | null
  created_at: string
}

export interface NdviHistoryPoint {
  flight_id: string
  flown_at: string
  ndvi_mean: number | null
  evi_mean: number | null
  anomaly_ha: number | null
}

export interface FlightStatus_ {
  flight_id: string
  status: FlightStatus
  odm_progress: number | null
  job_id: string | null
}

export interface AnomalyZone {
  id: string
  flight_id: string
  index_type: string
  zone_geom: GeoJSON.MultiPolygon
  area_ha: number
  threshold: number
}
