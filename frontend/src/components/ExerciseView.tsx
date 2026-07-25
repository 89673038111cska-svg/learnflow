import { useState } from "react";
import type { Exercise } from "../api/client";

interface Props {
  exercise: Exercise;
  onSubmit: (answer: unknown, usedHint: boolean, responseTimeMs: number) => void;
  disabled: boolean;
}

/** Рендер упражнения по kind. Ответ собирается и передаётся наверх. */
export default function ExerciseView({ exercise, onSubmit, disabled }: Props) {
  const [text, setText] = useState("");
  const [startedAt] = useState(Date.now());
  const [hintUsed, setHintUsed] = useState(false);
  const [ordered, setOrdered] = useState<string[]>(
    (exercise.payload.shuffled_steps as string[] | undefined) ?? [],
  );

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

  const hintBtn = p.prompt && exercise.kind !== "multiple_choice" && exercise.kind !== "reverse_choice" ? (
    <button
      type="button"
      onClick={() => setHintUsed(true)}
      className="text-sm text-gray-400 underline"
    >
      Подсказка (сбросит серию)
    </button>
  ) : null;

  switch (exercise.kind) {
    case "multiple_choice":
    case "reverse_choice":
      return (
        <div className="space-y-4">
          <p className="text-lg font-medium">{p.prompt}</p>
          <div className="grid gap-2">
            {(p.options as string[]).map((opt) => (
              <button
                key={opt}
                disabled={disabled}
                onClick={() => onSubmit(opt, hintUsed, elapsed())}
                className="text-left border rounded-lg px-4 py-3 hover:bg-indigo-50 hover:border-indigo-300 disabled:opacity-50"
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );

    case "order_steps":
      return (
        <div className="space-y-4">
          <p className="text-lg font-medium">{p.prompt}</p>
          <p className="text-sm text-gray-500">Расставь шаги в правильном порядке (верхний — первый)</p>
          <ul className="space-y-2">
            {ordered.map((step, i) => (
              <li
                key={step}
                className="flex items-center gap-2 border rounded-lg px-3 py-2 bg-white"
              >
                <span className="text-gray-400 w-6">{i + 1}.</span>
                <span className="flex-1 font-mono text-sm">{step}</span>
                <div className="flex flex-col">
                  <button
                    type="button"
                    disabled={i === 0}
                    onClick={() => {
                      const next = [...ordered];
                      [next[i - 1], next[i]] = [next[i], next[i - 1]];
                      setOrdered(next);
                    }}
                    className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
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
                    className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
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
            className="bg-indigo-600 text-white rounded-lg px-6 py-2 font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            Проверить
          </button>
          {hintBtn}
        </div>
      );

    case "next_step":
      return (
        <div className="space-y-4">
          <p className="text-lg font-medium">{p.prompt}</p>
          <ol className="list-decimal list-inside space-y-1 font-mono text-sm text-gray-700">
            {(p.given_steps as string[]).map((s) => (
              <li key={s}>{s}</li>
            ))}
            <li className="text-indigo-600">?</li>
          </ol>
          <TextAnswer text={text} setText={setText} onSubmit={submitText} disabled={disabled} placeholder="Следующий шаг..." />
          {hintBtn}
        </div>
      );

    case "fill_blank":
      return (
        <div className="space-y-4">
          <p className="text-lg font-medium">{p.prompt}</p>
          <p className="font-mono text-sm bg-gray-100 rounded-lg px-3 py-2">
            {(p.template as string).split("{{blank}}")[0]}
            <span className="bg-amber-200 px-2 rounded">?</span>
            {(p.template as string).split("{{blank}}")[1]}
          </p>
          <TextAnswer text={text} setText={setText} onSubmit={submitText} disabled={disabled} placeholder="Пропущенный фрагмент..." />
          {hintBtn}
        </div>
      );

    // text_input, write_command, find_bug
    default:
      return (
        <div className="space-y-4">
          <p className="text-lg font-medium">{p.prompt}</p>
          <TextAnswer
            text={text}
            setText={setText}
            onSubmit={submitText}
            disabled={disabled}
            placeholder={exercise.kind === "write_command" || exercise.kind === "find_bug" ? "Полная команда..." : "Ответ..."}
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
    <div className="flex gap-2">
      <input
        className="flex-1 border rounded-lg px-3 py-2 font-mono"
        placeholder={placeholder}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        autoFocus
      />
      <button
        onClick={onSubmit}
        disabled={disabled || !text.trim()}
        className="bg-indigo-600 text-white rounded-lg px-6 py-2 font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        Ответить
      </button>
    </div>
  );
}
