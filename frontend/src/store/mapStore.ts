import { create } from 'zustand'

interface MapState {
  selectedSystem: number | null
  route: number[] | null
  setSelectedSystem: (systemId: number | null) => void
  setRoute: (route: number[] | null) => void
}

export const useMapStore = create<MapState>((set) => ({
  selectedSystem: null,
  route: null,
  setSelectedSystem: (systemId) => set({ selectedSystem: systemId }),
  setRoute: (route) => set({ route }),
}))

