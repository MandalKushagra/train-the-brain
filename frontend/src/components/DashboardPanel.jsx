import { useState } from 'react'
import { getProgress, getStats } from '../api'

export default function DashboardPanel({ jobId: initialJobId, onJobIdChange }) {
  const [jobId, setJobId] = useState(initialJobId || '')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleLoad() {
    if (!jobId.trim()) return
    setError(null)
    setLoading(true)
    try {
      const [s, u] = await Promise.all([
        getStats(jobId.trim()).catch(() => null),
        getProgress(jobId.trim()).catch(() => []),
      ])
      setStats(s)
      setUsers(u)
      onJobIdChange?.(jobId.trim())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const statusBadge = (s) => {
    const colors = {
      completed: 'bg-green-500/20 text-green-300',
      in_progress: 'bg-blue-500/20 text-blue-300',
      pending: 'bg-yellow-500/20 text-yellow-300',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${colors[s] || 'bg-gray-700 text-gray-300'}`}>
        {s}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Job ID input */}
      <div className="flex gap-3">
        <input
          type="text" value={jobId}
          onChange={(e) => setJobId(e.target.value)}
          placeholder="Enter Job ID"
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
          onKeyDown={(e) => e.key === 'Enter' && handleLoad()}
        />
        <button onClick={handleLoad} disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors">
          {loading ? '...' : '📊 Load'}
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Total Assigned" value={stats.total_assigned} />
          <StatCard label="Completed" value={stats.completed} color="text-green-400" />
          <StatCard label="In Progress" value={stats.in_progress} color="text-blue-400" />
          <StatCard label="Pending" value={stats.pending} color="text-yellow-400" />
          <StatCard label="Completion Rate" value={`${stats.completion_rate}%`} />
          <StatCard label="Avg Quiz Score" value={stats.avg_quiz_score != null ? `${Math.round(stats.avg_quiz_score * 100)}%` : '—'} />
          <StatCard label="Quiz Pass Rate" value={stats.quiz_pass_rate != null ? `${stats.quiz_pass_rate}%` : '—'} />
        </div>
      )}

      {/* User table */}
      {users && users.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left px-4 py-3 font-medium">User</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Progress</th>
                <th className="text-left px-4 py-3 font-medium">Quiz</th>
                <th className="text-left px-4 py-3 font-medium">Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {users.map((u) => (
                <tr key={u.token} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3">
                    <p className="text-white">{u.user_name}</p>
                    {u.user_email && <p className="text-xs text-gray-500">{u.user_email}</p>}
                  </td>
                  <td className="px-4 py-3">{statusBadge(u.status)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-indigo-500 h-full rounded-full transition-all"
                          style={{ width: `${u.progress_pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 w-16 text-right">
                        {u.current_step}/{u.total_steps}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {u.quiz_score != null ? (
                      <span className={u.quiz_passed ? 'text-green-400' : 'text-red-400'}>
                        {Math.round(u.quiz_score * 100)}%
                      </span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={`/training/link/${u.token}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      Open ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
