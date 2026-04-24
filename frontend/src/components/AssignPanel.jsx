import { useState } from 'react'
import { assignUsers } from '../api'

export default function AssignPanel({ jobId: initialJobId, onJobIdChange }) {
  const [jobId, setJobId] = useState(initialJobId || '')
  const [assignedBy, setAssignedBy] = useState('')
  const [rows, setRows] = useState([{ user_name: '', user_email: '' }])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  function addRow() {
    setRows([...rows, { user_name: '', user_email: '' }])
  }

  function updateRow(i, field, val) {
    const next = [...rows]
    next[i] = { ...next[i], [field]: val }
    setRows(next)
  }

  function removeRow(i) {
    if (rows.length <= 1) return
    setRows(rows.filter((_, idx) => idx !== i))
  }

  async function handleAssign(e) {
    e.preventDefault()
    setError(null)
    setResult(null)
    const users = rows.filter((r) => r.user_name.trim())
    if (!users.length) { setError('Add at least one user'); return }
    if (!jobId.trim()) { setError('Enter a Job ID'); return }

    setLoading(true)
    try {
      const data = await assignUsers(jobId.trim(), users, assignedBy || undefined)
      setResult(data)
      onJobIdChange?.(jobId.trim())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function copyLink(url) {
    const full = `${window.location.origin}${url}`
    navigator.clipboard.writeText(full)
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleAssign} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Job ID</label>
            <input
              type="text" value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              placeholder="Paste job ID from upload step"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Assigned By</label>
            <input
              type="text" value={assignedBy}
              onChange={(e) => setAssignedBy(e.target.value)}
              placeholder="Your name"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Users to Assign</label>
          <div className="space-y-2">
            {rows.map((r, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text" value={r.user_name}
                  onChange={(e) => updateRow(i, 'user_name', e.target.value)}
                  placeholder="Name"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
                <input
                  type="email" value={r.user_email}
                  onChange={(e) => updateRow(i, 'user_email', e.target.value)}
                  placeholder="Email (optional)"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
                <button type="button" onClick={() => removeRow(i)}
                  className="text-gray-500 hover:text-red-400 px-2">✕</button>
              </div>
            ))}
          </div>
          <button type="button" onClick={addRow}
            className="mt-2 text-sm text-indigo-400 hover:text-indigo-300">+ Add another user</button>
        </div>

        <button type="submit" disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 text-white font-medium py-3 rounded-lg transition-colors">
          {loading ? 'Assigning...' : '📨 Assign & Generate Links'}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {result && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800">
            <h3 className="text-sm font-medium text-gray-300">
              Assigned to {result.workflow_name}
            </h3>
          </div>
          <div className="divide-y divide-gray-800">
            {result.assigned.map((u) => (
              <div key={u.token} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-white">{u.user_name}</p>
                  <p className="text-xs text-gray-500 font-mono">{u.token}</p>
                </div>
                <div className="flex gap-2">
                  <a
                    href={u.training_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs bg-indigo-600/20 text-indigo-300 px-3 py-1.5 rounded-md hover:bg-indigo-600/30"
                  >
                    Open
                  </a>
                  <button
                    onClick={() => copyLink(u.training_url)}
                    className="text-xs bg-gray-800 text-gray-300 px-3 py-1.5 rounded-md hover:bg-gray-700"
                  >
                    Copy Link
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
