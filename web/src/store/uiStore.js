import { create } from 'zustand';

const UI_MODE_KEY = 'ai-web-team-ui-mode';
const REPO_PATH_KEY = 'ai-web-team-repo-path';

export const useUiStore = create((set) => ({
  interfaceMode: localStorage.getItem(UI_MODE_KEY) || 'standard',
  demoActive: false,
  lastRepoPath: localStorage.getItem(REPO_PATH_KEY) || '',

  setInterfaceMode: (mode) => {
    localStorage.setItem(UI_MODE_KEY, mode);
    set({ interfaceMode: mode });
  },

  setLastRepoPath: (path) => {
    const value = (path || '').trim();
    if (value) localStorage.setItem(REPO_PATH_KEY, value);
    set({ lastRepoPath: value });
  },

  startDemo: () => set({ demoActive: true }),

  endDemo: () => set({ demoActive: false }),
}));
