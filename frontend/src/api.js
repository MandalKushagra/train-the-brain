const BASE = ''  // proxied by vite in dev

export async function startPipeline(formData) {
  const res = await fetch(`${BASE}/pipeline/start`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}

export async function getJobStatus(jobId) {
  const res = await fetch(`${BASE}/pipeline/${jobId}`)
  if (!res.ok) throw new Error('Job not found')
  return res.json()
}

export async function getJobResult(jobId) {
  const res = await fetch(`${BASE}/pipeline/${jobId}/result`)
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}

export async function assignUsers(jobId, users, assignedBy) {
  const res = await fetch(`${BASE}/training/${jobId}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ users, assigned_by: assignedBy }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
  return res.json()
}

export async function getTrainingSession(token) {
  const res = await fetch(`${BASE}/training/link/${token}`)
  if (!res.ok) throw new Error('Training link not found')
  return res.json()
}

export async function completeStep(token, stepId, timeSpent) {
  const res = await fetch(`${BASE}/training/link/${token}/step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ step_id: stepId, time_spent_sec: timeSpent }),
  })
  return res.json()
}

export async function recordWrong(token, stepId) {
  const res = await fetch(`${BASE}/training/link/${token}/wrong`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ step_id: stepId }),
  })
  return res.json()
}

export async function completeTraining(token, quizScore, quizPassed, quizAnswers) {
  const res = await fetch(`${BASE}/training/link/${token}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quiz_score: quizScore, quiz_passed: quizPassed, quiz_answers: quizAnswers }),
  })
  return res.json()
}

export async function getProgress(jobId) {
  const res = await fetch(`${BASE}/training/${jobId}/progress`)
  if (!res.ok) throw new Error('No progress found')
  return res.json()
}

export async function getStats(jobId) {
  const res = await fetch(`${BASE}/training/${jobId}/stats`)
  if (!res.ok) throw new Error('No stats found')
  return res.json()
}
