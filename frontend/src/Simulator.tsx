import { useState, useRef } from "react";
import { manifest } from "./manifest";

type QuizState = {
  active: boolean;
  questionIndex: number;
  questions: typeof manifest.quiz_breaks[0]["questions"];
  score: number;
  answered: boolean;
  selectedOption: number | null;
};

export default function Simulator() {
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
      goNext();
    } else {
      setShowError(true);
      setTimeout(() => setShowError(false), 2000);
    }
  }

  function goNext() {
    const nextStepIndex = currentStep + 1;
    const quizBreak = manifest.quiz_breaks.find(q => q.after_step === step.step_id);

    if (quizBreak) {
      setQuiz({ active: true, questionIndex: 0, questions: quizBreak.questions, score: 0, answered: false, selectedOption: null });
    } else if (nextStepIndex >= manifest.steps.length) {
      setCompleted(true);
    } else {
      setCurrentStep(nextStepIndex);
      setShowTip(false);
    }
  }

  function handleQuizAnswer(optionIndex: number) {
    if (quiz.answered) return;
    const correct = quiz.questions[quiz.questionIndex].correct === optionIndex;
    setQuiz(q => ({ ...q, answered: true, selectedOption: optionIndex, score: q.score + (correct ? 1 : 0) }));
  }

  function handleQuizNext() {
    const nextQ = quiz.questionIndex + 1;
    if (nextQ < quiz.questions.length) {
      setQuiz(q => ({ ...q, questionIndex: nextQ, answered: false, selectedOption: null }));
    } else {
      setTotalScore(s => s + quiz.score);
      setTotalQuestions(t => t + quiz.questions.length);
      const nextStepIndex = currentStep + 1;
      if (nextStepIndex >= manifest.steps.length) {
        setCompleted(true);
      } else {
        setCurrentStep(nextStepIndex);
      }
      setQuiz({ active: false, questionIndex: 0, questions: [], score: 0, answered: false, selectedOption: null });
    }
  }

  if (completed) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl p-8 max-w-sm w-full text-center">
          <div className="text-5xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold mb-2">Training Complete!</h2>
          <p className="text-gray-600 mb-4">{manifest.workflow_name}</p>
          <div className="bg-green-50 rounded-xl p-4 mb-6">
            <p className="text-3xl font-bold text-green-600">{totalScore}/{totalQuestions}</p>
            <p className="text-sm text-green-700">Quiz Score</p>
          </div>
          <button onClick={() => { setCurrentStep(0); setCompleted(false); setTotalScore(0); setTotalQuestions(0); }}
            className="bg-blue-600 text-white px-6 py-3 rounded-xl w-full font-medium">
            Restart Training
          </button>
        </div>
      </div>
    );
  }

  const t = step.tap_target;
  const q = quiz.active ? quiz.questions[quiz.questionIndex] : null;

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-2">
      <div className="relative max-w-sm w-full">
        {/* Step counter */}
        <div className="text-white text-center text-sm mb-2 opacity-70">
          Step {step.step_id} of {manifest.steps.length} — {step.title}
        </div>

        {/* Phone frame */}
        <div ref={imgRef} className="relative rounded-2xl overflow-hidden shadow-2xl cursor-pointer" onClick={handleScreenClick}>
          {/* Screenshot */}
          <img src={step.screenshot} alt={step.screen} className="w-full select-none pointer-events-none" draggable={false} />

          {/* Tap target highlight */}
          <div className="absolute border-2 border-blue-400 rounded-lg animate-pulse pointer-events-none"
            style={{ left: `${t.x}%`, top: `${t.y}%`, width: `${t.width}%`, height: `${t.height}%` }} />

          {/* Instruction overlay */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 pt-12">
            <p className="text-white text-base font-medium">{step.instruction}</p>
          </div>

          {/* Error toast */}
          {showError && (
            <div className="absolute top-4 left-4 right-4 bg-red-500 text-white px-4 py-3 rounded-xl text-sm font-medium animate-bounce">
              ❌ {step.on_wrong_action}
            </div>
          )}
        </div>

        {/* Tip */}
        {step.tip && (
          <button onClick={() => setShowTip(!showTip)}
            className="mt-3 w-full text-left bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 text-sm">
            <span className="font-medium">💡 {showTip ? step.tip : "Tap for a tip"}</span>
          </button>
        )}

        {/* Quiz overlay */}
        {quiz.active && q && (
          <div className="absolute inset-0 bg-black/70 flex items-center justify-center p-4 rounded-2xl">
            <div className="bg-white rounded-2xl p-6 w-full max-w-sm">
              <p className="text-xs text-blue-600 font-medium mb-2">Quick Check!</p>
              <p className="font-semibold mb-4">{q.question}</p>
              <div className="space-y-2">
                {q.options.map((opt, i) => (
                  <button key={i} onClick={() => handleQuizAnswer(i)}
                    className={`w-full text-left px-4 py-3 rounded-xl border text-sm transition-all ${
                      quiz.answered
                        ? i === q.correct ? "bg-green-100 border-green-500 text-green-800"
                          : i === quiz.selectedOption ? "bg-red-100 border-red-500 text-red-800"
                          : "border-gray-200 opacity-50"
                        : "border-gray-200 hover:border-blue-400 hover:bg-blue-50"
                    }`}>
                    {opt}
                  </button>
                ))}
              </div>
              {quiz.answered && (
                <button onClick={handleQuizNext}
                  className="mt-4 bg-blue-600 text-white px-6 py-3 rounded-xl w-full font-medium">
                  Continue
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
