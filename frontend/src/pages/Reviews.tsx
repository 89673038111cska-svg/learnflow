import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type ReviewResponse } from "../api/client";

export default function Reviews() {
  const [reviews, setReviews] = useState<ReviewResponse[]>([]);
  const [current, setCurrent] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [startedAt, setStartedAt] = useState(Date.now());
  const [done, setDone] = useState<string | null>(null);

  async function load() {
    const r = await unwrap(api.GET("/api/reviews/due"));
    setReviews(r);
    setCurrent(0);
    setShowAnswer(false);
    setStartedAt(Date.now());
  }

  useEffect(() => {
    load();
  }, []);

  async function complete(success: boolean) {
    const r = reviews[current];
    if (!r) return;
    await unwrap(
      api.POST("/api/reviews/{review_id}/complete", {
        params: { path: { review_id: r.id } },
        body: { success, response_time_ms: Date.now() - startedAt },
      }),
    );
    if (current + 1 < reviews.length) {
      setCurrent(current + 1);
      setShowAnswer(false);
      setStartedAt(Date.now());
    } else {
      setDone(
        success
          ? "Все повторы пройдены!"
          : "Готово. Проваленные карточки вернулись в обучение.",
      );
    }
  }

  if (done)
    return (
      <div className="max-w-xl mx-auto text-center space-y-4">
        <p className="text-lg font-medium">{done}</p>
        <Link to="/" className="text-indigo-600 hover:underline">
          К темам
        </Link>
      </div>
    );

  const r = reviews[current];
  if (!r)
    return (
      <div className="max-w-xl mx-auto text-center space-y-4">
        <p className="text-gray-500">Нет карточек к повторению 🎉</p>
        <Link to="/" className="text-indigo-600 hover:underline">
          К темам
        </Link>
      </div>
    );

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="text-sm text-gray-500 hover:text-gray-800">
          ← К темам
        </Link>
        <span className="text-sm text-gray-500">
          {current + 1} / {reviews.length}
        </span>
      </div>

      <div className="bg-white rounded-xl shadow p-6 space-y-4">
        <div className="text-xs text-gray-400">
          интервал: {r.interval_days} дн.
        </div>
        <p className="text-lg font-medium">{r.card?.front_content}</p>
        {showAnswer ? (
          <p className="font-mono text-sm bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">
            {r.card?.back_content}
          </p>
        ) : (
          <button
            onClick={() => setShowAnswer(true)}
            className="w-full border rounded-lg py-2 text-gray-600 hover:bg-gray-50"
          >
            Показать ответ
          </button>
        )}
      </div>

      {showAnswer && (
        <div className="flex gap-3">
          <button
            onClick={() => complete(false)}
            className="flex-1 bg-red-100 text-red-800 rounded-lg py-2 font-medium hover:bg-red-200"
          >
            Не помню
          </button>
          <button
            onClick={() => complete(true)}
            className="flex-1 bg-green-600 text-white rounded-lg py-2 font-medium hover:bg-green-700"
          >
            Помню
          </button>
        </div>
      )}
    </div>
  );
}
