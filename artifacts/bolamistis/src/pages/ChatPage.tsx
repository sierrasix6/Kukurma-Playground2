import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Zap, LogOut, Coins } from "lucide-react";
import { useLocation } from "wouter";
import { useAuth } from "@/context/AuthContext";
import PredictionCard from "@/components/PredictionCard";

interface LastResult {
  date: string;
  opponent: string;
  score: string;
  outcome: "W" | "D" | "L";
  venue: string;
}

interface TeamData {
  name: string;
  league: string;
  badge: string;
  strength: number;
  last_results: LastResult[];
}

interface H2HMatch {
  date: string;
  home: string;
  away: string;
  score: string;
}

interface PredictionData {
  home_team: TeamData;
  away_team: TeamData;
  h2h: H2HMatch[];
  prediction: { home_score: number; away_score: number; score_str: string };
  match_date?: string;
}

interface Message {
  id: string;
  role: "user" | "ai" | "error";
  text: string;
  data?: PredictionData;
  timestamp: Date;
}

const EXAMPLE_PROMPTS = [
  "Chelsea vs Arsenal besok",
  "Barcelona vs Real Madrid",
  "Manchester City vs Liverpool",
];

function makeWelcome(username: string): Message {
  return {
    id: "welcome",
    role: "ai",
    text: `Halo, **${username}**! Selamat datang di Kukurma Playground!\n\nSaya bisa memprediksi skor pertandingan sepak bola berdasarkan data statistik nyata.\n\nCoba tanyakan sesuatu seperti:\n**Chelsea vs Arsenal besok malam**`,
    timestamp: new Date(),
  };
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 mb-4">
      <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
        <Zap size={14} className="text-primary" />
      </div>
      <div className="bg-card border border-border rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex items-center gap-1 h-4">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  );
}

function parseReply(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\n)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="text-foreground font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part === "\n") return <br key={i} />;
    return part;
  });
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isError = message.role === "error";

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-2.5 text-sm leading-relaxed">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-end gap-2 mb-4">
      <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mb-0.5">
        <Zap size={14} className="text-primary" />
      </div>
      <div className="max-w-[85%]">
        <div
          className={`rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed ${
            isError
              ? "bg-destructive/10 border border-destructive/30 text-destructive-foreground"
              : "bg-card border border-border text-card-foreground"
          }`}
        >
          <p className="whitespace-pre-line">{parseReply(message.text)}</p>
        </div>
        {message.data && (
          <PredictionCard
            homeTeam={message.data.home_team}
            awayTeam={message.data.away_team}
            h2h={message.data.h2h}
            prediction={message.data.prediction}
            matchDate={message.data.match_date}
          />
        )}
        <p className="text-[10px] text-muted-foreground mt-1 ml-1">
          {message.timestamp.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

function CreditsBar({ credits }: { credits: number }) {
  const unlimited = credits === -1;
  const pct = unlimited ? 100 : Math.min(100, (credits / 5) * 100);
  const color = unlimited
    ? "bg-primary"
    : credits > 2
    ? "bg-primary"
    : credits > 0
    ? "bg-yellow-400"
    : "bg-red-500";

  return (
    <div className="rounded-lg border border-border bg-muted/20 px-3 py-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Coins size={11} className="text-primary" />
          <p className="text-[10px] font-semibold text-primary uppercase tracking-wide">Kredit</p>
        </div>
        <span className="text-[11px] font-bold text-foreground">
          {unlimited ? "∞" : credits}
        </span>
      </div>
      <div className="h-1 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {!unlimited && (
        <p className="text-[9px] text-muted-foreground mt-1">
          {credits <= 0 ? "Kredit habis" : `${credits} prediksi tersisa`}
        </p>
      )}
    </div>
  );
}

export default function ChatPage() {
  const { user, token, logout, updateCredits } = useAuth();
  const [, setLocation] = useLocation();
  const [messages, setMessages] = useState<Message[]>(() => [makeWelcome(user?.username ?? "")]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleLogout = () => {
    logout();
    setLocation("/login");
  };

  const creditsExhausted = user && user.credits !== -1 && user.credits <= 0;

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    if (creditsExhausted) {
      const errMsg: Message = {
        id: Date.now().toString(),
        role: "error",
        text: "Kredit kamu sudah habis! Kamu telah menggunakan semua 5 kredit prediksi gratis.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
      return;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      text: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: trimmed }),
      });

      if (res.status === 401) {
        logout();
        setLocation("/login");
        return;
      }

      const json = await res.json();

      // Update credit count from response
      if (typeof json.credits_remaining === "number") {
        updateCredits(json.credits_remaining);
      }

      if (res.status === 402) {
        const errMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "error",
          text: "Kredit kamu sudah habis! Kamu telah menggunakan semua 5 kredit prediksi gratis.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errMsg]);
        return;
      }

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        text: json.reply || json.detail || "Maaf, tidak ada respons dari server.",
        data: json.data,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "error",
        text: "Gagal terhubung ke server. Pastikan koneksi internet kamu stabil dan coba lagi.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const showPrompts = messages.length === 1;

  return (
    <div className="flex h-full bg-background">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-64 flex-col bg-sidebar border-r border-sidebar-border p-4 flex-shrink-0">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
            <span className="text-base">⚽</span>
          </div>
          <div>
            <h1 className="font-bold text-sm leading-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Kukurma Playground
            </h1>
            <p className="text-[10px] text-muted-foreground">Football Score Predictor</p>
          </div>
        </div>

        <div className="space-y-1 mb-4">
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium px-2 mb-2">
            Contoh Pertanyaan
          </p>
          {EXAMPLE_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              disabled={loading || !!creditsExhausted}
              className="w-full text-left text-xs px-3 py-2 rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>

        <div className="mt-auto space-y-3 pt-4 border-t border-sidebar-border">
          {/* Credits */}
          {user && <CreditsBar credits={user.credits} />}

          {/* User info + logout */}
          <div className="flex items-center justify-between px-1">
            <div>
              <p className="text-xs font-semibold text-foreground">{user?.username}</p>
              <p className="text-[10px] text-muted-foreground">
                {user?.credits === -1 ? "Admin — kredit unlimited" : `${user?.credits} kredit tersisa`}
              </p>
            </div>
            <button
              onClick={handleLogout}
              title="Keluar"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
            >
              <LogOut size={14} />
            </button>
          </div>

          <div className="rounded-lg bg-primary/10 border border-primary/20 px-3 py-2.5">
            <p className="text-[10px] font-semibold text-primary mb-1">Data Sumber</p>
            <p className="text-[10px] text-muted-foreground leading-relaxed">
              ESPN Public API &mdash; gratis, tanpa API key. Data statistik nyata dari liga dunia.
            </p>
          </div>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-sidebar flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-sm">⚽</span>
          </div>
          <div className="flex-1">
            <h1 className="font-bold text-sm" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Kukurma Playground
            </h1>
            <p className="text-[10px] text-muted-foreground">Football Score Predictor</p>
          </div>
          {/* Mobile: credits badge */}
          {user && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-primary/10 border border-primary/20">
              <Coins size={10} className="text-primary" />
              <span className="text-[10px] font-bold text-primary">
                {user.credits === -1 ? "∞" : user.credits}
              </span>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut size={14} />
          </button>
        </header>

        {/* No credits banner */}
        {creditsExhausted && (
          <div className="flex-shrink-0 bg-yellow-500/10 border-b border-yellow-500/20 px-4 py-2.5">
            <p className="text-xs text-yellow-400 text-center font-medium">
              ⚠️ Kredit kamu sudah habis. Kamu tidak bisa lagi melakukan prediksi.
            </p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <div className="max-w-2xl mx-auto">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Quick prompts */}
        {showPrompts && (
          <div className="px-4 pb-2 flex-shrink-0">
            <div className="max-w-2xl mx-auto flex flex-wrap gap-2">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  disabled={loading || !!creditsExhausted}
                  className="text-xs px-3 py-1.5 rounded-full bg-card border border-border hover:border-primary/40 hover:bg-primary/5 text-muted-foreground hover:text-foreground transition-all disabled:opacity-50"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="px-4 pb-1 pt-2 flex-shrink-0 border-t border-border bg-background">
          <div className="max-w-2xl mx-auto">
            <div className={`flex items-end gap-2 bg-card border rounded-2xl px-4 py-2 transition-colors ${
              creditsExhausted ? "border-yellow-500/30 opacity-60" : "border-border focus-within:border-primary/50"
            }`}>
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
                }}
                onKeyDown={handleKeyDown}
                placeholder={creditsExhausted ? "Kredit habis..." : "Contoh: Chelsea vs Arsenal besok..."}
                disabled={loading || !!creditsExhausted}
                className="flex-1 bg-transparent resize-none text-sm text-foreground placeholder:text-muted-foreground outline-none min-h-[24px] max-h-[120px] py-1 disabled:opacity-50"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim() || !!creditsExhausted}
                className="flex-shrink-0 w-8 h-8 rounded-xl bg-primary hover:bg-primary/90 flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed mb-0.5"
              >
                <Send size={14} className="text-primary-foreground" />
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground text-center mt-1.5">
              Tekan Enter untuk kirim &bull; Shift+Enter untuk baris baru &bull;{" "}
              <span className="text-primary/50 font-medium">@KyonariDev</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
