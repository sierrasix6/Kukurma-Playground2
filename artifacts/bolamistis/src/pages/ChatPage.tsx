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
  stats?: {
    weighted_points: number;
    avg_scored: number;
    avg_conceded: number;
    home_avg_scored: number;
    home_avg_conceded: number;
    away_avg_scored: number;
    away_avg_conceded: number;
    win_streak: number;
    loss_streak: number;
    clean_sheets: number;
    failed_to_score: number;
    form_label: string;
    form_icons: string[];
    goal_diff: number;
  };
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
  "Arsenal vs Manchester City 19 April 2026",
];

function makeWelcome(username: string): Message {
  return {
    id: "welcome",
    role: "ai",
    text: `Halo, **${username}**! Selamat datang di Kyonayr Playground!\n\nSaya bisa memprediksi skor pertandingan sepak bola berdasarkan data statistik nyata.\n\nCoba tanyakan sesuatu seperti:\n**Club vs Club Tanggal**`,
    timestamp: new Date(),
  };
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 mb-4 animate-fade-in">
      <div className="w-8 h-8 rounded-full border border-border bg-muted/40 flex items-center justify-center flex-shrink-0">
        <Zap size={13} className="text-primary" />
      </div>
      <div className="bg-card border border-border/80 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1.2 h-3">
          <span className="typing-dot bg-muted-foreground/60" />
          <span className="typing-dot bg-muted-foreground/60" />
          <span className="typing-dot bg-muted-foreground/60" />
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
      <div className="flex justify-end mb-4 animate-fade-in">
        <div className="max-w-[75%] bg-secondary border border-border/60 text-foreground rounded-2xl rounded-br-sm px-4.5 py-2.5 text-sm leading-relaxed shadow-sm">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-end gap-3 mb-4 animate-fade-in">
      <div className="w-8 h-8 rounded-full border border-border bg-muted/40 flex items-center justify-center flex-shrink-0 mb-0.5 shadow-sm">
        <Zap size={13} className="text-primary" />
      </div>
      <div className="max-w-[85%]">
        <div
          className={`rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isError
              ? "bg-destructive/5 border border-destructive/20 text-destructive-foreground"
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
    ? "bg-amber-500/80"
    : "bg-destructive/80";

  return (
    <div className="rounded-xl border border-border bg-muted/30 p-3 shadow-2xs">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Coins size={11} className="text-muted-foreground" />
          <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">Kredit Prediksi</p>
        </div>
        <span className="text-[11px] font-bold text-foreground font-mono">
          {unlimited ? "∞" : credits}
        </span>
      </div>
      <div className="h-1 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {!unlimited && (
        <p className="text-[9px] text-muted-foreground/80 mt-1.5 font-medium">
          {credits <= 0 ? "Kredit telah habis" : `${credits} dari 5 prediksi gratis`}
        </p>
      )}
    </div>
  );
}


const generateClientAiReasoning = async (data: PredictionData): Promise<string> => {
  const homeName = data.home_team.name;
  const awayName = data.away_team.name;
  
  const homeResultsStr = data.home_team.last_results
    ? data.home_team.last_results
        .map((r) => `- Lawan ${r.opponent}: ${r.score} (${r.outcome}) di ${r.venue === "home" ? "Kandang" : "Tandang"}`)
        .join("\n")
    : "Data tidak tersedia";
  const awayResultsStr = data.away_team.last_results
    ? data.away_team.last_results
        .map((r) => `- Lawan ${r.opponent}: ${r.score} (${r.outcome}) di ${r.venue === "home" ? "Kandang" : "Tandang"}`)
        .join("\n")
    : "Data tidak tersedia";
    
  const h2hStr = data.h2h && data.h2h.length > 0
    ? data.h2h.map((m) => `- ${m.home} vs ${m.away}: ${m.score} (${m.date})`).join("\n")
    : "Tidak ada catatan pertemuan baru-baru ini.";
    
  const homeStats = data.home_team.stats;
  const awayStats = data.away_team.stats;
  const predictedHome = data.prediction.home_score;
  const predictedAway = data.prediction.away_score;
  
  const homeStatsStr = homeStats
    ? `Rata-rata gol dicetak ${homeStats.avg_scored}, kebobolan ${homeStats.avg_conceded}. Streak menang: ${homeStats.win_streak}, Clean sheet: ${homeStats.clean_sheets}.`
    : "Tidak ada data statistik.";
  const awayStatsStr = awayStats
    ? `Rata-rata gol dicetak ${awayStats.avg_scored}, kebobolan ${awayStats.avg_conceded}. Streak menang: ${awayStats.win_streak}, Clean sheet: ${awayStats.clean_sheets}.`
    : "Tidak ada data statistik.";

  const prompt = `
[System Instruction]
Anda adalah analis sepak bola profesional, pengamat taktis, dan jurnalis olahraga senior.
Tugas Anda adalah menulis ulasan analisis pertandingan yang sangat mendalam, taktis, objektif, dan berbobot dalam Bahasa Indonesia.
PENTING: Jangan gunakan emoji dalam ulasan Anda (maksimal hanya boleh 1 emoji di seluruh ulasan). Tulis dengan nada bahasa jurnalistik yang formal, analitis, dan profesional.
PENTING: Tulis ulasan secara padat, ringkas, langsung pada intinya, dan hindari penjelasan bertele-tele agar respon cepat. Tulis maksimal 2-3 paragraf singkat.

[Data Statistik Pertandingan]
Tim Tuan Rumah: ${homeName}
Tim Tamu: ${awayName}

Laga Terakhir ${homeName}:
${homeResultsStr}
Statistik ${homeName}: ${homeStatsStr}

Laga Terakhir ${awayName}:
${awayResultsStr}
Statistik ${awayName}: ${awayStatsStr}

Catatan Head-to-Head (H2H):
${h2hStr}

Prediksi Skor Matematis (Poisson Engine): ${homeName} ${predictedHome} - ${predictedAway} ${awayName}

[Struktur Output]
Tulis analisis Anda dengan membaginya ke dalam 3 poin berikut:
1. **Analisis Taktis & Form Terkini**: Penjelasan objektif dan mendalam mengenai performa, kelemahan, dan kekuatan terkini dari kedua tim.
2. **Kunci Pertandingan & Analisis Venue**: Bahas detail performa kandang vs tandang (home/away splits), pertahanan vs serangan, dan pengaruh keunggulan stadion.
3. **Prediksi Skor & Verdict**: Berikan penjelasan taktis logis mengapa skor akhir diprediksi berkisar ${predictedHome} - ${predictedAway} (Anda dapat menyetujui atau menyesuaikan tipis skor prediksi ini berdasarkan analisis taktis Anda).
`;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 20000); // 20s timeout
  
  try {
    const url = `https://text.pollinations.ai/${encodeURIComponent(prompt.trim())}`;
    const response = await fetch(url, {
      signal: controller.signal,
    });
    clearTimeout(id);
    if (response.ok) {
      const text = await response.text();
      if (text && text.trim()) {
        return text.trim();
      }
    }
  } catch (e) {
    clearTimeout(id);
    throw e;
  }
  return "";
};


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

      let replyText = json.reply || json.detail || "Maaf, tidak ada respons dari server.";

      if (json.data) {
        try {
          const clientAi = await generateClientAiReasoning(json.data);
          if (clientAi) {
            const matchDate = json.data.match_date;
            replyText = `Berikut ulasan profesional pertandingan **${json.data.home_team.name}** vs **${json.data.away_team.name}**${
              matchDate ? ` (${matchDate})` : ""
            }:\n\n${clientAi}`;
          }
        } catch (e) {
          console.warn("Client-side AI reasoning failed, using backend fallback:", e);
        }
      }

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        text: replyText,
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
    <div className="flex h-full bg-background font-sans text-foreground">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-64 flex-col bg-sidebar border-r border-border p-5 flex-shrink-0 justify-between">
        <div className="flex flex-col gap-6">
          {/* Logo header */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl border border-border bg-card flex items-center justify-center shadow-xs">
              <span className="text-base">⚽</span>
            </div>
            <div>
              <h1 className="font-bold text-sm leading-tight tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Kyonayr Playground
              </h1>
              <p className="text-[9px] text-muted-foreground uppercase tracking-widest font-semibold">Football Predictor</p>
            </div>
          </div>

          {/* Examples list */}
          <div className="space-y-1.5">
            <p className="text-[9px] uppercase tracking-widest text-muted-foreground font-bold px-2 mb-2">
              Contoh Pertanyaan
            </p>
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => sendMessage(p)}
                disabled={loading || !!creditsExhausted}
                className="w-full text-left text-xs px-3 py-2 rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-all duration-150 disabled:opacity-50 cursor-pointer"
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Sidebar bottom */}
        <div className="space-y-4 pt-4 border-t border-border">
          {/* Credits info */}
          {user && <CreditsBar credits={user.credits} />}

          {/* User profile & logout */}
          <div className="flex items-center justify-between px-1">
            <div className="min-w-0">
              <p className="text-xs font-bold text-foreground truncate">{user?.username}</p>
              <p className="text-[9px] text-muted-foreground/80 font-medium">
                {user?.credits === -1 ? "Administrator" : "Free Account"}
              </p>
            </div>
            <button
              onClick={handleLogout}
              title="Keluar"
              className="w-8 h-8 rounded-lg border border-transparent flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent hover:border-border transition-all duration-150 cursor-pointer"
            >
              <LogOut size={13} />
            </button>
          </div>

          {/* Data source card */}
          <div className="rounded-xl bg-muted/20 border border-border/80 px-3.5 py-3 shadow-2xs">
            <p className="text-[9px] font-bold text-foreground/80 uppercase tracking-wider mb-1">Data Sumber</p>
            <p className="text-[10px] text-muted-foreground/80 leading-relaxed font-medium">
              ESPN Public API &bull; data statistik sepak bola riil liga-liga top dunia secara langsung.
            </p>
          </div>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-sidebar flex-shrink-0">
          <div className="w-8 h-8 rounded-xl border border-border bg-card flex items-center justify-center shadow-2xs">
            <span className="text-sm">⚽</span>
          </div>
          <div className="flex-1">
            <h1 className="font-bold text-sm leading-tight tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Kyonayr Playground
            </h1>
            <p className="text-[9px] text-muted-foreground uppercase tracking-widest font-semibold">Predictor</p>
          </div>
          {/* Mobile: credits badge */}
          {user && (
            <div className="flex items-center gap-1.2 px-2.5 py-1 rounded-full bg-muted/40 border border-border shadow-2xs">
              <Coins size={10} className="text-muted-foreground" />
              <span className="text-[10px] font-bold text-foreground font-mono">
                {user.credits === -1 ? "∞" : user.credits}
              </span>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
          >
            <LogOut size={13} />
          </button>
        </header>

        {/* No credits banner */}
        {creditsExhausted && (
          <div className="flex-shrink-0 bg-destructive/5 border-b border-destructive/15 px-4 py-2.5">
            <p className="text-xs text-destructive/80 text-center font-medium">
              ⚠️ Kredit prediksi gratis Anda telah habis.
            </p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-thin">
          <div className="max-w-2xl mx-auto space-y-2">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Quick prompts */}
        {showPrompts && (
          <div className="px-4 pb-3 flex-shrink-0">
            <div className="max-w-2xl mx-auto flex flex-wrap gap-2 justify-center md:justify-start">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  disabled={loading || !!creditsExhausted}
                  className="text-xs px-3.5 py-2 rounded-xl bg-card border border-border hover:border-muted-foreground/30 hover:bg-muted/20 text-muted-foreground hover:text-foreground transition-all duration-150 disabled:opacity-50 cursor-pointer shadow-2xs"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="px-4 pb-4 pt-3 flex-shrink-0 border-t border-border bg-background">
          <div className="max-w-2xl mx-auto">
            <div className={`flex items-end gap-2 bg-card border rounded-2xl px-4 py-3.5 transition-all duration-200 shadow-sm ${
              creditsExhausted ? "border-destructive/20 opacity-60" : "border-border focus-within:border-border-foreground/30 focus-within:ring-1 focus-within:ring-border/40"
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
                placeholder={creditsExhausted ? "Kredit habis..." : "Chelsea vs Arsenal besok..."}
                disabled={loading || !!creditsExhausted}
                className="flex-1 bg-transparent resize-none text-sm text-foreground placeholder:text-muted-foreground/60 outline-none min-h-[24px] max-h-[120px] py-0.5 disabled:opacity-50 font-medium"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim() || !!creditsExhausted}
                className="flex-shrink-0 w-8 h-8 rounded-xl bg-primary text-primary-foreground hover:opacity-90 flex items-center justify-center transition-all disabled:bg-muted disabled:text-muted-foreground disabled:opacity-40 mb-0.5 cursor-pointer disabled:cursor-not-allowed shadow-xs"
              >
                <Send size={13} />
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground/60 text-center mt-2.5 font-medium">
              Enter untuk mengirim &bull; Shift+Enter untuk baris baru &bull;{" "}
              <span className="text-primary/70 font-semibold">@KyonariDev</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

