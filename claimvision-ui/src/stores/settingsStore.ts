import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  autoOpenDetailPanel: boolean;
  setAutoOpenDetailPanel: (value: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      autoOpenDetailPanel: false, // Default to false
      setAutoOpenDetailPanel: (value) => set({ autoOpenDetailPanel: value }),
    }),
    {
      name: 'claimvision-settings',
    }
  )
);
