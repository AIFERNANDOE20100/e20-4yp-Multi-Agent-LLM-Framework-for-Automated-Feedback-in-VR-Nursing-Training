export default function ScenarioCard({
  scenario,
  onStart,
  onViewDetails,
  detailsOpen = false,
  details = null,
}) {
  return (
    <article className="card">
      <div className="scenario-card-header">
        <div>
          <div className="scenario-meta">Scenario ID</div>
          <h3>{scenario.scenario_id}</h3>
          <p>{scenario.title}</p>
        </div>
        <div className="button-row">
          <button className="btn btn-secondary" onClick={onViewDetails}>
            {detailsOpen ? "Hide Details" : "View Details"}
          </button>
          <button className="btn btn-primary" onClick={onStart}>
            Start Session
          </button>
        </div>
      </div>
      <p>{scenario.description || "No description provided."}</p>
      {detailsOpen && details && (
        <div className="detail-box">
          <pre>{JSON.stringify(details, null, 2)}</pre>
        </div>
      )}
    </article>
  );
}
