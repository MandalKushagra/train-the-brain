import { useState, useRef } from "react";

type QuizState = {
  active: boolean;
  questionIndex: number;
  questions: typeof manifest.quiz_breaks[0]["questions"];
  score: number;
  answered: boolean;
  selectedOption: number | null;
};

export default function Simulator({ manifest, onBack }: { manifest: any; onBack: () => void }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [showError, setShowError] = useState(false);
  const [showTip, setShowTip] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [totalScore, setTotalScore] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [quiz, setQuiz] = useState<QuizState>({
    active: false, questionIndex: 0, questions: [], score: 0, answered: false, selectedOption: null,
  });
  const imgRef = useRef<HTMLDivElement>(null);
  const step = manifest.steps[currentStep];
  if (!step && !completed) return null;

  function handleScreenClick(e: React.MouseEvent) {
    if (quiz.active || completed) return;
    const rect = imgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const xPct = ((e.clientX - rect.left) / rect.width) * 100;
    const yPct = ((e.clientY - rect.top) / rect.height) * 100;
    const t = step.tap_target;
    if (xPct >= t.x && xPct <= t.x + t.width && yPct >= t.y && yPct <= t.y + t.height) {
      setShowError(false);
      setShowTip(false);
      goNext();
    } else {
      setShowError(true);
      setTimeout(() => setShowError(false), 2500);
    }
  }

  function goNext() {
    const quizBreak = manifest.quiz_breaks.find(q => q.after_step === step.step_id);
    if (quizBreak) {
      setQuiz({ active: true, questionIndex: 0, questions: quizBreak.questions, score: 0, answered: false, selectedOption: null });
    } else if (currentStep + 1 >= manifest.steps.length) {
      setCompleted(true);
    } else {
      setCurrentStep(currentStep + 1);
      setShowTip(false);
    }
  }

  function handleQuizAnswer(i: number) {
    if (quiz.answered) return;
    const correct = quiz.questions[quiz.questionIndex].correct === i;
    setQuiz(q => ({ ...q, answered: true, selectedOption: i, score: q.score + (correct ? 1 : 0) }));
  }

  function handleQuizNext() {
    const nextQ = quiz.questionIndex + 1;
    if (nextQ < quiz.questions.length) {
      setQuiz(q => ({ ...q, questionIndex: nextQ, answered: false, selectedOption: null }));
    } else {
      setTotalScore(s => s + quiz.score);
      setTotalQuestions(t => t + quiz.questions.length);
      if (currentStep + 1 >= manifest.steps.length) { setCompleted(true); }
      else { setCurrentStep(currentStep + 1); }
      setQuiz({ active: false, questionIndex: 0, questions: [], score: 0, answered: false, selectedOption: null });
    }
  }

  if (completed) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl p-8 max-w-sm w-full text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold mb-2">Training Complete!</h2>
          <p className="text-gray-500 mb-6">{manifest.workflow_name}</p>
          <div className="bg-green-50 rounded-xl p-6 mb-6">
            <p className="text-4xl font-bold text-green-600">{totalScore}/{totalQuestions}</p>
            <p className="text-sm text-green-700 mt-1">Quiz Score</p>
          </div>
          <button onClick={() => { setCurrentStep(0); setCompleted(false); setTotalScore(0); setTotalQuestions(0); }}
            className="bg-blue-600 text-white px-6 py-3 rounded-xl w-full font-semibold text-lg mb-2">
            Restart Training
          </button>
          <button onClick={onBack}
            className="bg-gray-200 text-gray-700 px-6 py-3 rounded-xl w-full font-semibold text-lg">
            Back to Menu
          </button>
        </div>
      </div>
    );
  }

  const t = step.tap_target;
  const q = quiz.active ? quiz.questions[quiz.questionIndex] : null;
  const arrowX = t.x + t.width / 2;
  const arrowY = t.y - 4;

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-start py-4 px-2">
      {/* Progress bar */}
      <div className="max-w-sm w-full mb-2">
        <div className="flex items-center justify-between text-white text-xs opacity-60 mb-1">
          <span>Step {step.step_id} of {manifest.steps.length}</span>
          <span>{step.title}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${(step.step_id / manifest.steps.length) * 100}%` }} />
        </div>
      </div>

      {/* Instruction card ABOVE the screenshot */}
      <div className="max-w-sm w-full bg-blue-600 rounded-t-xl px-4 py-3">
        <p className="text-white text-base font-semibold leading-snug">
          👆 {step.instruction}
        </p>
      </div>

      {/* Phone frame with screenshot */}
      <div ref={imgRef} className="relative max-w-sm w-full cursor-pointer" onClick={handleScreenClick}>
        <img src={step.screenshot} alt={step.screen}
          className="w-full select-none pointer-events-none rounded-b-xl" draggable={false} />

        {/* Tap target outline */}
        <div className="absolute rounded-lg pointer-events-none"
          style={{
            left: `${t.x}%`, top: `${t.y}%`, width: `${t.width}%`, height: `${t.height}%`,
            border: '2px solid rgba(59, 130, 246, 0.6)',
            boxShadow: '0 0 15px rgba(59, 130, 246, 0.4), inset 0 0 8px rgba(59, 130, 246, 0.15)',
          }} />

        {/* Animated arrow */}
        <div className="absolute pointer-events-none flex flex-col items-center"
          style={{ left: `${arrowX}%`, top: `${arrowY}%`, transform: 'translate(-50%, -100%)' }}>
          <div className="animate-bounce">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M12 4v12m0 0l-4-4m4 4l4-4" stroke="#3B82F6" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>

        {/* Error toast */}
        {showError && (
          <div className="absolute top-4 left-4 right-4 bg-red-500 text-white px-4 py-3 rounded-xl text-sm font-semibold shadow-lg animate-bounce">
            ❌ {step.on_wrong_action}
          </div>
        )}
      </div>

      {/* Floating tip bar BELOW screenshot */}
      {step.tip && (
        <div className="max-w-sm w-full mt-2">
          <button onClick={() => setShowTip(!showTip)}
            className={`w-full text-left rounded-xl px-4 py-3 transition-all ${
              showTip ? 'bg-yellow-100 border-2 border-yellow-400' : 'bg-gray-800 border border-gray-700'
            }`}>
            <div className="flex items-center gap-2">
              <span className="text-lg">💡</span>
              <span className={`text-sm font-medium ${showTip ? 'text-yellow-900' : 'text-gray-300'}`}>
                {showTip ? step.tip : "Tap here for a helpful tip"}
              </span>
            </div>
          </button>
        </div>
      )}

      {/* Quiz overlay */}
      {quiz.active && q && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm">
            <p className="text-sm text-blue-600 font-bold mb-1">📝 Quick Check!</p>
            <p className="font-semibold text-lg mb-4">{q.question}</p>
            <div className="space-y-2">
              {q.options.map((opt, i) => (
                <button key={i} onClick={() => handleQuizAnswer(i)}
                  className={`w-full text-left px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                    quiz.answered
                      ? i === q.correct ? "bg-green-100 border-green-500 text-green-800"
                        : i === quiz.selectedOption ? "bg-red-100 border-red-500 text-red-800"
                        : "border-gray-200 opacity-40"
                      : "border-gray-200 hover:border-blue-400 hover:bg-blue-50"
                  }`}>
                  {opt}
                </button>
              ))}
            </div>
            {quiz.answered && (
              <button onClick={handleQuizNext}
                className="mt-4 bg-blue-600 text-white px-6 py-3 rounded-xl w-full font-semibold text-lg">
                Continue
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
