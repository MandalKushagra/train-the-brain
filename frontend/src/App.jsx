import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import AssignPanel from './components/AssignPanel'
import DashboardPanel from './components/DashboardPanel'

const TABS = ['Upload & Generate', 'Assign Users', 'Dashboard']

export default function App() {
  const [tab, setTab] = useState(0)
  const [jobId, setJobId] = useState('')
  const [jobStatus, setJobStatus] = useState(null)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <span className="text-3xl">🧠</span>
          <div>
            <h1 className="text-xl font-bold text-white">Train the Brain</h1>
            <p className="text-sm text-gray-400">AI-powered interactive training generator</p>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-5xl mx-auto px-6 pt-6">
        <div className="flex gap-1 bg-gray-900 rounded-lg p-1">
          {TABS.map((t, i) => (
            <button
              key={t}
              onClick={() => setTab(i)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                tab === i
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-6 py-6">
        {tab === 0 && (
          <UploadPanel
            onJobCreated={(id) => { setJobId(id); setJobStatus('pending') }}
            onJobCompleted={(id) => { setJobId(id); setJobStatus('completed'); setTab(1) }}
          />
        )}
        {tab === 1 && <AssignPanel jobId={jobId} onJobIdChange={setJobId} />}
        {tab === 2 && <DashboardPanel jobId={jobId} onJobIdChange={setJobId} />}
      </main>
    </div>
  )
}
