import { Link } from "react-router-dom";

export default function Dashboard() {
  const cards = [
    {
      title: "Create Scenario",
      description:
        "Add a new clinical scenario and store the runtime-compatible metadata in Firestore.",
      to: "/scenarios/create",
      action: "Open Builder",
    },
    {
      title: "View Scenarios",
      description:
        "Review saved scenarios and launch a VR session for a selected student.",
      to: "/scenarios",
      action: "Browse Scenarios",
    },
    {
      title: "Upload Guidelines",
      description:
        "Send guideline `.txt` files to the shared OpenAI vector store used by the backend.",
      to: "/guidelines/upload",
      action: "Upload File",
    },
  ];

  return (
    <section className="page-grid">
      <div className="page-header">
        <div>
          <h1>Teacher Dashboard</h1>
          <p>Manage scenarios, launch sessions, and update retrieval guidelines.</p>
        </div>
      </div>

      <div className="page-grid dashboard-grid">
        {cards.map((card) => (
          <article key={card.title} className="card">
            <h3>{card.title}</h3>
            <p>{card.description}</p>
            <div className="cta-row">
              <Link className="btn btn-primary btn-link" to={card.to}>
                {card.action}
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
