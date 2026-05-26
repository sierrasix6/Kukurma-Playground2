import { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/context/AuthContext";

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
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl border border-border bg-card mb-4 shadow-xs">
            <span className="text-2xl">⚽</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            Kyonayr Playground
          </h1>
          <p className="text-xs text-muted-foreground/80 mt-1 font-medium">Football Score Predictor</p>
        </div>

        {/* Tab switcher */}
        <div className="flex rounded-xl bg-muted/20 p-1 mb-6 border border-border">
          <button
            className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all cursor-pointer ${
              tab === "login"
                ? "bg-secondary text-foreground shadow-sm border border-border/80"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => { setTab("login"); setError(""); }}
          >
            Masuk
          </button>
          <button
            className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all cursor-pointer ${
              tab === "register"
                ? "bg-secondary text-foreground shadow-sm border border-border/80"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => { setTab("register"); setError(""); }}
          >
            Daftar
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold text-muted-foreground mb-1.5 uppercase tracking-wider">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Masukkan username"
              required
              autoComplete="username"
              className="w-full px-4 py-3.5 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-border-foreground/30 focus:ring-1 focus:ring-border/40 transition-all text-sm font-medium"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-muted-foreground mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Masukkan password"
              required
              autoComplete={tab === "login" ? "current-password" : "new-password"}
              className="w-full px-4 py-3.5 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-border-foreground/30 focus:ring-1 focus:ring-border/40 transition-all text-sm font-medium"
            />
          </div>

          {error && (
            <div className="px-4 py-3 rounded-xl bg-destructive/5 border border-destructive/20 text-destructive-foreground text-xs font-semibold">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full py-3.5 rounded-xl bg-primary hover:opacity-95 text-primary-foreground font-bold text-sm transition-all disabled:bg-muted disabled:text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed shadow-sm cursor-pointer"
          >
            {loading ? "Memproses..." : tab === "login" ? "Masuk" : "Buat Akun"}
          </button>
        </form>

        {/* Info for register */}
        {tab === "register" && (
          <p className="text-center text-xs text-muted-foreground mt-4.5 font-medium">
            Akun baru mendapatkan <span className="text-primary font-bold">5 kredit</span> gratis untuk prediksi.
          </p>
        )}
      </div>
    </div>
  );
}
