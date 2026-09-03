import { Routes, Route } from 'react-router-dom';
import AppNav from './components/AppNav.jsx';
import HomePage from './pages/HomePage.jsx';
import NewProjectPage from './pages/NewProjectPage.jsx';
import MinimalBatchPage from './pages/MinimalBatchPage.jsx';
import ProjectPage from './pages/ProjectPage.jsx';
import JiraBoardPage from './pages/JiraBoardPage.jsx';
import ArchivedTicketsPage from './pages/ArchivedTicketsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import { useUiStore } from './store/uiStore.js';

export default function App() {
  const interfaceMode = useUiStore(s => s.interfaceMode);
  const demoActive = useUiStore(s => s.demoActive);

  return (
    <div className={`app${interfaceMode === 'minimal' ? ' minimal-ui' : ''}${demoActive ? ' demo-active' : ''}`}>
      <AppNav />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/new" element={<NewProjectPage />} />
        <Route path="/new/jira" element={<NewProjectPage />} />
        <Route path="/batch" element={<MinimalBatchPage />} />
        <Route path="/project/:projectId" element={<ProjectPage />} />
        <Route path="/board" element={<JiraBoardPage />} />
        <Route path="/board/:projectId" element={<ProjectPage />} />
        <Route path="/archived" element={<ArchivedTicketsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  );
}
