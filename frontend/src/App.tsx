import Dashboard from "./components/dashboard";
import Participants from "./components/participants";
import Metrics from "./components/metrics";
import { Activity } from "lucide-react";
import type {
  AdherenceResponse,
  DashboardSummary,
  Participant,
  ParticipantMetrics,
} from "./types";
import { useCallback, useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from "react-router-dom";

function App() {
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-01-02");

  const [participants, setParticipants] = useState<Participant[]>([]);
  const [adherenceData, setAdherenceData] = useState<AdherenceResponse | null>(
    null
  );
  const [dashboardSummary, setDashboardSummary] =
    useState<DashboardSummary | null>(null);
  const [selectedParticipant, setSelectedParticipant] = useState<number | null>(
    null
  );
  const [participantMetrics, setParticipantMetrics] =
    useState<ParticipantMetrics | null>(null);

  const [emailModal, setEmailModal] = useState(false);
  const [emailSubject, setEmailSubject] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [selectedParticipantsForEmail, setSelectedParticipantsForEmail] =
    useState<number[]>([]);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [summaryRes, adherenceRes, participantsRes] = await Promise.all([
        fetch(`${import.meta.env.VITE_API_URL}/dashboard/summary`),
        fetch(`${import.meta.env.VITE_API_URL}/adherence`),
        fetch(`${import.meta.env.VITE_API_URL}/participants`),
      ]);
      if (summaryRes.ok) {
        const summary = await summaryRes.json();
        setDashboardSummary(summary);
      }
      if (adherenceRes.ok) {
        const adherence = await adherenceRes.json();
        setAdherenceData(adherence);
      }

      if (participantsRes.ok) {
        const participantsList = await participantsRes.json();
        setParticipants(participantsList);
      }
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    }
  }, []);

  const fetchParticipantMetrics = useCallback(
    async (participantId: number) => {
      try {
        const params = new URLSearchParams({
          start_date: startDate,
          end_date: endDate,
        });

        const res = await fetch(
          `${
            import.meta.env.VITE_API_URL
          }/participants/${participantId}/metrics?${params}`
        );

        if (res.ok) {
          const metrics = await res.json();
          setParticipantMetrics(metrics);
        }
      } catch (err) {
        console.error("Failed to fetch participant metrics:", err);
      }
    },
    [startDate, endDate]
  );

  const sendEmail = useCallback(async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/email/send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          participant_ids: selectedParticipantsForEmail,
          subject: emailSubject,
          message: emailMessage,
        }),
      });
      if (res.ok) {
        setEmailModal(false);
        setEmailSubject("");
        setEmailMessage("");
        setSelectedParticipantsForEmail([]);
        alert("Email sent successfully!");
      }
    } catch (err) {
      console.error("Failed to send email:", err);
      alert("Failed to send email");
    }
  }, [selectedParticipantsForEmail, emailSubject, emailMessage]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  useEffect(() => {
    if (selectedParticipant) {
      fetchParticipantMetrics(selectedParticipant);
    }
  }, [selectedParticipant, fetchParticipantMetrics]);

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2 flex items-center gap-2">
              <Activity className="w-8 h-8" />
              Metrics Dashboard
            </h1>
            <p className="text-gray-600">
              Monitor and visualize health metrics over time with automatic
              aggregation, there is no limit in the backend for data points, so
              higher limits may make the website slower.
            </p>
          </div>

          <div className="mb-8">
            <nav className="flex space-x-8">
              <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                  `py-2 px-1 border-b-2 font-medium text-sm ${
                    isActive
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`
                }
              >
                Dashboard Overview
              </NavLink>
              <NavLink
                to="/participants"
                className={({ isActive }) =>
                  `py-2 px-1 border-b-2 font-medium text-sm ${
                    isActive
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`
                }
              >
                Participants
              </NavLink>
              <NavLink
                to="/metrics"
                className={({ isActive }) =>
                  `py-2 px-1 border-b-2 font-medium text-sm ${
                    isActive
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`
                }
              >
                Metrics Analysis
              </NavLink>
            </nav>
          </div>

          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="/dashboard"
              element={
                <Dashboard
                  adherenceData={adherenceData}
                  dashboardSummary={dashboardSummary}
                  participants={participants}
                  setAdherenceData={setAdherenceData}
                  setDashboardSummary={setDashboardSummary}
                  setSelectedParticipant={setSelectedParticipant}
                  selectedParticipant={selectedParticipant}
                  setParticipantMetrics={setParticipantMetrics}
                  participantMetrics={participantMetrics}
                  setEmailModal={setEmailModal}
                  setEmailSubject={setEmailSubject}
                  setEmailMessage={setEmailMessage}
                  setSelectedParticipantsForEmail={setSelectedParticipantsForEmail}
                  startDate={startDate}
                  endDate={endDate}
                  setParticipants={setParticipants}
                />
              }
            />
            <Route
              path="/participants"
              element={
                <Participants
                  startDate={startDate}
                  endDate={endDate}
                  setDashboardSummary={setDashboardSummary}
                  setAdherenceData={setAdherenceData}
                  setParticipants={setParticipants}
                  setParticipantMetrics={setParticipantMetrics}
                  participants={participants}
                  participantMetrics={participantMetrics}
                  selectedParticipant={selectedParticipant}
                  setSelectedParticipant={setSelectedParticipant}
                />
              }
            />
            <Route
              path="/metrics"
              element={
                <Metrics
                  startDate={startDate}
                  endDate={endDate}
                  setStartDate={setStartDate}
                  setEndDate={setEndDate}
                  selectedParticipant={selectedParticipant}
                  setDashboardSummary={setDashboardSummary}
                  setAdherenceData={setAdherenceData}
                  setParticipants={setParticipants}
                  setParticipantMetrics={setParticipantMetrics}
                />
              }
            />
          </Routes>

          {emailModal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-lg max-w-md w-full p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Send Email
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Recipients: {selectedParticipantsForEmail.length}{" "}
                      participants
                    </label>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Subject
                    </label>
                    <input
                      type="text"
                      value={emailSubject}
                      onChange={(e) => setEmailSubject(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Message
                    </label>
                    <textarea
                      value={emailMessage}
                      onChange={(e) => setEmailMessage(e.target.value)}
                      rows={4}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="flex gap-2 mt-6">
                  <button
                    onClick={sendEmail}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Send Email
                  </button>
                  <button
                    onClick={() => setEmailModal(false)}
                    className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Router>
  );
}

export default App;
