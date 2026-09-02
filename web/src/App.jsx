import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
import NewProjectPage from './pages/NewProjectPage.jsx';
import ProjectPage from './pages/ProjectPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';

export default function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/new" element={<NewProjectPage />} />
        <Route path="/project/:projectId" element={<ProjectPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </div>
  );
}
