import { useState, useMemo, useCallback } from 'react'
import { Calendar, Activity, User } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

type MetricOption = {
  value: string
  label: string
}

type DataPoint = {
  metric_type: string
  participant_id: string
  value: number
  timestamp: number
}

const metricOptions: MetricOption[] = [
  { value: 'heart_rate', label: 'Heart Rate' },
]

function downsample(data: DataPoint[], maxPoints = 500): DataPoint[] {
  if (data.length <= maxPoints) return data
  const sampled: DataPoint[] = []
  const step = Math.floor(data.length / maxPoints)
  for (let i = 0; i < data.length; i += step) {
    sampled.push(data[i])
  }
  return sampled
}

function App() {
  const [metric, setMetric] = useState('heart_rate')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-01-02')
  const [userId, setUserId] = useState('1')
  const [data, setData] = useState<DataPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    if (!metric || !startDate || !endDate || !userId) {
      setError('Please fill in all fields')
      return
    }
    setLoading(true)
    setError('')

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/data?metric=${metric}&start_date=${startDate}&end_date=${endDate}&user_id=${userId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      )

      if (!res.ok) throw new Error()

      const result = await res.json()

      const formattedData: DataPoint[] = result.map(
        (item: Pick<DataPoint, 'timestamp' | 'value'>) => ({
          ...item,
          timestamp: new Date(item.timestamp).getTime(),
        })
      )

      setData(formattedData)
    } catch {
      setError('Failed to fetch data. Please check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }, [metric, startDate, endDate, userId])

  const metricLabel = useMemo(
    () => metricOptions.find(m => m.value === metric)?.label,
    [metric]
  )

  const chartData = useMemo(() => {
    const sampledData = downsample(data, 500)
    return sampledData.map(point => ({
      timestamp: point.timestamp,
      value: point.value,
      date: new Date(point.timestamp).toLocaleDateString(),
    }))
  }, [data])

  const formatTooltipDate = useCallback((timestamp: number) => {
    return (
      new Date(timestamp).toLocaleDateString() +
      ' ' +
      new Date(timestamp).toLocaleTimeString()
    )
  }, [])

  const tickFormatter = useCallback((timestamp: number) => {
    return new Date(timestamp).toLocaleDateString()
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2 flex items-center gap-2">
            Fitbit Dashboard
          </h1>
          <p className="text-gray-600">
            Monitor and visualize your health metrics over time
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Metric
              </label>
              <select
                value={metric}
                onChange={e => setMetric(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select metric...</option>
                {metricOptions.map(option => (
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
                onChange={e => setStartDate(e.target.value)}
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
                onChange={e => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <User className="w-4 h-4" />
                User ID
              </label>
              <input
                type="text"
                value={userId}
                onChange={e => setUserId(e.target.value)}
                placeholder="Enter user ID..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            onClick={fetchData}
            disabled={loading}
            className="w-full md:w-auto px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Loading...' : 'Fetch Data'}
          </button>

          {error && (
            <div className="mt-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-md">
              {error}
            </div>
          )}
        </div>

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
                    domain={['dataMin', 'dataMax']}
                    tickFormatter={tickFormatter}
                    tickCount={8}
                  />
                  <YAxis label={{ value: 'Value', angle: -90, position: 'insideLeft' }} />
                  <Tooltip
                    labelFormatter={timestamp => formatTooltipDate(timestamp)}
                    formatter={value => [value, metricLabel || 'Metric']}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, fill: '#6366f1' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {chartData.length === 0 && !loading && (
          <div className="bg-white rounded-lg shadow-lg p-12 text-center">
            <div className="text-gray-400 mb-4">
              <Activity className="w-16 h-16 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Data Yet</h3>
            <p className="text-gray-500">
              Select your parameters and click "Fetch Data" to see your metrics
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
