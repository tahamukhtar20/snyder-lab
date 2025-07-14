import { useState, useMemo, useCallback, useEffect } from "react";
import {
  Calendar,
  Activity,
  User,
  BarChart3,
  Info,
  Clock,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { downsample } from "../utils/common";
import { aggregationOptions, metricOptions } from "../constants";
import type {
  AdherenceResponse,
  ApiResponse,
  DashboardSummary,
  DataStats,
  Participant,
  ParticipantMetrics,
} from "../types";

type Props = {
  startDate: string;
  endDate: string;
  setStartDate: (date: string) => void;
  setEndDate: (date: string) => void;
  selectedParticipant: number | null;
  setDashboardSummary: (summary: DashboardSummary) => void;
  setAdherenceData: (data: AdherenceResponse) => void;
  setParticipants: (participants: Participant[]) => void;
  setParticipantMetrics: (metrics: ParticipantMetrics) => void;
};

function Metrics(props: Props) {
  const {
    startDate,
    endDate,
    setStartDate,
    setEndDate,
    selectedParticipant,
    setDashboardSummary,
    setAdherenceData,
    setParticipants,
    setParticipantMetrics,
  } = props;
  const [metric, setMetric] = useState("heart_rate");
  const [userIds, setUserIds] = useState("1");
  const [aggregation, setAggregation] = useState("");
  const [limit, setLimit] = useState(100);
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [apiResponse, setApiResponse] = useState<ApiResponse | null>(null);
  const [dataStats, setDataStats] = useState<DataStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  const fetchDataStats = useCallback(async () => {
    if (!startDate || !endDate || !userIds) return;

    try {
      const userIdArray = userIds
        .split(",")
        .map((id) => parseInt(id.trim()))
        .filter((id) => !isNaN(id));
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });

      userIdArray.forEach((id) =>
        params.append("participant_ids", id.toString())
      );

      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/data/stats?${params}`
      );

      if (res.ok) {
        const stats = await res.json();
        setDataStats(stats);
      }
    } catch (err) {
      console.error("Failed to fetch data stats:", err);
    }
  }, [startDate, endDate, userIds]);

  const fetchData = useCallback(
    async (paginationCursor?: string | null, isNewQuery = false) => {
      if (!metric || !startDate || !endDate || !userIds) {
        setError("Please fill in all fields");
        return;
      }

      setLoading(true);
      setError("");

      try {
        const userIdArray = userIds
          .split(",")
          .map((id) => parseInt(id.trim()))
          .filter((id) => !isNaN(id));

        if (userIdArray.length === 0) {
          setError("Please provide valid user IDs");
          setLoading(false);
          return;
        }

        const params = new URLSearchParams({
          metric,
          start_date: startDate,
          end_date: endDate,
          limit: limit.toString(),
        });

        userIdArray.forEach((id) => params.append("user_ids", id.toString()));

        if (aggregation) {
          params.append("aggregation", aggregation);
        }

        if (paginationCursor) {
          params.append("cursor", paginationCursor);
        }

        const res = await fetch(
          `${import.meta.env.VITE_API_URL}/data?${params}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || "Failed to fetch data");
        }

        const result: ApiResponse = await res.json();
        setApiResponse(result);

        if (isNewQuery) {
          setCursor(null);
          setCursorHistory([]);
          setCurrentPage(1);
        }

        await fetchDataStats();
      } catch (err) {
        setError(
          err instanceof Error
            ? JSON.stringify(err)
            : "Failed to fetch data. Please check your connection and try again."
        );
      } finally {
        setLoading(false);
      }
    },
    [metric, startDate, endDate, userIds, aggregation, limit, fetchDataStats]
  );

  useEffect(() => {
    if (startDate && endDate && userIds) {
      fetchData(null, true);
    }
  }, [metric, startDate, endDate, userIds, aggregation, limit, fetchData]);

  const handleNextPage = useCallback(() => {
    if (apiResponse?.metadata.next_cursor) {
      setCursorHistory((prev) => [...prev, cursor || ""]);
      setCursor(apiResponse.metadata.next_cursor);
      setCurrentPage((prev) => prev + 1);
      fetchData(apiResponse.metadata.next_cursor);
    }
  }, [apiResponse, cursor, fetchData]);

  const handlePreviousPage = useCallback(() => {
    if (cursorHistory.length > 0) {
      const previousCursor = cursorHistory[cursorHistory.length - 1];
      setCursorHistory((prev) => prev.slice(0, -1));
      setCursor(previousCursor || null);
      setCurrentPage((prev) => prev - 1);
      fetchData(previousCursor || null);
    }
  }, [cursorHistory, fetchData]);

  const handleFirstPage = useCallback(() => {
    setCursor(null);
    setCursorHistory([]);
    setCurrentPage(1);
    fetchData(null, true);
  }, [fetchData]);

  const metricLabel = useMemo(
    () => metricOptions.find((m) => m.value === metric)?.label,
    [metric]
  );

  const chartData = useMemo(() => {
    if (!apiResponse) return [];

    const sampledData = downsample(apiResponse.data, 1000);
    return sampledData.map((point) => {
      const timestamp = new Date(point.timestamp).getTime();
      const isAggregated =
        point.aggregation_level && point.aggregation_level !== "raw";

      return {
        timestamp,
        participant_id: point.participant_id,
        value: isAggregated ? point.avg_value : point.value,
        min_value: point.min_value,
        max_value: point.max_value,
        date: new Date(timestamp).toLocaleDateString(),
        isAggregated,
      };
    });
  }, [apiResponse]);

  const formatTooltipDate = useCallback((timestamp: number) => {
    return (
      new Date(timestamp).toLocaleDateString() +
      " " +
      new Date(timestamp).toLocaleTimeString()
    );
  }, []);

  const tickFormatter = useCallback((timestamp: number) => {
    return new Date(timestamp).toLocaleDateString();
  }, []);

  const getAggregationDescription = (level: string) => {
    const descriptions = {
      raw: "Raw data points (highest resolution)",
      "1m": "1-minute aggregated data",
      "1h": "1-hour aggregated data",
      "1d": "1-day aggregated data",
    };
    return descriptions[level as keyof typeof descriptions] || level;
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 mb-6">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Metric
            </label>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select metric...</option>
              {metricOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <User className="w-4 h-4" />
              User IDs
            </label>
            <input
              type="text"
              value={userIds}
              onChange={(e) => setUserIds(e.target.value)}
              placeholder="1,2,3 or single ID"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Aggregation
            </label>
            <select
              value={aggregation}
              onChange={(e) => setAggregation(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {aggregationOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Limit
            </label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              min="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => fetchData(null, true)}
            disabled={loading}
            className="flex-1 md:flex-none px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading ? "Loading..." : "Fetch Data"}
          </button>

          {apiResponse && (
            <div className="flex gap-2">
              <button
                onClick={handleFirstPage}
                disabled={loading || currentPage === 1}
                className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="First Page"
              >
                First
              </button>
              <button
                onClick={handlePreviousPage}
                disabled={loading || currentPage === 1}
                className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
                Prev
              </button>
              <div className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md flex items-center">
                Page {currentPage}
              </div>
              <button
                onClick={handleNextPage}
                disabled={loading || !apiResponse?.metadata.next_cursor}
                className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                title="Next Page"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-md">
            {error}
          </div>
        )}

        {dataStats && (
          <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 space-y-2">
            <div className="flex items-center gap-2 font-medium text-gray-800">
              <Info className="w-4 h-4" />
              Data Summary
            </div>
            <div>Participant IDs: {dataStats.participant_ids.join(", ")}</div>
            <div>
              Date Range: {dataStats.start_date} to {dataStats.end_date}
            </div>
            <div>Query Span: {dataStats.query_span_days} days</div>
            <div>
              Recommended Aggregation: {dataStats.recommended_aggregation}
            </div>
            <div className="space-y-1">
              <div>Available Data Points:</div>
              <ul className="list-disc list-inside ml-4">
                <li>Raw: {dataStats.data_counts.raw.toLocaleString()}</li>
                <li>1m: {dataStats.data_counts["1m"].toLocaleString()}</li>
                <li>1h: {dataStats.data_counts["1h"].toLocaleString()}</li>
                <li>1d: {dataStats.data_counts["1d"].toLocaleString()}</li>
              </ul>
            </div>
          </div>
        )}
      </div>

      {apiResponse && (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">
              Query Results
            </h2>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-600">
                Page {currentPage} • {apiResponse.metadata.total_points} points
              </div>
              {apiResponse.metadata.next_cursor && (
                <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                  More data available
                </div>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="font-medium text-gray-700">Aggregation Level</div>
              <div className="text-gray-600">
                {apiResponse.metadata.aggregation_level}
              </div>
            </div>
            <div>
              <div className="font-medium text-gray-700">Query Span</div>
              <div className="text-gray-600">
                {apiResponse.metadata.query_span_days} days
              </div>
            </div>
            <div>
              <div className="font-medium text-gray-700">Participants</div>
              <div className="text-gray-600">
                {apiResponse.metadata.participant_ids.join(", ")}
              </div>
            </div>
            <div>
              <div className="font-medium text-gray-700">Next Cursor</div>
              <div className="text-gray-600">
                {apiResponse.metadata.next_cursor ? "Available" : "None"}
              </div>
            </div>
          </div>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            {metricLabel} over Time
          </h2>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={tickFormatter}
                  tickCount={8}
                />
                <YAxis
                  label={{ value: "Value", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  labelFormatter={(timestamp) => formatTooltipDate(timestamp)}
                  formatter={(value, _, props) => [
                    value,
                    `${metricLabel || "Metric"} (ID: ${
                      props.payload.participant_id
                    })`,
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: "#6366f1" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          {apiResponse?.metadata.aggregation_level && (
            <div className="mt-4 text-sm text-gray-600 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Aggregation:{" "}
              {getAggregationDescription(
                apiResponse.metadata.aggregation_level
              )}
            </div>
          )}
        </div>
      )}

      {chartData.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <div className="text-gray-400 mb-4">
            <Activity className="w-16 h-16 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Data Yet
          </h3>
          <p className="text-gray-500">
            Select your parameters and click "Fetch Data" to see your metrics
          </p>
        </div>
      )}
    </div>
  );
}

export default Metrics;
