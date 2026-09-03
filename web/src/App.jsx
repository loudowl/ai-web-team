import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import NewProjectPage from './pages/NewProjectPage.jsx';
import MinimalBatchPage from './pages/MinimalBatchPage.jsx';
import ProjectPage from './pages/ProjectPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import { useUiStore } from './store/uiStore.js';

export default function App() {
  const interfaceMode = useUiStore(s => s.interfaceMode);
  const demoActive = useUiStore(s => s.demoActive);

  return (
    <div className={`app${interfaceMode === 'minimal' ? ' minimal-ui' : ''}${demoActive ? ' demo-active' : ''}`}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/new" element={<NewProjectPage />} />
        <Route path="/batch" element={<MinimalBatchPage />} />
        <Route path="/project/:projectId" element={<ProjectPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  );
}
