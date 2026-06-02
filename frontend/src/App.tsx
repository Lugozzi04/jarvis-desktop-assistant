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

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/automations" element={<Automations />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/settings/llm" element={<LLMSettings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
