import { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/context/AuthContext";
import { Trophy } from "lucide-react";

export default function LoginPage() {
  const [, setLocation] = useLocation();
  const { login } = useAuth();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const endpoint = tab === "login" ? "/api/auth/login" : "/api/auth/register";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Terjadi kesalahan");
      } else {
        login(data.token, data.user);
        setLocation("/");
      }
    } catch {
      setError("Tidak bisa terhubung ke server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl border border-white/[0.04] bg-zinc-900/60 mb-4 shadow-sm">
            <Trophy className="text-emerald-400" size={20} />
          </div>
          <h1 className="text-lg font-extrabold text-foreground tracking-widest uppercase font-mono">
            Kyonayr Predictor
          </h1>
          <p className="text-[9px] text-muted-foreground/45 mt-1 font-bold uppercase tracking-widest font-mono">Football Score Predictor</p>
        </div>

        {/* Tab switcher */}
        <div className="flex rounded-xl bg-zinc-900/40 p-1 mb-6 border border-white/[0.04] backdrop-blur-md">
          <button
            className={`flex-1 py-1.5 text-xs font-bold font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer ${
              tab === "login"
                ? "bg-zinc-900 text-foreground border border-white/[0.04] shadow-xs"
                : "text-muted-foreground/60 hover:text-foreground/90"
            }`}
            onClick={() => { setTab("login"); setError(""); }}
          >
            Masuk
          </button>
          <button
            className={`flex-1 py-1.5 text-xs font-bold font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer ${
              tab === "register"
                ? "bg-zinc-900 text-foreground border border-white/[0.04] shadow-xs"
                : "text-muted-foreground/60 hover:text-foreground/90"
            }`}
            onClick={() => { setTab("register"); setError(""); }}
          >
            Daftar
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[8px] font-bold text-muted-foreground/50 mb-1.5 uppercase tracking-widest font-mono">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Masukkan username"
              required
              autoComplete="username"
              className="w-full px-4 py-3 rounded-xl bg-zinc-900/10 border border-white/[0.04] text-foreground placeholder:text-muted-foreground/20 focus:outline-none focus:border-white/[0.08] focus:ring-1 focus:ring-white/[0.04] transition-all text-xs font-medium"
            />
          </div>

          <div>
            <label className="block text-[8px] font-bold text-muted-foreground/50 mb-1.5 uppercase tracking-widest font-mono">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Masukkan password"
              required
              autoComplete={tab === "login" ? "current-password" : "new-password"}
              className="w-full px-4 py-3 rounded-xl bg-zinc-900/10 border border-white/[0.04] text-foreground placeholder:text-muted-foreground/20 focus:outline-none focus:border-white/[0.08] focus:ring-1 focus:ring-white/[0.04] transition-all text-xs font-medium"
            />
          </div>

          {error && (
            <div className="px-4 py-2.5 rounded-xl bg-rose-500/5 border border-rose-500/10 text-rose-300 text-xs font-semibold leading-normal">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold text-xs uppercase tracking-widest font-mono transition-all disabled:bg-zinc-900 disabled:text-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm cursor-pointer"
          >
            {loading ? "Memproses..." : tab === "login" ? "Masuk" : "Daftar"}
          </button>
        </form>

        {/* Info for register */}
        {tab === "register" && (
          <p className="text-center text-[10px] text-muted-foreground/40 mt-4.5 font-bold uppercase tracking-wider font-mono">
            Mendapatkan <span className="text-emerald-400 font-extrabold">5 prediksi</span> gratis untuk akun baru.
          </p>
        )}
      </div>
    </div>
  );
}
