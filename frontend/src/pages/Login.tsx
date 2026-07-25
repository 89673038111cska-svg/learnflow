import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken, unwrap } from "../api/client";

export default function Login() {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await unwrap(
        api.POST("/api/auth/login", { body: { login, password } }),
      );
      setToken(res.access_token);
      navigate("/");
    } catch (err: any) {
      setError(err.message ?? "Ошибка входа");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="bg-white p-8 rounded-xl shadow w-full max-w-sm space-y-4"
      >
        <h1 className="text-2xl font-bold text-gray-900">LearnFlow</h1>
        <input
          className="w-full border rounded-lg px-3 py-2"
          placeholder="Логин"
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          autoFocus
        />
        <input
          className="w-full border rounded-lg px-3 py-2"
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white rounded-lg py-2 font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Вход..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
