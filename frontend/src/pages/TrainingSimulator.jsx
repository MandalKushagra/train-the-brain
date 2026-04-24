import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { getTrainingSession, completeStep, recordWrong, completeTraining } from '../api'

export default function TrainingSimulator() {
  const { token } = useParams()
  const [session, setSession] = useState(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [phase, setPhase] = useState('loading') // loading | training | quiz | done
  const [error, setError] = useState(null)
  const stepStartRef = useRef(Date.now())

  // Quiz state
  const [quizIndex, setQuizIndex] = useState(0)
  const [quizAnswers, setQuizAnswers] = useState([])
  const [selectedOption, setSelectedOption] = useState(null)
  const [showFeedback, setShowFeedback] = useState(false)

  useEffect(() => {
    loadSession()
  }, [token])

  async function loadSession() {
    try {
      const data = await getTrainingSession(token)
      setSession(data)
      setCurrentStep(data.current_step || 0)
      setPhase('training')
    } catch (err) {
      setError('Training link not found or expired.')
    }
  }

  const steps = session?.manifest?.steps || []
  const questions = session?.assessment?.questions || []
  const step = steps[currentStep]

  async function handleCorrectAction() {
    const timeSpent = (Date.now() - stepStartRef.current) / 1000
    await completeStep(token, step.step_id, timeSpent)

    if (currentStep + 1 >= steps.length) {
      setPhase('quiz')
    } else {
      setCurrentStep(currentStep + 1)
      stepStartRef.current = Date.now()
    }
  }

  async function handleWrongAction() {
    await recordWrong(token, step.step_id)
  }

  function handleQuizAnswer(optionIndex) {
    setSelectedOption(optionIndex)
    setShowFeedback(true)
    const newAnswers = [...quizAnswers, optionIndex]
    setQuizAnswers(newAnswers)

    setTimeout(() => {
      setShowFeedback(false)
      setSelectedOption(null)
      if (quizIndex + 1 >= questions.length) {
        finishQuiz(newAnswers)
      } else {
        setQuizIndex(quizIndex + 1)
      }
    }, 1500)
  }

  async function finishQuiz(answers) {
    const correct = answers.filter((a, i) => a === questions[i]?.correct).length
    const score = correct / questions.length
    const passed = score >= (session?.assessment?.pass_threshold || 0.6)
    await completeTraining(token, score, passed, answers)
    setSession((s) => ({ ...s, quizScore: score, quizPassed: passed }))
    setPhase('done')
  }

  // ── Loading ──────────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        {error ? (
          <p className="text-red-400 text-lg">{error}</p>
        ) : (
          <div className="text-center">
            <div className="text-4xl mb-4 animate-bounce">🧠</div>
            <p className="text-gray-400">Loading training...</p>
          </div>
        )}
      </div>
    )
  }

  // ── Training steps ───────────────────────────────────────────
  if (phase === 'training' && step) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex flex-col">
        {/* Progress bar */}
        <div className="bg-gray-900 px-4 py-3 flex items-center gap-3">
          <span className="text-lg">🧠</span>
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>{session.workflow_name}</span>
              <span>Step {currentStep + 1} of {steps.length}</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5">
              <div
                className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Step content */}
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-10">
          {/* Screen indicator */}
          <div className="mb-6 px-4 py-1.5 bg-gray-800 rounded-full text-xs text-gray-400">
            📱 {step.screen}
          </div>

          {/* Title + instruction */}
          <h2 className="text-2xl font-bold mb-2 text-center">{step.title}</h2>
          <p className="text-lg text-indigo-300 mb-6 text-center">{step.instruction}</p>

          {/* Narration */}
          <div className="max-w-md bg-gray-900 border border-gray-800 rounded-xl p-5 mb-8">
            <p className="text-sm text-gray-300 leading-relaxed">💬 {step.narration}</p>
          </div>

          {/* Highlight element */}
          <div className="mb-8">
            <div className="relative inline-block">
              <div className="bg-gray-800 border-2 border-indigo-500 rounded-xl px-8 py-4 animate-pulse">
                <p className="text-xs text-gray-500 mb-1">Tap target</p>
                <p className="text-sm font-mono text-indigo-300">{step.highlight_element}</p>
              </div>
              <div className="absolute -inset-2 border-2 border-indigo-400/30 rounded-2xl animate-ping" />
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleCorrectAction}
              className="bg-green-600 hover:bg-green-500 text-white px-8 py-3 rounded-xl font-medium transition-colors text-sm"
            >
              ✅ {step.expected_action === 'TAP' ? 'Tap' :
                  step.expected_action === 'TYPE' ? 'Type' :
                  step.expected_action === 'SCAN' ? 'Scan' :
                  step.expected_action === 'VERIFY' ? 'Verify' :
                  step.expected_action} Done
            </button>
            <button
              onClick={handleWrongAction}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-6 py-3 rounded-xl text-sm transition-colors"
            >
              ❓ I'm stuck
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Quiz ─────────────────────────────────────────────────────
  if (phase === 'quiz' && questions[quizIndex]) {
    const q = questions[quizIndex]
    return (
      <div className="min-h-screen bg-gray-950 text-white flex flex-col">
        <div className="bg-gray-900 px-4 py-3 flex items-center gap-3">
          <span className="text-lg">🧠</span>
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Quiz</span>
              <span>Question {quizIndex + 1} of {questions.length}</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5">
              <div
                className="bg-purple-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${((quizIndex + 1) / questions.length) * 100}%` }}
              />
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center px-6 py-10">
          <h2 className="text-xl font-bold mb-8 text-center max-w-lg">{q.question}</h2>
          <div className="w-full max-w-md space-y-3">
            {q.options.map((opt, i) => {
              let bg = 'bg-gray-900 border-gray-700 hover:border-indigo-500'
              if (showFeedback && i === q.correct) bg = 'bg-green-900/30 border-green-500'
              else if (showFeedback && i === selectedOption && i !== q.correct) bg = 'bg-red-900/30 border-red-500'

              return (
                <button
                  key={i}
                  onClick={() => !showFeedback && handleQuizAnswer(i)}
                  disabled={showFeedback}
                  className={`w-full text-left px-5 py-3.5 rounded-xl border ${bg} transition-colors text-sm`}
                >
                  <span className="text-gray-500 mr-3">{String.fromCharCode(65 + i)}.</span>
                  {opt}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // ── Done ─────────────────────────────────────────────────────
  if (phase === 'done') {
    const score = session.quizScore
    const passed = session.quizPassed
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-6">{passed ? '🎉' : '📚'}</div>
          <h1 className="text-3xl font-bold mb-2">
            {passed ? 'Training Complete!' : 'Training Finished'}
          </h1>
          <p className="text-gray-400 mb-8">
            {passed
              ? 'Great job! You passed the assessment.'
              : 'You completed the training but didn\'t pass the quiz. Consider retaking it.'}
          </p>
          <div className={`inline-block text-5xl font-bold mb-2 ${passed ? 'text-green-400' : 'text-yellow-400'}`}>
            {Math.round(score * 100)}%
          </div>
          <p className="text-sm text-gray-500">Quiz Score</p>
          <div className="mt-8">
            <p className="text-xs text-gray-600">
              {session.workflow_name} • {steps.length} steps • {questions.length} questions
            </p>
          </div>
        </div>
      </div>
    )
  }

  return null
}
