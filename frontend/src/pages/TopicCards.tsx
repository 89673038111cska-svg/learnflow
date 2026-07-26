import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  unwrap,
  type CardResponse,
  type CardType,
  type TopicResponse,
} from "../api/client";

// Конфигурация стилей для типов карточек
const cardTypeConfig: Record<CardType, {
  color: string;
  bgColor: string;
  borderColor: string;
  icon: string;
  label: string;
}> = {
  term: {
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    icon: "📖",
    label: "Термин",
  },
  command: {
    color: "text-purple-700",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
    icon: "⌨️",
    label: "Команда",
  },
  procedure: {
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
    icon: "📋",
    label: "Процедура",
  },
};

// Статусы карточек
const statusConfig: Record<string, {
  color: string;
  bgColor: string;
  label: string;
}> = {
  draft: {
    color: "text-sky-700",
    bgColor: "bg-sky-100",
    label: "Черновик",
  },
  learning: {
    color: "text-amber-700",
    bgColor: "bg-amber-100",
    label: "Изучаю",
  },
  mastered: {
    color: "text-green-700",
    bgColor: "bg-green-100",
    label: "Освоено",
  },
};

/** Список карточек темы + ручное создание. */
export default function TopicCards() {
  const { id } = useParams<{ id: string }>();
  const topicId = Number(id);
  const [topic, setTopic] = useState<TopicResponse | null>(null);
  const [cards, setCards] = useState<CardResponse[]>([]);
  const [type, setType] = useState<CardType>("term");
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [filter, setFilter] = useState<CardType | "all">("all");

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

  // Фильтрация карточек
  const filteredCards = filter === "all" 
    ? cards 
    : cards.filter(c => c.type === filter);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Заголовок страницы */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {topic?.name ?? "Загрузка..."}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Карточки обучения • {cards.length} всего
          </p>
        </div>
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-indigo-600 transition-colors px-3 py-2 rounded-lg hover:bg-gray-100"
        >
          ← К темам
        </Link>
      </div>

      {/* Форма добавления новой карточки */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Добавить карточку</h2>
          <p className="text-sm text-gray-600 mt-1">Создайте новую карточку для изучения</p>
        </div>
        
        <form onSubmit={createCard} className="p-6 space-y-4">
          {/* Выбор типа карточки */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Тип карточки
            </label>
            <div className="flex flex-wrap gap-2">
              {(["term", "command", "procedure"] as CardType[]).map((t) => {
                const config = cardTypeConfig[t];
                const isSelected = type === t;
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setType(t)}
                    className={`
                      inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all
                      ${isSelected 
                        ? `${config.bgColor} ${config.color} ${config.borderColor} border-2 shadow-md scale-105`
                        : "bg-gray-50 text-gray-600 border-2 border-transparent hover:border-gray-200 hover:bg-gray-100"
                      }
                    `}
                  >
                    <span className="text-lg">{config.icon}</span>
                    <span>{config.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Поле вопроса/термина */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {type === "term" ? "Термин / вопрос" : type === "command" ? "Команда / задача" : "Задача / ситуация"}
            </label>
            <input
              className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all outline-none"
              placeholder={
                type === "term" 
                  ? "Например: Что такое Git rebase?"
                  : type === "command"
                  ? "Например: git commit -m \"message\""
                  : "Например: Как отменить последний коммит?"
              }
              value={front}
              onChange={(e) => setFront(e.target.value)}
            />
          </div>

          {/* Поле ответа */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {type === "procedure" ? "Шаги решения (по строке на шаг)" : "Ответ / определение"}
            </label>
            <textarea
              className={`
                w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-900 placeholder-gray-400 
                focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all outline-none
                ${type === "command" || type === "procedure" ? "font-mono text-sm bg-gray-50" : ""}
              `}
              placeholder={
                type === "procedure"
                  ? "1. Шаг первый\n2. Шаг второй\n3. Шаг третий"
                  : type === "command"
                  ? "git reset --soft HEAD~1"
                  : "Перебазирование — это процесс переноса коммитов..."
              }
              rows={type === "procedure" ? 5 : 3}
              value={back}
              onChange={(e) => setBack(e.target.value)}
            />
          </div>

          {/* Кнопка создания */}
          <button
            type="submit"
            disabled={!front.trim() || !back.trim()}
            className="
              w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl px-6 py-3 
              font-semibold text-base shadow-lg hover:shadow-xl hover:from-indigo-700 hover:to-purple-700 
              disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg
              transform hover:-translate-y-0.5 transition-all duration-200
            "
          >
            ✨ Добавить в обучение
          </button>
        </form>
      </div>

      {/* Фильтры и список карточек */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Все карточки</h2>
          
          {/* Фильтры по типу */}
          <div className="flex gap-2">
            <button
              onClick={() => setFilter("all")}
              className={`
                px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                ${filter === "all" 
                  ? "bg-gray-900 text-white shadow-md"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }
              `}
            >
              Все ({cards.length})
            </button>
            {(["term", "command", "procedure"] as CardType[]).map((t) => {
              const count = cards.filter(c => c.type === t).length;
              const config = cardTypeConfig[t];
              return (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className={`
                    inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                    ${filter === t
                      ? `${config.bgColor} ${config.color} shadow-md`
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }
                  `}
                >
                  <span>{config.icon}</span>
                  <span>{count}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Сетка карточек */}
        {filteredCards.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200">
            <div className="text-4xl mb-3">📝</div>
            <p className="text-gray-500 font-medium">
              {filter === "all" 
                ? "Пока нет карточек. Создайте первую!"
                : `Нет карточек типа "${cardTypeConfig[filter as CardType].label}"`
              }
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
            {filteredCards.map((c) => {
              const typeConfig = cardTypeConfig[c.type];
              const statusCfg = statusConfig[c.status] || statusConfig.draft;
              
              return (
                <div
                  key={c.id}
                  className={`
                    group bg-white rounded-2xl border-2 ${typeConfig.borderColor} 
                    shadow-sm hover:shadow-xl transition-all duration-300
                    hover:-translate-y-1 overflow-hidden
                  `}
                >
                  {/* Шапка карточки */}
                  <div className={`${typeConfig.bgColor} px-4 py-3 border-b ${typeConfig.borderColor}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{typeConfig.icon}</span>
                        <span className={`text-xs font-semibold ${typeConfig.color} uppercase tracking-wide`}>
                          {typeConfig.label}
                        </span>
                      </div>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${statusCfg.bgColor} ${statusCfg.color}`}>
                        {statusCfg.label}
                      </span>
                    </div>
                  </div>

                  {/* Тело карточки */}
                  <div className="p-4 space-y-3">
                    {/* Вопрос */}
                    <div>
                      <p className="font-semibold text-gray-900 text-base leading-relaxed">
                        {c.front_content}
                      </p>
                    </div>

                    {/* Ответ */}
                    <div className={`
                      p-3 rounded-xl text-sm leading-relaxed
                      ${c.type === "command" || c.type === "procedure" 
                        ? "bg-gray-900 text-green-400 font-mono" 
                        : "bg-gray-50 text-gray-700"
                      }
                    `}>
                      {c.type === "procedure" ? (
                        <ol className="list-decimal list-inside space-y-1">
                          {c.back_content.split('\n').filter(line => line.trim()).map((line, idx) => (
                            <li key={idx}>{line.replace(/^\d+\.?\s*/, '').trim()}</li>
                          ))}
                        </ol>
                      ) : (
                        <p className="whitespace-pre-wrap">{c.back_content}</p>
                      )}
                    </div>
                  </div>

                  {/* Футер с кнопкой удаления */}
                  <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex justify-end">
                    <button
                      onClick={() => removeCard(c.id)}
                      className="
                        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                        text-gray-500 hover:text-red-600 hover:bg-red-50 transition-all
                        opacity-0 group-hover:opacity-100
                      "
                      title="Удалить карточку"
                    >
                      <span>🗑️</span>
                      <span>Удалить</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
