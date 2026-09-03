import { create } from 'zustand';

const UI_MODE_KEY = 'ai-web-team-ui-mode';
const REPO_PATH_KEY = 'ai-web-team-repo-path';
const NEW_PROJECT_LAYOUT_KEY = 'ai-web-team-new-project-layout';

export const useUiStore = create((set) => ({
  interfaceMode: localStorage.getItem(UI_MODE_KEY) || 'standard',
  newProjectLayout: localStorage.getItem(NEW_PROJECT_LAYOUT_KEY) || 'standard',
  demoActive: false,
  lastRepoPath: localStorage.getItem(REPO_PATH_KEY) || '',

  setInterfaceMode: (mode) => {
    localStorage.setItem(UI_MODE_KEY, mode);
    set({ interfaceMode: mode });
  },

  setNewProjectLayout: (layout) => {
    localStorage.setItem(NEW_PROJECT_LAYOUT_KEY, layout);
    set({ newProjectLayout: layout });
  },

  setLastRepoPath: (path) => {
    const value = (path || '').trim();
    if (value) localStorage.setItem(REPO_PATH_KEY, value);
    set({ lastRepoPath: value });
  },

  startDemo: () => set({ demoActive: true }),

  endDemo: () => set({ demoActive: false }),
}));
