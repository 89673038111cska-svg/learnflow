import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { getToken, clearToken } from "./api/client";
import Login from "./pages/Login";
import Topics from "./pages/Topics";
import Learn from "./pages/Learn";
import TopicCards from "./pages/TopicCards";
import Reviews from "./pages/Reviews";
import Drafts from "./pages/Drafts";

function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1
            className="text-2xl font-bold text-gray-900 cursor-pointer"
            onClick={() => navigate("/")}
          >
            LearnFlow
          </h1>
          <button
            onClick={() => {
              clearToken();
              navigate("/login");
            }}
            className="text-sm text-gray-500 hover:text-gray-800"
          >
            Выйти
          </button>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
    </div>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Topics /></RequireAuth>} />
        <Route path="/topic/:id" element={<RequireAuth><Learn /></RequireAuth>} />
        <Route path="/topic/:id/cards" element={<RequireAuth><TopicCards /></RequireAuth>} />
        <Route path="/reviews" element={<RequireAuth><Reviews /></RequireAuth>} />
        <Route path="/drafts" element={<RequireAuth><Drafts /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
