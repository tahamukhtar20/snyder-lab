type MetricOption = {
  value: string;
  label: string;
};

type DataPoint = {
  participant_id: number;
  timestamp: string;
  value?: number;
  metric_type?: string;
  avg_value?: number;
  min_value?: number;
  max_value?: number;
  aggregation_level?: string;
};

type ApiResponse = {
  data: DataPoint[];
  metadata: {
    aggregation_level: string;
    query_span_days: number;
    total_points: number;
    participant_ids: number[];
    start_date: string;
    end_date: string;
    next_cursor?: string;
  };
};

type DataStats = {
  query_span_days: number;
  recommended_aggregation: string;
  data_counts: {
    raw: number;
    "1m": number;
    "1h": number;
    "1d": number;
  };
  participant_ids: number[];
  start_date: string;
  end_date: string;
};

type AdherenceStatus =
  | "no_token"
  | "no_data_48h"
  | "low_sleep"
  | "low_adherence"
  | "good";

type Participant = {
  participant_id: number;
  name: string;
  token: string;
};

type AdherenceItem = {
  participant_id: number;
  name: string;
  status: AdherenceStatus;
  last_data_timestamp?: string;
  adherence_percentage: number;
  sleep_upload_percentage: number;
  details: string;
};

type AdherenceResponse = {
  participants: AdherenceItem[];
  total_participants: number;
  issues_count: number;
};

type DashboardSummary = {
  total_participants: number;
  active_participants: number;
  total_data_points: number;
  data_date_range: {
    start_date: string;
    end_date: string;
  } | null;
  system_status: string;
};

type ParticipantMetrics = {
  participant_id: number;
  participant_name: string;
  date_range: {
    start_date: string;
    end_date: string;
  };
  heart_rate_summary: {
    avg_hr: number;
    min_hr: number;
    max_hr: number;
    total_points: number;
  };
  daily_summaries: Array<{
    date: string;
    resting_heart_rate: number;
  }>;
  heart_rate_zones: Array<{
    zone_name: string;
    avg_minutes: number;
    avg_calories: number;
  }>;
};

export type {
    MetricOption,
    DataPoint,
    ApiResponse,
    DataStats,
    AdherenceStatus,
    Participant,
    AdherenceItem,
    AdherenceResponse,
    DashboardSummary,
    ParticipantMetrics
};