import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Skills from './pages/Skills';
import Workflows from './pages/Workflows';
import Automations from './pages/Automations';
import Logs from './pages/Logs';
import Settings from './pages/Settings';
import LLMSettings from './pages/LLMSettings';
import Voice from './pages/Voice';
import Habits from './pages/Habits';
import Documents from './pages/Documents';
import PendingActions from './pages/PendingActions';
import SetupWizard from './pages/SetupWizard';
import AppWizard from './pages/AppWizard';
import Study from './pages/Study';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/study" element={<Study />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/automations" element={<Automations />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/settings/llm" element={<LLMSettings />} />
          <Route path="/voice" element={<Voice />} />
          <Route path="/habits" element={<Habits />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/pending-actions" element={<PendingActions />} />
          <Route path="/setup" element={<SetupWizard />} />
          <Route path="/apps" element={<AppWizard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
