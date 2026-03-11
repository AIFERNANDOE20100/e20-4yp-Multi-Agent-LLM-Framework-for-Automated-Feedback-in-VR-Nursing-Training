import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import ScenarioCard from "../components/ScenarioCard.jsx";
import { getScenarioById, getScenarios } from "../api/backend.js";

export default function ScenarioList() {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailId, setDetailId] = useState("");
  const [detailData, setDetailData] = useState({});

  async function handleLoadScenarios() {
    setLoading(true);
    setError("");
    try {
      const data = await getScenarios();
      setScenarios(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    handleLoadScenarios();
  }, []);

  async function toggleDetails(scenarioId) {
    if (detailId === scenarioId) {
      setDetailId("");
      return;
    }

    setError("");
    try {
      const data = await getScenarioById(scenarioId);
      setDetailData((current) => ({ ...current, [scenarioId]: data }));
      setDetailId(scenarioId);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load scenario");
    }
  }

  return (
    <section className="page-grid">
      <div className="page-header">
        <div>
          <h1>Scenario List</h1>
          <p>Load the scenario catalog, inspect the JSON, or jump straight to session launch.</p>
        </div>
        <div className="button-row">
          <button className="btn btn-primary" onClick={handleLoadScenarios}>
            {loading ? "Loading..." : "Refresh Scenarios"}
          </button>
        </div>
      </div>

      {error && <div className="status error">{error}</div>}

      <div className="scenario-list">
        {scenarios.length === 0 ? (
          <div className="panel">
            <p className="muted">No scenarios loaded yet. Use refresh to query the backend.</p>
          </div>
        ) : (
          scenarios.map((scenario) => (
            <ScenarioCard
              key={scenario.scenario_id}
              scenario={scenario}
              onViewDetails={() => toggleDetails(scenario.scenario_id)}
              onStart={() =>
                navigate("/sessions/start", {
                  state: { scenarioId: scenario.scenario_id },
                })
              }
              detailsOpen={detailId === scenario.scenario_id}
              details={detailData[scenario.scenario_id]}
            />
          ))
        )}
      </div>
    </section>
  );
}
