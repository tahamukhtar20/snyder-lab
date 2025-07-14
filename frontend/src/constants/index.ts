import type { MetricOption } from "../types";

const metricOptions: MetricOption[] = [
  { value: "heart_rate", label: "Heart Rate" },
];

const aggregationOptions = [
  { value: "", label: "Auto (Recommended)" },
  { value: "raw", label: "Raw Data" },
  { value: "1m", label: "1-Minute Aggregates" },
  { value: "1h", label: "1-Hour Aggregates" },
  { value: "1d", label: "1-Day Aggregates" },
];

const statusColors = {
  good: "#10b981",
  low_adherence: "#f59e0b",
  low_sleep: "#f59e0b",
  no_data_48h: "#ef4444",
  no_token: "#ef4444",
};

const statusLabels = {
  good: "Good",
  low_adherence: "Low Adherence",
  low_sleep: "Low Sleep Upload",
  no_data_48h: "No Data 48h",
  no_token: "No Token",
};

export { metricOptions, aggregationOptions, statusColors, statusLabels };
