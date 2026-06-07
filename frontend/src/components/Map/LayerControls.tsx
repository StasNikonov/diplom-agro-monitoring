import type { LayerType } from '../../store/useAppStore'
import type { IndexMap } from '../../types'

const ALL_TABS: { key: LayerType; label: string; indexType?: string; isDsm?: boolean }[] = [
  { key: 'orthophoto', label: 'Ортофото' },
  { key: 'ndvi', label: 'NDVI', indexType: 'NDVI' },
  { key: 'ndre', label: 'NDRE', indexType: 'NDRE' },
  { key: 'evi', label: 'EVI', indexType: 'EVI' },
  { key: 'dsm', label: 'Рельєф', isDsm: true },
]

interface Props {
  activeLayer: LayerType
  setActiveLayer: (l: LayerType) => void
  indexMaps: IndexMap[]
  hasDsm?: boolean
}

export default function LayerControls({ activeLayer, setActiveLayer, indexMaps, hasDsm }: Props) {
  const indexTypes = new Set<string>(indexMaps.map((im) => im.index_type))

  const visibleTabs = ALL_TABS.filter(
    (t) => (!t.indexType && !t.isDsm) || (t.indexType && indexTypes.has(t.indexType)) || (t.isDsm && hasDsm),
  )

  const stat = indexMaps.find(
    (im) => im.index_type === activeLayer.toUpperCase() as 'NDVI' | 'NDRE' | 'EVI',
  )

  return (
    <div className="layer-controls">
      <div className="layer-tabs">
        {visibleTabs.map((t) => (
          <button
            key={t.key}
            className={`tab-btn ${activeLayer === t.key ? 'active' : ''}`}
            onClick={() => setActiveLayer(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {stat && (
        <div className="layer-stats">
          <span>min: {stat.min_value?.toFixed(3) ?? '—'}</span>
          <span>mid: {stat.mean_value?.toFixed(3) ?? '—'}</span>
          <span>max: {stat.max_value?.toFixed(3) ?? '—'}</span>
        </div>
      )}

      {activeLayer !== 'orthophoto' && activeLayer !== 'dsm' && (
        <div className="legend">
          <div className="legend-gradient" />
          <div className="legend-labels">
            <span>низький</span>
            <span>середній</span>
            <span>високий</span>
          </div>
        </div>
      )}
      {activeLayer === 'dsm' && (
        <div className="legend">
          <div className="legend-gradient" style={{ background: 'linear-gradient(to right, #0080ff, #00ff80, #ffff00, #ff0000)' }} />
          <div className="legend-labels">
            <span>низько</span>
            <span>середньо</span>
            <span>високо</span>
          </div>
        </div>
      )}
    </div>
  )
}
