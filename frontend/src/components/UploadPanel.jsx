import { useState, useEffect, useRef } from 'react'
import { startPipeline, getJobStatus } from '../api'

export default function UploadPanel({ onJobCreated, onJobCompleted }) {
  const [workflowName, setWorkflowName] = useState('')
  const [prdText, setPrdText] = useState('')
  const [codeText, setCodeText] = useState('')
  const [figmaDesc, setFigmaDesc] = useState('')
  const [prdFile, setPrdFile] = useState(null)
  const [codeFile, setCodeFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  // Poll job status
  useEffect(() => {
    if (!jobId || status === 'completed' || status === 'failed') return
    pollRef.current = setInterval(async () => {
      try {
        const data = await getJobStatus(jobId)
        setStatus(data.status)
        if (data.status === 'completed') {
          clearInterval(pollRef.current)
          onJobCompleted?.(jobId)
        }
        if (data.status === 'failed') {
          clearInterval(pollRef.current)
          setError(data.error_message || 'Pipeline failed')
        }
      } catch {}
    }, 2000)
    return () => clearInterval(pollRef.current)
  }, [jobId, status])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('workflow_name', workflowName || 'Training Flow')
      if (prdFile) fd.append('prd_file', prdFile)
      else if (prdText) fd.append('prd_text', prdText)
      if (codeFile) fd.append('code_file', codeFile)
      else if (codeText) fd.append('code_text', codeText)
      if (figmaDesc) fd.append('figma_description', figmaDesc)

      const data = await startPipeline(fd)
      setJobId(data.job_id)
      setStatus('pending')
      onJobCreated?.(data.job_id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const statusColors = {
    pending: 'text-yellow-400',
    processing: 'text-blue-400',
    completed: 'text-green-400',
    failed: 'text-red-400',
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Workflow name */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Workflow Name</label>
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="e.g. FTG Dimension Capture"
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* PRD */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">PRD / Requirements</label>
          <div className="flex gap-3 items-start">
            <textarea
              value={prdText}
              onChange={(e) => setPrdText(e.target.value)}
              placeholder="Paste PRD text here..."
              rows={5}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
            <div className="text-center">
              <span className="text-xs text-gray-500 block mb-1">or upload</span>
              <label className="cursor-pointer inline-block bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-sm">
                {prdFile ? prdFile.name : '📄 File'}
                <input type="file" className="hidden" accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => setPrdFile(e.target.files[0])} />
              </label>
            </div>
          </div>
        </div>

        {/* Code */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Source Code</label>
          <div className="flex gap-3 items-start">
            <textarea
              value={codeText}
              onChange={(e) => setCodeText(e.target.value)}
              placeholder="Paste source code here..."
              rows={5}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
            />
            <div className="text-center">
              <span className="text-xs text-gray-500 block mb-1">or upload</span>
              <label className="cursor-pointer inline-block bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-sm">
                {codeFile ? codeFile.name : '💻 File'}
                <input type="file" className="hidden" accept=".kt,.java,.py,.js,.ts,.txt"
                  onChange={(e) => setCodeFile(e.target.files[0])} />
              </label>
            </div>
          </div>
        </div>

        {/* Figma */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Figma / Screenshot Description (optional)</label>
          <textarea
            value={figmaDesc}
            onChange={(e) => setFigmaDesc(e.target.value)}
            placeholder="Describe the screens from Figma..."
            rows={3}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || status === 'processing'}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium py-3 rounded-lg transition-colors"
        >
          {loading ? 'Submitting...' : status === 'processing' ? 'Pipeline Running...' : '🚀 Generate Training'}
        </button>
      </form>

      {/* Status */}
      {jobId && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Job ID</span>
            <code className="text-sm text-indigo-300 bg-gray-800 px-2 py-0.5 rounded">{jobId}</code>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Status</span>
            <span className={`text-sm font-medium ${statusColors[status] || 'text-gray-300'}`}>
              {status === 'processing' && '⏳ '}{status === 'completed' && '✅ '}{status === 'failed' && '❌ '}
              {status?.toUpperCase()}
            </span>
          </div>
          {status === 'processing' && (
            <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
              <div className="bg-indigo-500 h-full rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
          )}
          {error && <p className="text-sm text-red-400 mt-2">{error}</p>}
        </div>
      )}
    </div>
  )
}
