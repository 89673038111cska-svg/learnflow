import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  unwrap,
  type CardResponse,
  type CardType,
  type TopicResponse,
} from "../api/client";

/** Список карточек темы + ручное создание. */
export default function TopicCards() {
  const { id } = useParams<{ id: string }>();
  const topicId = Number(id);
  const [topic, setTopic] = useState<TopicResponse | null>(null);
  const [cards, setCards] = useState<CardResponse[]>([]);
  const [type, setType] = useState<CardType>("term");
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");

  async function load() {
    setTopic(
      await unwrap(api.GET("/api/topics/{topic_id}", { params: { path: { topic_id: topicId } } })),
    );
    setCards(
      await unwrap(
        api.GET("/api/topics/{topic_id}/cards", { params: { path: { topic_id: topicId } } }),
      ),
    );
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicId]);

  async function createCard(e: React.FormEvent) {
    e.preventDefault();
    if (!front.trim() || !back.trim()) return;
    await unwrap(
      api.POST("/api/cards", {
        body: {
          topic_id: topicId,
          type,
          front_content: front.trim(),
          back_content: back.trim(),
        },
      }),
    );
    setFront("");
    setBack("");
    load();
  }

  async function removeCard(id: number) {
    await unwrap(api.DELETE("/api/cards/{card_id}", { params: { path: { card_id: id } } }));
    load();
  }

  const statusBadge: Record<string, string> = {
    draft: "bg-sky-100 text-sky-800",
    learning: "bg-amber-100 text-amber-800",
    mastered: "bg-green-100 text-green-800",
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">{topic?.name ?? "..."} — карточки</h1>
        <Link to="/" className="text-sm text-gray-500 hover:text-gray-800">
          ← К темам
        </Link>
      </div>

      <form onSubmit={createCard} className="bg-white rounded-xl shadow p-5 space-y-3">
        <div className="flex gap-2">
          {(["term", "command", "procedure"] as CardType[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setType(t)}
              className={`px-3 py-1 rounded-lg text-sm font-medium ${
                type === t ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <input
          className="w-full border rounded-lg px-3 py-2"
          placeholder="Вопрос / термин / задача"
          value={front}
          onChange={(e) => setFront(e.target.value)}
        />
        <textarea
          className="w-full border rounded-lg px-3 py-2 font-mono text-sm"
          placeholder={
            type === "procedure"
              ? "Шаги — по строке на шаг"
              : "Ответ / определение / команда"
          }
          rows={type === "procedure" ? 4 : 2}
          value={back}
          onChange={(e) => setBack(e.target.value)}
        />
        <button
          type="submit"
          className="bg-indigo-600 text-white rounded-lg px-4 py-2 font-medium hover:bg-indigo-700"
        >
          Добавить в обучение
        </button>
      </form>

      <div className="space-y-2">
        {cards.map((c) => (
          <div key={c.id} className="bg-white rounded-lg shadow-sm p-4 flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-xs">
                <span className={`px-2 py-0.5 rounded ${statusBadge[c.status]}`}>{c.status}</span>
                <span className="text-gray-400">{c.type}</span>
              </div>
              <p className="font-medium truncate">{c.front_content}</p>
              <p className="text-sm text-gray-500 font-mono truncate">{c.back_content}</p>
            </div>
            <button
              onClick={() => removeCard(c.id)}
              className="text-gray-300 hover:text-red-500"
              title="Удалить"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
