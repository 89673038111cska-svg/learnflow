import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type CardResponse } from "../api/client";

export default function Drafts() {
  const [drafts, setDrafts] = useState<CardResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setDrafts(await unwrap(api.GET("/api/cards/drafts")));
    } catch (err: any) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function approve(id: number) {
    await unwrap(
      api.POST("/api/cards/{card_id}/approve", { params: { path: { card_id: id } } }),
    );
    load();
  }

  async function reject(id: number) {
    await unwrap(
      api.POST("/api/cards/{card_id}/reject", { params: { path: { card_id: id } } }),
    );
    load();
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Черновики от агентов</h1>
        <Link to="/" className="text-sm text-gray-500 hover:text-gray-800">
          ← К темам
        </Link>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {drafts.length === 0 && (
        <p className="text-gray-500">Черновиков нет — очередь чиста.</p>
      )}
      {drafts.map((c) => (
        <div key={c.id} className="bg-white rounded-xl shadow p-5 space-y-3">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span className="uppercase">{c.type}</span>
            <span>· источник: {c.source}</span>
          </div>
          <p className="font-medium">{c.front_content}</p>
          <p className="font-mono text-sm bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">
            {c.back_content}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => approve(c.id)}
              className="bg-green-600 text-white rounded-lg px-4 py-1.5 text-sm font-medium hover:bg-green-700"
            >
              Approve → в обучение
            </button>
            <button
              onClick={() => reject(c.id)}
              className="bg-red-100 text-red-800 rounded-lg px-4 py-1.5 text-sm font-medium hover:bg-red-200"
            >
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
