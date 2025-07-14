import type { DataPoint } from "../types";

function downsample(data: DataPoint[], maxPoints = 1000): DataPoint[] {
  if (data.length <= maxPoints) return data;
  const sampled: DataPoint[] = [];
  const step = Math.floor(data.length / maxPoints);
  for (let i = 0; i < data.length; i += step) {
    sampled.push(data[i]);
  }
  return sampled;
}

export { downsample };
