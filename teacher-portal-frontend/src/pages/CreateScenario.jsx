import { useState } from "react";

import { createScenario } from "../api/backend.js";

const DEFAULT_SCENARIO_JSON = {
  patient_history: {},
  wound_details: {},
  assessment_questions: [],
  evaluation_criteria: {},
};

export default function CreateScenario() {
  const [form, setForm] = useState({
    scenario_id: "",
    title: "",
    description: "",
    scenario_json: JSON.stringify(DEFAULT_SCENARIO_JSON, null, 2),
  });
  const [status, setStatus] = useState({ type: "", message: "" });
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setStatus({ type: "", message: "" });

    try {
      const scenarioData = JSON.parse(form.scenario_json);
      const response = await createScenario({
        scenario_id: form.scenario_id.trim(),
        title: form.title.trim(),
        description: form.description.trim(),
        scenario_data: scenarioData,
      });

      setStatus({
        type: "success",
        message: response.message || "Scenario created successfully",
      });
    } catch (err) {
      const message =
        err instanceof SyntaxError
          ? "Scenario JSON is not valid."
          : err.response?.data?.detail || err.message || "Failed to create scenario";
      setStatus({ type: "error", message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page-grid">
      <div className="page-header">
        <div>
          <h1>Create Scenario</h1>
          <p>
            Submit the teacher-facing metadata plus the runtime scenario JSON used by the VR flow.
          </p>
        </div>
      </div>

      {status.message && <div className={`status ${status.type}`}>{status.message}</div>}

      <form className="panel page-grid" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="scenario_id">Scenario ID</label>
            <input
              id="scenario_id"
              value={form.scenario_id}
              onChange={(event) =>
                setForm((current) => ({ ...current, scenario_id: event.target.value }))
              }
              placeholder="scenario_002"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="title">Title</label>
            <input
              id="title"
              value={form.title}
              onChange={(event) =>
                setForm((current) => ({ ...current, title: event.target.value }))
              }
              placeholder="Post Operative Wound"
              required
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            value={form.description}
            onChange={(event) =>
              setForm((current) => ({ ...current, description: event.target.value }))
            }
            placeholder="Surgical wound on forearm"
            required
          />
        </div>

        <div className="field">
          <label htmlFor="scenario_json">Scenario JSON Editor</label>
          <textarea
            id="scenario_json"
            value={form.scenario_json}
            onChange={(event) =>
              setForm((current) => ({ ...current, scenario_json: event.target.value }))
            }
            spellCheck={false}
            required
          />
        </div>

        <div className="button-row">
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Scenario"}
          </button>
        </div>
      </form>
    </section>
  );
}
