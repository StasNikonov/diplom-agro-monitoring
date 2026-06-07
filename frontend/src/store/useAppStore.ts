import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type LayerType = 'orthophoto' | 'ndvi' | 'ndre' | 'evi' | 'dsm'
export type UserRole = 'admin' | 'employee'

interface AppState {
  token: string | null
  role: UserRole | null
  setToken: (token: string) => void
  setRole: (role: UserRole) => void
  clearToken: () => void

  selectedFieldId: string | null
  setSelectedFieldId: (id: string | null) => void

  selectedFlightId: string | null
  setSelectedFlightId: (id: string | null) => void

  activeLayer: LayerType
  setActiveLayer: (layer: LayerType) => void

  zoomToBounds: [[number, number], [number, number]] | null
  setZoomToBounds: (b: [[number, number], [number, number]] | null) => void
}

const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      setToken: (token) => set({ token }),
      setRole: (role) => set({ role }),
      clearToken: () => set({ token: null, role: null }),

      selectedFieldId: null,
      setSelectedFieldId: (id) => set({ selectedFieldId: id }),

      selectedFlightId: null,
      setSelectedFlightId: (id) => set({ selectedFlightId: id }),

      activeLayer: 'ndvi',
      setActiveLayer: (layer) => set({ activeLayer: layer }),

      zoomToBounds: null,
      setZoomToBounds: (b) => set({ zoomToBounds: b }),
    }),
    {
      name: 'agro-storage',
      partialize: (s) => ({ token: s.token, role: s.role }),
    },
  ),
)

export default useAppStore
