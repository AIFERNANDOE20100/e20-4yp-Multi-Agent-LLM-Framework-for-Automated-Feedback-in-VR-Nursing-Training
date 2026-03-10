import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, apiUpload } from "./api.js";

const EMPTY_PATIENT = {
  name: "",
  age: "",
  gender: "",
  address: "",
  medical_history: [],
  allergies: [],
  current_medications: [],
  surgery_details: {
    procedure: "",
    date: "",
    surgeon: "",
    reason: "N/A",
    hospital: "N/A",
  },
  pain_level: {
    description: "",
    pain_score: 0,
    pain_characteristics: "N/A",
    pain_medication: "N/A",
    last_pain_medication: "N/A",
  },
  comfort_needs: {
    current_position: "Sitting upright in bed",
    needs_bathroom: false,
    needs_water: false,
    comfortable_to_proceed: true,
  },
};

const EMPTY_QUESTION = () => ({
  question: "",
  options: ["", "", "", ""],
  correct_answer: "A",
  explanation: "",
});

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "-";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return value;
}

function ScenarioPreview({ scenario }) {
  const patient = scenario.patient_history || {};
  const surgery = patient.surgery_details || {};
  const pain = patient.pain_level || {};
  const comfort = patient.comfort_needs || {};
  const wound = scenario.wound_details || {};
  const questions = scenario.assessment_questions || [];

  return (
    <div className="preview">
      <div className="preview-header">
        <h2>{scenario.scenario_title || "Scenario Preview"}</h2>
        <div className="preview-meta">
          <span>ID: {scenario.scenario_id || "-"}</span>
          <span>Created: {scenario.created_at || "-"}</span>
        </div>
      </div>

      <div className="preview-grid">
        <div className="preview-section">
          <h3>Patient Details</h3>
          <div className="info-row"><span>Name</span><span>{formatValue(patient.name)}</span></div>
          <div className="info-row"><span>Age</span><span>{formatValue(patient.age)}</span></div>
          <div className="info-row"><span>Gender</span><span>{formatValue(patient.gender)}</span></div>
          <div className="info-row"><span>Address</span><span>{formatValue(patient.address)}</span></div>
          <div className="info-row"><span>Medical History</span><span>{formatValue(patient.medical_history)}</span></div>
          <div className="info-row"><span>Allergies</span><span>{formatValue(patient.allergies)}</span></div>
          <div className="info-row"><span>Current Medications</span><span>{formatValue(patient.current_medications)}</span></div>
        </div>

        <div className="preview-section">
          <h3>Surgery Details</h3>
          <div className="info-row"><span>Procedure</span><span>{formatValue(surgery.procedure)}</span></div>
          <div className="info-row"><span>Date</span><span>{formatValue(surgery.date)}</span></div>
          <div className="info-row"><span>Surgeon</span><span>{formatValue(surgery.surgeon)}</span></div>
          <div className="info-row"><span>Reason</span><span>{formatValue(surgery.reason)}</span></div>
          <div className="info-row"><span>Hospital</span><span>{formatValue(surgery.hospital)}</span></div>
        </div>

        <div className="preview-section">
          <h3>Pain Level</h3>
          <div className="info-row"><span>Description</span><span>{formatValue(pain.description)}</span></div>
          <div className="info-row"><span>Pain Score</span><span>{formatValue(pain.pain_score)}</span></div>
          <div className="info-row"><span>Characteristics</span><span>{formatValue(pain.pain_characteristics)}</span></div>
          <div className="info-row"><span>Pain Medication</span><span>{formatValue(pain.pain_medication)}</span></div>
          <div className="info-row"><span>Last Medication</span><span>{formatValue(pain.last_pain_medication)}</span></div>
        </div>

        <div className="preview-section">
          <h3>Comfort Needs</h3>
          <div className="info-row"><span>Current Position</span><span>{formatValue(comfort.current_position)}</span></div>
          <div className="info-row"><span>Needs Bathroom</span><span>{formatValue(comfort.needs_bathroom)}</span></div>
          <div className="info-row"><span>Needs Water</span><span>{formatValue(comfort.needs_water)}</span></div>
          <div className="info-row"><span>Comfortable to Proceed</span><span>{formatValue(comfort.comfortable_to_proceed)}</span></div>
        </div>
      </div>

      <div className="preview-section">
        <h3>Wound Details (Fixed)</h3>
        <div className="info-row"><span>Location</span><span>{formatValue(wound.location)}</span></div>
        <div className="info-row"><span>Type</span><span>{formatValue(wound.wound_type)}</span></div>
        <div className="info-row"><span>Appearance</span><span>{formatValue(wound.appearance)}</span></div>
        <div className="info-row"><span>Size</span><span>{formatValue(wound.size)}</span></div>
        <div className="info-row"><span>Wound Age</span><span>{formatValue(wound.wound_age)}</span></div>
        <div className="info-row"><span>Suture Type</span><span>{formatValue(wound.suture_type)}</span></div>
        <div className="info-row"><span>Expected Healing</span><span>{formatValue(wound.expected_healing)}</span></div>
        <div className="info-row"><span>Dressing Status</span><span>{formatValue(wound.dressing_status)}</span></div>
      </div>

      <div className="preview-section">
        <h3>MCQ Questions</h3>
        {questions.length === 0 ? (
          <div className="muted">No questions added.</div>
        ) : (
          questions.map((q, index) => (
            <div key={q.id || index} className="question-card">
              <div className="question-title">
                Q{index + 1}. {q.question}
              </div>
              <ul className="options-list">
                {(q.options || []).map((opt, optIndex) => (
                  <li key={optIndex}>
                    {String.fromCharCode(65 + optIndex)}. {opt}
                  </li>
                ))}
              </ul>
              <div className="info-row">
                <span>Correct Answer</span>
                <span>{formatValue(q.correct_answer)}</span>
              </div>
              <div className="info-row">
                <span>Explanation</span>
                <span>{formatValue(q.explanation)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [section, setSection] = useState("scenarios");
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [patient, setPatient] = useState(EMPTY_PATIENT);
  const [questions, setQuestions] = useState([EMPTY_QUESTION()]);
  const [listInput, setListInput] = useState({
    medical_history: "",
    allergies: "",
    current_medications: "",
  });

  const [historyFile, setHistoryFile] = useState(null);
  const [woundFile, setWoundFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState({ history: "", wound: "" });

  const scenarioTitle = useMemo(() => {
    const name = patient.name.trim() || "Patient";
    return `Custom Scenario - ${name}`;
  }, [patient.name]);

  async function loadScenarios() {
    setLoading(true);
    setError("");
    try {
      const data = await apiGet("/scenarios");
      setScenarios(data || []);
    } catch (err) {
      setError(err.message || "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }

  async function openScenario(id) {
    setLoading(true);
    setError("");
    try {
      const data = await apiGet(`/scenarios/${id}`);
      setSelectedScenario(data);
    } catch (err) {
      setError(err.message || "Failed to load scenario");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteScenario(id) {
    const ok = window.confirm("Are you sure you want to delete this scenario?");
    if (!ok) return;

    setLoading(true);
    setError("");
    try {
      await apiPost(`/scenarios/${id}`, null, { method: "DELETE" });
      if (selectedScenario?.scenario_id === id || selectedScenario?.id === id) {
        setSelectedScenario(null);
      }
      await loadScenarios();
    } catch (err) {
      setError(err.message || "Failed to delete scenario");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (section === "scenarios") {
      loadScenarios();
    }
  }, [section]);

  function handleListAdd(key) {
    const value = listInput[key].trim();
    if (!value) return;
    setPatient((prev) => ({
      ...prev,
      [key]: [...prev[key], value],
    }));
    setListInput((prev) => ({ ...prev, [key]: "" }));
  }

  function handleListRemove(key, index) {
    setPatient((prev) => ({
      ...prev,
      [key]: prev[key].filter((_, i) => i !== index),
    }));
  }

  function updateQuestion(index, updater) {
    setQuestions((prev) =>
      prev.map((q, i) => (i === index ? updater(q) : q))
    );
  }

  function addQuestion() {
    setQuestions((prev) => [...prev, EMPTY_QUESTION()]);
  }

  function removeQuestion(index) {
    setQuestions((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleCreateScenario(e) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const payload = {
      scenario_title: scenarioTitle,
      patient_history: {
        ...patient,
        age: Number(patient.age || 0),
        pain_level: {
          ...patient.pain_level,
          pain_score: Number(patient.pain_level.pain_score || 0),
        },
      },
      assessment_questions: questions.map((q, index) => ({
        id: `q${index + 1}`,
        question: q.question,
        options: q.options,
        correct_answer: q.correct_answer,
        explanation: q.explanation,
      })),
      created_by: "teacher_portal",
    };

    try {
      await apiPost("/scenarios", payload);
      setSection("scenarios");
      setSelectedScenario(null);
      setPatient(EMPTY_PATIENT);
      setQuestions([EMPTY_QUESTION()]);
      await loadScenarios();
    } catch (err) {
      setError(err.message || "Failed to create scenario");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(type) {
    const file = type === "history" ? historyFile : woundFile;
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("guideline_type", type);

    try {
      await apiUpload("/guidelines/upload", formData);
      setUploadStatus((prev) => ({
        ...prev,
        [type]: "Upload successful",
      }));
    } catch (err) {
      setUploadStatus((prev) => ({
        ...prev,
        [type]: err.message || "Upload failed",
      }));
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Teacher Portal</div>
        <nav className="nav">
          <button
            className={section === "scenarios" ? "active" : ""}
            onClick={() => {
              setSection("scenarios");
              setSelectedScenario(null);
            }}
          >
            Scenarios
          </button>
          <button
            className={section === "guidelines" ? "active" : ""}
            onClick={() => setSection("guidelines")}
          >
            Guidelines
          </button>
        </nav>
      </header>

      <main className="content">
        {error && <div className="alert error">{error}</div>}
        {loading && <div className="alert">Loading...</div>}

        {section === "scenarios" && (
          <section className="scenarios">
            <div className="section-header">
              <h1>Scenarios</h1>
              <button className="primary" onClick={() => setSection("create")}>
                Create New Scenario
              </button>
            </div>

            <div className="panel">
              {scenarios.length === 0 && !loading ? (
                <div className="muted">No scenarios found.</div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Patient Name</th>
                      <th>Created At</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenarios.map((scenario) => (
                      <tr key={scenario.id}>
                        <td>
                          <div className="id-cell">
                            <span>{scenario.id}</span>
                            <button
                              className="ghost"
                              onClick={() =>
                                navigator.clipboard.writeText(scenario.id)
                              }
                            >
                              Copy
                            </button>
                          </div>
                        </td>
                        <td>{scenario.patient_name || "-"}</td>
                        <td>{scenario.created_at || "-"}</td>
                        <td>
                          <button
                            className="ghost"
                            onClick={() => openScenario(scenario.id)}
                          >
                            Preview
                          </button>
                          <button
                            className="danger"
                            onClick={() => handleDeleteScenario(scenario.id)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {selectedScenario && (
              <div className="panel">
                <ScenarioPreview scenario={selectedScenario} />
              </div>
            )}
          </section>
        )}

        {section === "create" && (
          <section className="create">
            <div className="section-header">
              <h1>Create Scenario</h1>
              <button className="ghost" onClick={() => setSection("scenarios")}>
                Back to List
              </button>
            </div>

            <form className="panel form" onSubmit={handleCreateScenario}>
              <h2>Patient Details</h2>
              <div className="grid">
                <label>
                  Name
                  <input
                    type="text"
                    value={patient.name}
                    onChange={(e) =>
                      setPatient((prev) => ({ ...prev, name: e.target.value }))
                    }
                    required
                  />
                </label>
                <label>
                  Age
                  <input
                    type="number"
                    value={patient.age}
                    onChange={(e) =>
                      setPatient((prev) => ({ ...prev, age: e.target.value }))
                    }
                    required
                  />
                </label>
                <label>
                  Gender
                  <input
                    type="text"
                    value={patient.gender}
                    onChange={(e) =>
                      setPatient((prev) => ({ ...prev, gender: e.target.value }))
                    }
                    required
                  />
                </label>
                <label>
                  Address
                  <input
                    type="text"
                    value={patient.address}
                    onChange={(e) =>
                      setPatient((prev) => ({ ...prev, address: e.target.value }))
                    }
                    required
                  />
                </label>
              </div>

              <div className="grid">
                <label>
                  Surgical Procedure Name
                  <input
                    type="text"
                    value={patient.surgery_details.procedure}
                    onChange={(e) =>
                      setPatient((prev) => ({
                        ...prev,
                        surgery_details: {
                          ...prev.surgery_details,
                          procedure: e.target.value,
                        },
                      }))
                    }
                    required
                  />
                </label>
                <label>
                  Surgery Date
                  <input
                    type="date"
                    value={patient.surgery_details.date}
                    onChange={(e) =>
                      setPatient((prev) => ({
                        ...prev,
                        surgery_details: {
                          ...prev.surgery_details,
                          date: e.target.value,
                        },
                      }))
                    }
                    required
                  />
                </label>
                <label>
                  Surgeon Name
                  <input
                    type="text"
                    value={patient.surgery_details.surgeon}
                    onChange={(e) =>
                      setPatient((prev) => ({
                        ...prev,
                        surgery_details: {
                          ...prev.surgery_details,
                          surgeon: e.target.value,
                        },
                      }))
                    }
                    required
                  />
                </label>
                <label>
                  Pain Description
                  <input
                    type="text"
                    value={patient.pain_level.description}
                    onChange={(e) =>
                      setPatient((prev) => ({
                        ...prev,
                        pain_level: {
                          ...prev.pain_level,
                          description: e.target.value,
                        },
                      }))
                    }
                    required
                  />
                </label>
                <label>
                  Pain Score (0-10)
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={patient.pain_level.pain_score}
                    onChange={(e) =>
                      setPatient((prev) => ({
                        ...prev,
                        pain_level: {
                          ...prev.pain_level,
                          pain_score: e.target.value,
                        },
                      }))
                    }
                    required
                  />
                </label>
              </div>

              <div className="list-group">
                <h3>Medical History</h3>
                <div className="list-input">
                  <input
                    type="text"
                    value={listInput.medical_history}
                    onChange={(e) =>
                      setListInput((prev) => ({
                        ...prev,
                        medical_history: e.target.value,
                      }))
                    }
                  />
                  <button type="button" onClick={() => handleListAdd("medical_history")}>
                    Add
                  </button>
                </div>
                <div className="chips">
                  {patient.medical_history.map((item, index) => (
                    <span key={index}>
                      {item}
                      <button type="button" onClick={() => handleListRemove("medical_history", index)}>
                        Remove
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="list-group">
                <h3>Allergies</h3>
                <div className="list-input">
                  <input
                    type="text"
                    value={listInput.allergies}
                    onChange={(e) =>
                      setListInput((prev) => ({
                        ...prev,
                        allergies: e.target.value,
                      }))
                    }
                  />
                  <button type="button" onClick={() => handleListAdd("allergies")}>
                    Add
                  </button>
                </div>
                <div className="chips">
                  {patient.allergies.map((item, index) => (
                    <span key={index}>
                      {item}
                      <button type="button" onClick={() => handleListRemove("allergies", index)}>
                        Remove
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="list-group">
                <h3>Current Medications</h3>
                <div className="list-input">
                  <input
                    type="text"
                    value={listInput.current_medications}
                    onChange={(e) =>
                      setListInput((prev) => ({
                        ...prev,
                        current_medications: e.target.value,
                      }))
                    }
                  />
                  <button type="button" onClick={() => handleListAdd("current_medications")}>
                    Add
                  </button>
                </div>
                <div className="chips">
                  {patient.current_medications.map((item, index) => (
                    <span key={index}>
                      {item}
                      <button type="button" onClick={() => handleListRemove("current_medications", index)}>
                        Remove
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <h2>MCQ Questions</h2>
              {questions.map((q, index) => (
                <div key={index} className="panel nested">
                  <div className="section-header">
                    <h3>Question {index + 1}</h3>
                    <button type="button" className="ghost" onClick={() => removeQuestion(index)}>
                      Remove
                    </button>
                  </div>
                  <label>
                    Question Text
                    <input
                      type="text"
                      value={q.question}
                      onChange={(e) =>
                        updateQuestion(index, (prev) => ({
                          ...prev,
                          question: e.target.value,
                        }))
                      }
                      required
                    />
                  </label>

                  <div className="grid">
                    {q.options.map((opt, optIndex) => (
                      <label key={optIndex}>
                        Option {String.fromCharCode(65 + optIndex)}
                        <input
                          type="text"
                          value={opt}
                          onChange={(e) =>
                            updateQuestion(index, (prev) => {
                              const nextOptions = [...prev.options];
                              nextOptions[optIndex] = e.target.value;
                              return { ...prev, options: nextOptions };
                            })
                          }
                          required
                        />
                      </label>
                    ))}
                  </div>

                  <label>
                    Correct Answer
                    <select
                      value={q.correct_answer}
                      onChange={(e) =>
                        updateQuestion(index, (prev) => ({
                          ...prev,
                          correct_answer: e.target.value,
                        }))
                      }
                    >
                      <option value="A">A</option>
                      <option value="B">B</option>
                      <option value="C">C</option>
                      <option value="D">D</option>
                    </select>
                  </label>

                  <label>
                    Explanation
                    <textarea
                      value={q.explanation}
                      onChange={(e) =>
                        updateQuestion(index, (prev) => ({
                          ...prev,
                          explanation: e.target.value,
                        }))
                      }
                      required
                    />
                  </label>
                </div>
              ))}

              <button type="button" className="ghost" onClick={addQuestion}>
                Add Question
              </button>

              <button type="submit" className="primary">Create Scenario</button>
            </form>
          </section>
        )}

        {section === "guidelines" && (
          <section className="guidelines">
            <div className="section-header">
              <h1>Guidelines Upload</h1>
            </div>

            <div className="panel">
              <h2>History Taking Guidelines</h2>
              <input
                type="file"
                accept=".txt"
                onChange={(e) => setHistoryFile(e.target.files?.[0] || null)}
              />
              <button className="primary" onClick={() => handleUpload("history")}>
                Upload
              </button>
              {uploadStatus.history && (
                <div className="muted">{uploadStatus.history}</div>
              )}
            </div>

            <div className="panel">
              <h2>Wound Cleaning and Dressing Guidelines</h2>
              <input
                type="file"
                accept=".txt"
                onChange={(e) => setWoundFile(e.target.files?.[0] || null)}
              />
              <button className="primary" onClick={() => handleUpload("wound")}>
                Upload
              </button>
              {uploadStatus.wound && (
                <div className="muted">{uploadStatus.wound}</div>
              )}
            </div>

            <div className="note">
              Uploading a new guideline file affects all future student sessions.
              Sessions already in progress are not affected because guidelines are cached per session when the cleaning and dressing step begins.
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
