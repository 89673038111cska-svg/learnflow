import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, unwrap, type TopicResponse } from "../api/client";

export default function Topics() {
  const [topics, setTopics] = useState<TopicResponse[]>([]);
  const [reviewsDue, setReviewsDue] = useState(0);
  const [draftsCount, setDraftsCount] = useState(0);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const [t, drafts] = await Promise.all([
        unwrap(api.GET("/api/topics")),
        unwrap(api.GET("/api/cards/drafts")),
      ]);
      setTopics(t);
      setDraftsCount(drafts.length);
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
    setLoading(true);
    try {
      await unwrap(api.POST("/api/topics", { body: { name: newName.trim() } }));
      setNewName("");
      await load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Цвета для карточек тем
  const topicColors = [
    "from-blue-500 to-cyan-500",
    "from-purple-500 to-pink-500",
    "from-green-500 to-emerald-500",
    "from-orange-500 to-red-500",
    "from-indigo-500 to-blue-500",
    "from-pink-500 to-rose-500",
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 py-8">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Мои темы</h1>
          <p className="text-gray-500 mt-1">Выберите тему для изучения или создайте новую</p>
        </div>
        
        {/* Быстрые ссылки */}
        <div className="flex gap-3">
          <Link
            to="/reviews"
            className={`btn-secondary flex items-center gap-2 ${
              reviewsDue > 0 ? "bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100" : ""
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Повторы
            {reviewsDue > 0 && (
              <span className="bg-amber-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {reviewsDue}
              </span>
            )}
          </Link>
          <Link
            to="/drafts"
            className={`btn-secondary flex items-center gap-2 ${
              draftsCount > 0 ? "bg-sky-50 border-sky-200 text-sky-700 hover:bg-sky-100" : ""
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Черновики
            {draftsCount > 0 && (
              <span className="bg-sky-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {draftsCount}
              </span>
            )}
          </Link>
        </div>
      </div>

      {/* Ошибка */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}

      {/* Сетка тем */}
      {topics.length === 0 ? (
        <div className="text-center py-16 bg-white/50 rounded-2xl border border-dashed border-gray-300">
          <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <p className="text-gray-500 text-lg">Нет тем для изучения</p>
          <p className="text-gray-400 text-sm mt-1">Создайте первую тему ниже</p>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {topics.map((t, index) => {
            const colorClass = topicColors[index % topicColors.length];
            const progress = t.cards_total ? Math.round((100 * t.cards_mastered) / t.cards_total) : 0;
            
            return (
              <div key={t.id} className="card group overflow-hidden">
                {/* Градиентная шапка */}
                <div className={`h-2 bg-gradient-to-r ${colorClass}`} />
                
                <div className="p-6 space-y-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">
                      {t.name}
                    </h2>
                    {t.description && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">{t.description}</p>
                    )}
                  </div>

                  {/* Прогресс */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Прогресс</span>
                      <span className="font-semibold text-gray-900">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${colorClass} transition-all duration-500 ease-out`}
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      Освоено {t.cards_mastered} из {t.cards_total} карточек
                    </p>
                  </div>

                  {/* Кнопки действий */}
                  <div className="flex gap-2 pt-2">
                    <Link
                      to={`/topic/${t.id}`}
                      className="flex-1 btn-primary text-center text-sm py-2.5"
                    >
                      Учиться
                    </Link>
                    <Link
                      to={`/topic/${t.id}/cards`}
                      className="btn-secondary px-4 py-2.5 text-sm"
                    >
                      Карточки
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Форма создания темы */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Создать новую тему</h3>
        <form onSubmit={createTopic} className="flex gap-3">
          <input
            className="input-field flex-1"
            placeholder="Название темы..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading || !newName.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Создаю...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Создать
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
