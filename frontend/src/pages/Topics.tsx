import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type TopicResponse } from "../api/client";

export default function Topics() {
  const [topics, setTopics] = useState<TopicResponse[]>([]);
  const [reviewsDue, setReviewsDue] = useState(0);
  const [draftsCount, setDraftsCount] = useState(0);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [t, drafts] = await Promise.all([
        unwrap(api.GET("/api/topics")),
        unwrap(api.GET("/api/cards/drafts")),
      ]);
      setTopics(t);
      setDraftsCount(drafts.length);
      // reviews_due берём из первой темы со state — проще: отдельный запрос due
      const due = await unwrap(api.GET("/api/reviews/due"));
      setReviewsDue(due.length);
    } catch (err: any) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createTopic(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    await unwrap(api.POST("/api/topics", { body: { name: newName.trim() } }));
    setNewName("");
    load();
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-3">
        <Link
          to="/reviews"
          className="bg-amber-100 text-amber-900 px-4 py-2 rounded-lg font-medium hover:bg-amber-200"
        >
          Повторы ({reviewsDue})
        </Link>
        <Link
          to="/drafts"
          className="bg-sky-100 text-sky-900 px-4 py-2 rounded-lg font-medium hover:bg-sky-200"
        >
          Черновики ({draftsCount})
        </Link>
      </div>

      {error && <p className="text-red-600">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {topics.map((t) => (
          <div key={t.id} className="bg-white rounded-xl shadow p-5 space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">{t.name}</h2>
            {t.description && (
              <p className="text-sm text-gray-500">{t.description}</p>
            )}
            <div className="text-sm text-gray-600">
              Освоено {t.cards_mastered} / {t.cards_total}
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-indigo-600 h-2 rounded-full"
                style={{
                  width: t.cards_total
                    ? `${(100 * t.cards_mastered) / t.cards_total}%`
                    : "0%",
                }}
              />
            </div>
            <div className="flex gap-2">
              <Link
                to={`/topic/${t.id}`}
                className="flex-1 text-center bg-indigo-600 text-white rounded-lg py-1.5 text-sm font-medium hover:bg-indigo-700"
              >
                Учиться
              </Link>
              <Link
                to={`/topic/${t.id}/cards`}
                className="px-3 border rounded-lg py-1.5 text-sm text-gray-600 hover:bg-gray-50"
              >
                Карточки
              </Link>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={createTopic} className="flex gap-2 max-w-md">
        <input
          className="flex-1 border rounded-lg px-3 py-2"
          placeholder="Новая тема..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <button
          type="submit"
          className="bg-indigo-600 text-white rounded-lg px-4 py-2 font-medium hover:bg-indigo-700"
        >
          Создать
        </button>
      </form>
    </div>
  );
}
