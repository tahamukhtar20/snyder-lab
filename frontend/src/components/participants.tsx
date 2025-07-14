import { useCallback, useEffect } from "react";
import {
  Activity,
  BarChart3,
  Users,
  Eye,
  TrendingUp,
  Heart,
} from "lucide-react";
import type { AdherenceResponse, DashboardSummary, Participant, ParticipantMetrics } from "../types";

type Props = {
    startDate: string;
    endDate: string;
    setDashboardSummary: (summary: DashboardSummary) => void;
    setAdherenceData: (data: AdherenceResponse) => void;
    setParticipants: (participants: Participant[]) => void;
    setParticipantMetrics: (metrics: ParticipantMetrics) => void;
    participants: Participant[];
    participantMetrics: ParticipantMetrics | null;
    selectedParticipant: number | null;
    setSelectedParticipant: (id: number | null) => void;
    };

function Participants(props: Props) {
    const {
        startDate,
        endDate,
        setDashboardSummary,
        setAdherenceData,
        setParticipants,
        setParticipantMetrics,
        participants,
        participantMetrics,
        selectedParticipant,
        setSelectedParticipant,
    } = props
  
    const fetchDashboardData = useCallback(async () => {
      try {
        const [summaryRes, adherenceRes, participantsRes] = await Promise.all([
          fetch(`${import.meta.env.VITE_API_URL}/dashboard/summary`),
          fetch(`${import.meta.env.VITE_API_URL}/adherence`),
          fetch(`${import.meta.env.VITE_API_URL}/participants`)
        ])
        if (summaryRes.ok) {
          const summary = await summaryRes.json()
          setDashboardSummary(summary)
        }
        if (adherenceRes.ok) {
          const adherence = await adherenceRes.json()
          setAdherenceData(adherence)
        }
  
        if (participantsRes.ok) {
          const participantsList = await participantsRes.json()
          setParticipants(participantsList)
        }
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      }
    }, [])
  
    const fetchParticipantMetrics = useCallback(async (participantId: number) => {
      try {
        const params = new URLSearchParams({
          start_date: startDate,
          end_date: endDate,
        })
        
        const res = await fetch(
          `${import.meta.env.VITE_API_URL}/participants/${participantId}/metrics?${params}`
        )
        
        if (res.ok) {
          const metrics = await res.json()
          setParticipantMetrics(metrics)
        }
      } catch (err) {
        console.error('Failed to fetch participant metrics:', err)
      }
    }, [startDate, endDate])
  
    useEffect(() => {
      fetchDashboardData()
    }, [fetchDashboardData])
  
    useEffect(() => {
      if (selectedParticipant) {
        fetchParticipantMetrics(selectedParticipant)
      }
    }, [selectedParticipant, fetchParticipantMetrics])

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            <Users className="w-5 h-5" />
            Participants Management
          </h2>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {participants.map((participant) => (
              <div
                key={participant.participant_id}
                className="border rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900">
                    {participant.name}
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                        setSelectedParticipant(participant.participant_id)
                      }
                      className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                      title="View Details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="text-sm text-gray-600 space-y-1">
                  <div>ID: {participant.participant_id}</div>
                  <div>
                    Token: {participant.token ? "Active" : "Not Active"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {selectedParticipant && participantMetrics && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-800">
                {participantMetrics.participant_name} - Detailed Metrics
              </h2>
              <button
                onClick={() => setSelectedParticipant(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-red-50 rounded-lg p-4">
                <div className="flex items-center">
                  <Heart className="w-6 h-6 text-red-500" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-red-800">
                      Avg Heart Rate
                    </p>
                    <p className="text-xl font-bold text-red-900">
                      {participantMetrics.heart_rate_summary.avg_hr.toFixed(0)}{" "}
                      bpm
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-center">
                  <TrendingUp className="w-6 h-6 text-blue-500" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-blue-800">
                      Max Heart Rate
                    </p>
                    <p className="text-xl font-bold text-blue-900">
                      {participantMetrics.heart_rate_summary.max_hr.toFixed(0)}{" "}
                      bpm
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center">
                  <Activity className="w-6 h-6 text-green-500" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-green-800">
                      Min Heart Rate
                    </p>
                    <p className="text-xl font-bold text-green-900">
                      {participantMetrics.heart_rate_summary.min_hr.toFixed(0)}{" "}
                      bpm
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-purple-50 rounded-lg p-4">
                <div className="flex items-center">
                  <BarChart3 className="w-6 h-6 text-purple-500" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-purple-800">
                      Total Points
                    </p>
                    <p className="text-xl font-bold text-purple-900">
                      {participantMetrics.heart_rate_summary.total_points.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {participantMetrics.heart_rate_zones.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Heart Rate Zones
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {participantMetrics.heart_rate_zones.map((zone) => (
                    <div key={zone.zone_name} className="border rounded-lg p-4">
                      <h4 className="font-medium text-gray-900">
                        {zone.zone_name}
                      </h4>
                      <div className="text-sm text-gray-600 mt-2">
                        <div>Avg Minutes: {zone.avg_minutes.toFixed(0)}</div>
                        <div>Avg Calories: {zone.avg_calories.toFixed(0)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Participants;
