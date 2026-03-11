import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import CreateScenario from "./pages/CreateScenario.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ScenarioList from "./pages/ScenarioList.jsx";
import StartSession from "./pages/StartSession.jsx";
import UploadGuidelines from "./pages/UploadGuidelines.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="page-shell">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scenarios" element={<ScenarioList />} />
          <Route path="/scenarios/create" element={<CreateScenario />} />
          <Route path="/sessions/start" element={<StartSession />} />
          <Route path="/guidelines/upload" element={<UploadGuidelines />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
