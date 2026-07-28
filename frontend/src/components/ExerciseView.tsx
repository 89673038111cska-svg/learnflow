import { useState } from "react";
import { api, unwrap, type Exercise, type HintResponse } from "../api/client";

interface Props {
  exercise: Exercise;
  cardId: number;
  onSubmit: (answer: unknown, usedHint: boolean, responseTimeMs: number) => void;
  disabled: boolean;
}

/** Рендер упражнения по kind. Ответ собирается и передаётся наверх. */
export default function ExerciseView({ exercise, cardId, onSubmit, disabled }: Props) {
  const [text, setText] = useState("");
  const [startedAt] = useState(Date.now());
  const [hint, setHint] = useState<HintResponse | null>(null);
  const [hintLoading, setHintLoading] = useState(false);
  const [hintUsed, setHintUsed] = useState(false);
  const [ordered, setOrdered] = useState<string[]>(
    (exercise.payload.shuffled_steps as string[] | undefined) ?? [],
  );

  async function requestHint() {
    if (hintLoading || hint) return;
    setHintLoading(true);
    try {
      const result = await unwrap(
        api.POST("/api/learning/hint", {
          body: {
            card_id: cardId,
            exercise_kind: exercise.kind,
            answer: "",
            used_hint: true,
          },
        }),
      );
      setHint(result);
      setHintUsed(true);
    } catch (err: any) {
      console.error("Failed to get hint:", err);
    } finally {
      setHintLoading(false);
    }
  }

  const p = exercise.payload as Record<string, any>;

  function elapsed() {
    return Date.now() - startedAt;
  }

  function submitText() {
    if (!text.trim()) return;
    onSubmit(text.trim(), hintUsed, elapsed());
    setText("");
    setHintUsed(false);
  }

  const hintBtn = p.prompt ? (
    <div className="mt-2">
      {!hint ? (
        <button
          type="button"
          onClick={requestHint}
          disabled={hintLoading}
          className="text-sm text-gray-500 hover:text-indigo-600 underline transition-colors disabled:opacity-50"
        >
          {hintLoading ? "Загрузка..." : "💡 Подсказка (сбросит серию)"}
        </button>
      ) : (
        <div className="text-sm bg-yellow-50 border border-yellow-200 rounded-lg p-3 mt-2">
          <p className="font-medium text-yellow-800 mb-1">Правильный ответ:</p>
          <p className="text-yellow-900 font-mono">
            {Array.isArray(hint.correct_answer)
              ? hint.correct_answer.join(", ")
              : String(hint.correct_answer)}
          </p>
        </div>
      )}
    </div>
  ) : null;

  switch (exercise.kind) {
    case "multiple_choice":
    case "reverse_choice":
      return (
        <div className="space-y-6 animate-fade-in">
          <p className="text-xl font-semibold text-gray-900 leading-relaxed">{p.prompt}</p>
          <div className="grid gap-3">
            {(p.options as string[]).map((opt, idx) => (
              <button
                key={opt}
                disabled={disabled}
                onClick={() => onSubmit(opt, hintUsed, elapsed())}
                className="group text-left border-2 border-gray-200 rounded-xl px-5 py-4 hover:border-indigo-400 hover:bg-indigo-50/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
              >
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 bg-gray-100 group-hover:bg-indigo-100 rounded-full flex items-center justify-center text-sm font-bold text-gray-600 group-hover:text-indigo-700 transition-colors">
                    {String.fromCharCode(65 + idx)}
                  </span>
                  <span className="flex-1 font-medium text-gray-800">{opt}</span>
                </div>
              </button>
            ))}
          </div>
          {hintBtn}
        </div>
      );

    case "order_steps":
      return (
        <div className="space-y-6 animate-fade-in">
          <p className="text-xl font-semibold text-gray-900">{p.prompt}</p>
          <p className="text-sm text-gray-600 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
            📋 Расставь шаги в правильном порядке (перетащи или используй стрелки)
          </p>
          <ul className="space-y-3">
            {ordered.map((step, i) => (
              <li
                key={step}
                className="group flex items-center gap-3 border-2 border-gray-200 rounded-xl px-4 py-3 bg-white hover:border-indigo-300 transition-all shadow-sm"
              >
                <span className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-500 text-white rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {i + 1}
                </span>
                <span className="flex-1 font-mono text-sm text-gray-800">{step}</span>
                <div className="flex flex-col gap-1 opacity-50 group-hover:opacity-100 transition-opacity">
                  <button
                    type="button"
                    disabled={i === 0}
                    onClick={() => {
                      const next = [...ordered];
                      [next[i - 1], next[i]] = [next[i], next[i - 1]];
                      setOrdered(next);
                    }}
                    className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 disabled:opacity-30 transition-colors"
                    title="Переместить вверх"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    disabled={i === ordered.length - 1}
                    onClick={() => {
                      const next = [...ordered];
                      [next[i + 1], next[i]] = [next[i], next[i + 1]];
                      setOrdered(next);
                    }}
                    className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 disabled:opacity-30 transition-colors"
                    title="Переместить вниз"
                  >
                    ▼
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <button
            disabled={disabled}
            onClick={() => onSubmit(ordered, hintUsed, elapsed())}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl px-6 py-3 font-semibold hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
          >
            ✓ Проверить порядок
          </button>
          {hintBtn}
        </div>
      );

    case "next_step":
      return (
        <div className="space-y-6 animate-fade-in">
          <p className="text-xl font-semibold text-gray-900">{p.prompt}</p>
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border-2 border-gray-200 p-5">
            <ol className="list-decimal list-inside space-y-2 font-mono text-sm">
              {(p.given_steps as string[]).map((s, idx) => (
                <li key={s} className="text-gray-700 pl-2">
                  <span className="font-bold text-indigo-600 mr-2">{idx + 1}.</span>
                  {s}
                </li>
              ))}
              <li className="text-indigo-600 font-bold pl-2 animate-pulse">
                <span className="mr-2">?</span>
                Следующий шаг...
              </li>
            </ol>
          </div>
          <TextAnswer text={text} setText={setText} onSubmit={submitText} disabled={disabled} placeholder="Введи следующий шаг..." />
          {hintBtn}
        </div>
      );

    case "fill_blank":
      return (
        <div className="space-y-6 animate-fade-in">
          <p className="text-xl font-semibold text-gray-900">{p.prompt}</p>
          <div className="bg-amber-50 border-2 border-amber-200 rounded-xl px-6 py-4 font-mono text-base">
            {(p.template as string).split("{{blank}}")[0]}
            <span className="inline-block bg-amber-200 text-amber-900 px-3 py-1 rounded-lg mx-1 font-bold animate-pulse">???</span>
            {(p.template as string).split("{{blank}}")[1]}
          </div>
          <TextAnswer text={text} setText={setText} onSubmit={submitText} disabled={disabled} placeholder="Пропущенный фрагмент..." />
          {hintBtn}
        </div>
      );

    // text_input, write_command, find_bug
    default:
      return (
        <div className="space-y-6 animate-fade-in">
          <p className="text-xl font-semibold text-gray-900 leading-relaxed">{p.prompt}</p>
          <TextAnswer
            text={text}
            setText={setText}
            onSubmit={submitText}
            disabled={disabled}
            placeholder={exercise.kind === "write_command" || exercise.kind === "find_bug" ? "Полная команда..." : "Твой ответ..."}
          />
          {hintBtn}
        </div>
      );
  }
}

function TextAnswer({
  text,
  setText,
  onSubmit,
  disabled,
  placeholder,
}: {
  text: string;
  setText: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  placeholder: string;
}) {
  return (
    <div className="flex gap-3">
      <input
        className="flex-1 border-2 border-gray-300 rounded-xl px-4 py-3 font-mono text-base focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all shadow-sm"
        placeholder={placeholder}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        autoFocus
        disabled={disabled}
      />
      <button
        onClick={onSubmit}
        disabled={disabled || !text.trim()}
        className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl px-8 py-3 font-semibold hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
      >
        Ответить →
      </button>
    </div>
  );
}
