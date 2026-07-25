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
        // карточка освоена — сразу перезагружаем state (следующая карточка)
        setTimeout(load, 1500);
      } else if (r.next_exercise) {
        // подменяем упражнение без полной перезагрузки
        setState({ ...state, exercise: r.next_exercise });
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!state) return <p className="text-gray-500">Загрузка...</p>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="text-sm text-gray-500 hover:text-gray-800">
          ← К темам
        </Link>
        <span className="text-sm text-gray-500">
          {state.cards_mastered}/{state.cards_total} освоено · повторов:{" "}
          {state.reviews_due}
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all"
          style={{ width: `${state.progress_percent}%` }}
        />
      </div>

      {error && <p className="text-red-600">{error}</p>}

      {result && (
        <div
          className={`rounded-lg px-4 py-3 ${
            result.correct
              ? "bg-green-50 text-green-800"
              : "bg-red-50 text-red-800"
          }`}
        >
          {result.correct ? (
            <>
              Верно! Серия: {result.consecutive_correct}/
              {result.required_consecutive}
              {result.card_mastered && " — карточка освоена! 🎉"}
              {result.exercise_mastered &&
                !result.card_mastered &&
                " — упражнение освоено, следующее:"}
            </>
          ) : (
            <>
              Неверно. Правильный ответ:{" "}
              <span className="font-mono">
                {Array.isArray(result.correct_answer)
                  ? result.correct_answer.join(" → ")
                  : String(result.correct_answer ?? "")}
              </span>
            </>
          )}
        </div>
      )}

      {state.current_card && state.exercise ? (
        <div className="bg-white rounded-xl shadow p-6">
          <div className="text-xs text-gray-400 mb-3">
            {state.current_card.type} · {state.exercise.kind}
          </div>
          <ExerciseView
            key={`${state.current_card.id}:${state.exercise.kind}:${result?.consecutive_correct ?? 0}`}
            exercise={state.exercise}
            onSubmit={submit}
            disabled={busy}
          />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow p-6 text-center space-y-3">
          <p className="text-lg font-medium">Все карточки темы освоены 🎉</p>
          <Link to="/reviews" className="text-indigo-600 hover:underline">
            Перейти к повторам ({state.reviews_due})
          </Link>
        </div>
      )}
    </div>
  );
}
