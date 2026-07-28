import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  api,
  unwrap,
  type AttemptResult,
  type LearningStateResponse,
} from "../api/client";
import ExerciseView from "../components/ExerciseView";

export default function Learn() {
  const { id } = useParams<{ id: string }>();
  const topicId = Number(id);
  const [state, setState] = useState<LearningStateResponse | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await unwrap(
        api.GET("/api/learning/state", { params: { query: { topic_id: topicId } } }),
      );
      setState(s);
      setResult(null);
    } catch (err: any) {
      setError(err.message);
    }
  }, [topicId]);

  useEffect(() => {
    load();
  }, [load]);

  async function submit(answer: unknown, usedHint: boolean, responseTimeMs: number) {
    if (!state?.current_card || !state.exercise || busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await unwrap(
        api.POST("/api/learning/attempt", {
          body: {
            card_id: state.current_card.id,
            exercise_kind: state.exercise.kind,
            answer: answer as any,
            used_hint: usedHint,
            response_time_ms: responseTimeMs,
          },
        }),
      );
      setResult(r);
      if (r.card_mastered) {
        setTimeout(load, 1500);
      } else if (r.next_exercise) {
        setState({ ...state, exercise: r.next_exercise });
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="animate-spin h-12 w-12 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-500">Загрузка...</p>
        </div>
      </div>
    );
  }

  const progress = state.progress_percent;
  const isComplete = !state.current_card || !state.exercise;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      {/* Шапка */}
      <div className="flex items-center justify-between">
        <Link
          to="/"
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          К темам
        </Link>
        <div className="text-sm text-gray-500 flex items-center gap-4">
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            {state.cards_mastered}/{state.cards_total}
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
            {state.reviews_due} повторов
          </span>
        </div>
      </div>

      {/* Прогресс-бар */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50 p-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="font-medium text-gray-700">Прогресс темы</span>
          <span className="font-bold text-indigo-600">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Ошибка */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center gap-2 animate-shake">
          <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}

      {/* Результат ответа */}
      {result && (
        <div
          className={`rounded-2xl px-6 py-4 border-2 animate-fade-in ${
            result.correct
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          <div className="flex items-start gap-3">
            {result.correct ? (
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            ) : (
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
            )}
            <div className="flex-1">
              {result.correct ? (
                <>
                  <p className="font-semibold text-lg">Верно! 🎉</p>
                  <p className="text-sm mt-1">
                    Серия правильных ответов: <span className="font-bold">{result.consecutive_correct}</span> из {result.required_consecutive}
                  </p>
                  {result.card_mastered && (
                    <p className="text-sm mt-2 font-medium text-green-700">
                      ✨ Карточка освоена!
                    </p>
                  )}
                  {result.exercise_mastered && !result.card_mastered && (
                    <p className="text-sm mt-2 text-green-700">
                      Упражнение освоено, переходим к следующему...
                    </p>
                  )}
                </>
              ) : (
                <>
                  <p className="font-semibold text-lg">Неверно</p>
                  <p className="text-sm mt-1">
                    Правильный ответ:{" "}
                    <span className="font-mono bg-white px-2 py-1 rounded border border-red-200">
                      {Array.isArray(result.correct_answer)
                        ? result.correct_answer.join(" → ")
                        : String(result.correct_answer ?? "")}
                    </span>
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Карточка упражнения */}
      {!isComplete && state.current_card && state.exercise ? (
        <div className="card p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full">
                {state.current_card.type}
              </span>
              <span className="text-xs font-medium px-3 py-1 bg-purple-100 text-purple-700 rounded-full">
                {state.exercise.kind}
              </span>
            </div>

          </div>
          <ExerciseView
            key={`${state.current_card.id}:${state.exercise.kind}:${result?.consecutive_correct ?? 0}`}
            exercise={state.exercise}
            cardId={state.current_card.id}
            onSubmit={submit}
            disabled={busy}
          />
        </div>
      ) : (
        /* Завершение */
        <div className="card p-12 text-center space-y-6">
          <div className="w-20 h-20 mx-auto bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center shadow-lg">
            <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Тема освоена! 🎉</h2>
            <p className="text-gray-500 mt-2">Все карточки этой темы успешно изучены</p>
          </div>
          <div className="flex justify-center gap-3">
            <Link
              to="/reviews"
              className="btn-primary flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Повторы ({state.reviews_due})
            </Link>
            <Link to="/" className="btn-secondary">
              К темам
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
