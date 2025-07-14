import { useCallback, useEffect } from "react";
import {
  Activity,
  BarChart3,
  Users,
  AlertTriangle,
  CheckCircle,
  Mail,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
    statusColors,
    statusLabels,
} from "../constants"
import type {
    DashboardSummary,
    AdherenceResponse,
    ParticipantMetrics,
    Participant,
    AdherenceStatus,
} from "../types";

type Props = {
    startDate: string;
    endDate: string;
    setEmailModal: (open: boolean) => void;
    setEmailSubject: (subject: string) => void;
    setEmailMessage: (message: string) => void;
    setSelectedParticipantsForEmail: (participants: number[]) => void;
    selectedParticipant: number | null;
    setSelectedParticipant: (participantId: number | null) => void;
    dashboardSummary: DashboardSummary | null;
    setDashboardSummary: (summary: DashboardSummary | null) => void;
    adherenceData: AdherenceResponse | null;
    setAdherenceData: (data: AdherenceResponse | null) => void;
    participants: Participant[] | null;
    setParticipants: (participants: Participant[]) => void;
    participantMetrics: ParticipantMetrics | null;
    setParticipantMetrics: (metrics: ParticipantMetrics | null) => void;
};

function Dashboard(props: Props) {
    const {
        startDate,
        endDate,
        setEmailModal,
        setEmailSubject,
        setEmailMessage,
        setSelectedParticipantsForEmail,
        selectedParticipant,
        setSelectedParticipant,
        dashboardSummary,
        setDashboardSummary,
        adherenceData,
        setAdherenceData,
        setParticipants,
        setParticipantMetrics,
    } = props;
    
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
  

    useEffect(() => {
      fetchDashboardData();
    }, [fetchDashboardData]);
  
    useEffect(() => {
      if (selectedParticipant) {
        fetchParticipantMetrics(selectedParticipant);
      }
    }, [selectedParticipant, fetchParticipantMetrics]);


  



  return (
    <div className="space-y-6">
      {dashboardSummary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Users className="w-8 h-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">
                  Total Participants
                </p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardSummary.total_participants}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">
                  Active Participants
                </p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardSummary.active_participants}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <BarChart3 className="w-8 h-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">
                  Total Data Points
                </p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardSummary.total_data_points.toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">
                  System Status
                </p>
                <p className="text-2xl font-bold text-gray-900 capitalize">
                  {dashboardSummary.system_status}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {adherenceData && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Adherence Overview
              </h2>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600">
                  {adherenceData.issues_count} issues found
                </span>
                <button
                  onClick={() => {
                    const issueParticipants = adherenceData.participants
                      .filter((p) => p.status !== "good")
                      .map((p) => p.participant_id);
                    setSelectedParticipantsForEmail(issueParticipants);
                    setEmailSubject("Adherence Alert");
                    setEmailMessage(
                      "We noticed some issues with your data upload. Please check your device and sync your data."
                    );
                    setEmailModal(true);
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
                >
                  <Mail className="w-4 h-4" />
                  Email Issues
                </button>
              </div>
            </div>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {adherenceData.participants.map((participant) => (
                <div
                  key={participant.participant_id}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() =>
                    setSelectedParticipant(participant.participant_id)
                  }
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-900">
                      {participant.name}
                    </h3>
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{
                        backgroundColor: statusColors[participant.status],
                      }}
                    />
                  </div>

                  <div className="text-sm text-gray-600 space-y-1">
                    <div>Status: {statusLabels[participant.status]}</div>
                    <div>
                      Adherence: {participant.adherence_percentage.toFixed(1)}%
                    </div>
                    <div>
                      Sleep Upload:{" "}
                      {participant.sleep_upload_percentage.toFixed(1)}%
                    </div>
                    {participant.last_data_timestamp && (
                      <div>
                        Last Data:{" "}
                        {new Date(
                          participant.last_data_timestamp
                        ).toLocaleDateString()}
                      </div>
                    )}
                  </div>

                  <div className="mt-2 text-xs text-gray-500">
                    {participant.details}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {adherenceData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            Adherence Status Distribution
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={Object.entries(
                    adherenceData.participants.reduce((acc, p) => {
                      acc[p.status] = (acc[p.status] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>)
                  ).map(([status, count]) => ({
                    name: statusLabels[status as AdherenceStatus],
                    value: count,
                    color: statusColors[status as AdherenceStatus],
                  }))}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                >
                  {Object.keys(statusColors).map((status, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={statusColors[status as AdherenceStatus]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
