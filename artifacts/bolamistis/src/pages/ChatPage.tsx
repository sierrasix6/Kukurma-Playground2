import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Zap, LogOut, Coins, Trophy, Settings, Cpu } from "lucide-react";
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
    <div className="flex items-end gap-3.5 mb-4 animate-fade-in">
      <div className="w-7 h-7 rounded-xl border border-white/[0.03] bg-zinc-900 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-3xs">
        <Cpu size={11} className="text-muted-foreground/75" />
      </div>
      <div className="bg-zinc-900/35 border border-white/[0.03] rounded-2xl rounded-bl-none px-4 py-2.5 shadow-xs backdrop-blur-md">
        <div className="flex items-center gap-1.2 h-3">
          <span className="typing-dot bg-muted-foreground/50" />
          <span className="typing-dot bg-muted-foreground/50" />
          <span className="typing-dot bg-muted-foreground/50" />
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
        <div className="max-w-[75%] bg-zinc-900 border border-white/[0.04] text-foreground/90 rounded-2xl rounded-tr-none px-4 py-2.5 text-xs font-semibold leading-relaxed shadow-xs">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3.5 mb-5 animate-fade-in">
      <div className="w-7 h-7 rounded-xl border border-emerald-500/10 bg-emerald-500/5 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-3xs">
        <Cpu size={11} className="text-emerald-400" />
      </div>
      <div className="max-w-[85%] flex-1">
        <div
          className={`rounded-2xl rounded-tl-none px-4.5 py-3 text-xs leading-relaxed shadow-xs font-medium ${
            isError
              ? "bg-rose-500/5 border border-rose-500/10 text-rose-300"
              : "bg-zinc-900/10 border border-white/[0.03] text-foreground/90 backdrop-blur-md"
          }`}
        >
          <p className="whitespace-pre-line leading-relaxed">{parseReply(message.text)}</p>
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
        <p className="text-[9px] text-muted-foreground/30 mt-1.5 ml-1 font-mono tracking-wider uppercase">
          {message.timestamp.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

function CreditsBar({ credits }: { credits: number }) {
  const unlimited = credits === -1;
  return (
    <div className="rounded-2xl border border-white/[0.03] bg-zinc-950/20 p-3.5 space-y-2 shadow-2xs backdrop-blur-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-4.5 h-4.5 rounded-lg bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center">
            <Coins size={9} className="text-emerald-400" />
          </div>
          <p className="text-[8px] font-extrabold text-muted-foreground/75 uppercase tracking-wider font-mono">Kredit Prediksi</p>
        </div>
        <span className="text-[10px] font-extrabold text-foreground/95 font-mono bg-zinc-900 border border-white/[0.04] px-1.5 py-0.5 rounded shadow-3xs">
          {unlimited ? "∞" : `${credits}/5`}
        </span>
      </div>
      {!unlimited && (
        <p className="text-[8px] text-muted-foreground/40 font-semibold tracking-wide">
          {credits <= 0 ? "Kredit gratis telah habis" : `${credits} prediksi tersisa`}
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
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem("gemini_api_key") || "");
  const [showSettings, setShowSettings] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleLogout = () => {
    logout();
    setLocation("/login");
  };

  const handleGeminiKeyChange = (val: string) => {
    setGeminiKey(val);
    if (val.trim()) {
      localStorage.setItem("gemini_api_key", val.trim());
    } else {
      localStorage.removeItem("gemini_api_key");
    }
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
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      };
      if (geminiKey.trim()) {
        headers["x-gemini-key"] = geminiKey.trim();
      }

      const res = await fetch("/api/chat", {
        method: "POST",
        headers,
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

      if (json.data && !json.ai_generated_by_server) {
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
    <div className="flex h-full bg-zinc-950 font-sans text-foreground">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-64 flex-col bg-zinc-950/80 border-r border-white/[0.04] p-6 flex-shrink-0 justify-between backdrop-blur-xl">
        <div className="flex flex-col gap-6">
          {/* Logo header */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center shadow-xs">
              <Trophy size={13} className="text-emerald-400" />
            </div>
            <div>
              <h1 className="font-extrabold text-xs tracking-wider text-foreground/90 uppercase font-mono">
                Kyonayr Predictor
              </h1>
              <p className="text-[7px] text-muted-foreground/45 uppercase tracking-widest font-extrabold font-mono">STATISTICS ENGINE</p>
            </div>
          </div>

          {/* Settings panel */}
          <div className="rounded-2xl border border-white/[0.03] bg-zinc-950/20 p-3.5 space-y-2 shadow-2xs backdrop-blur-md">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center justify-between w-full text-left text-muted-foreground hover:text-foreground/90 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <Settings size={10} className="text-zinc-500" />
                <span className="text-[8px] font-extrabold uppercase tracking-wider font-mono">PENGATURAN AI</span>
              </div>
              <span className="text-[7px] bg-zinc-900 border border-white/[0.04] px-1.5 py-0.5 rounded font-mono font-bold text-muted-foreground/80 hover:bg-zinc-800 transition-all cursor-pointer">
                {geminiKey ? "GEMINI" : "CODESTRAL"}
              </span>
            </button>
            
            {showSettings && (
              <div className="space-y-1.5 pt-1.5 border-t border-white/[0.02] animate-fade-in">
                <p className="text-[8px] text-muted-foreground/40 leading-normal font-medium">
                  Masukkan Gemini API Key untuk membuka ulasan analitis Gemini 2.0 Flash yang lebih cerdas.
                </p>
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => handleGeminiKeyChange(e.target.value)}
                  placeholder="Gemini API Key..."
                  className="w-full px-2.5 py-1.5 text-[9px] font-mono rounded-lg bg-zinc-950 border border-white/[0.04] text-foreground placeholder:text-muted-foreground/20 focus:outline-none focus:border-emerald-500/20 transition-all"
                />
              </div>
            )}
          </div>

          {/* Examples list */}
          <div className="space-y-1.5">
            <p className="text-[8px] uppercase tracking-widest text-muted-foreground/40 font-bold font-mono px-2.5 mb-1">
              Contoh Pertanyaan
            </p>
            <div className="space-y-1">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  disabled={loading || !!creditsExhausted}
                  className="w-full text-left text-[11px] px-3 py-1.5 rounded-xl text-muted-foreground/75 hover:bg-white/[0.01] border border-transparent hover:border-white/[0.01] hover:text-foreground/90 transition-all duration-200 disabled:opacity-50 cursor-pointer font-medium"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar bottom */}
        <div className="space-y-4 pt-4 border-t border-white/[0.04]">
          {/* Credits info */}
          {user && <CreditsBar credits={user.credits} />}

          {/* User profile & logout */}
          <div className="flex items-center justify-between px-1">
            <div className="min-w-0">
              <p className="text-xs font-bold text-foreground/90 truncate">{user?.username}</p>
              <p className="text-[8px] text-muted-foreground/40 font-bold uppercase tracking-widest font-mono">
                {user?.credits === -1 ? "Administrator" : "Free Account"}
              </p>
            </div>
            <button
              onClick={handleLogout}
              title="Keluar"
              className="w-8 h-8 rounded-xl border border-white/[0.02] bg-zinc-900/30 flex items-center justify-center text-muted-foreground hover:text-foreground/90 hover:bg-white/[0.01] hover:border-white/[0.04] transition-all duration-200 cursor-pointer shadow-3xs"
            >
              <LogOut size={12} />
            </button>
          </div>

          {/* Data source card */}
          <div className="rounded-xl border border-white/[0.02] bg-zinc-950/10 px-3.5 py-2.5 text-[8px] text-muted-foreground/40 leading-relaxed font-semibold font-mono">
            ESPN Public API &bull; data statistik sepak bola riil liga-liga top dunia secara langsung.
          </div>
        </div>
      </aside>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0 bg-zinc-950">
        {/* Mobile header */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-white/[0.04] bg-zinc-950/80 backdrop-blur-md flex-shrink-0">
          <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center shadow-2xs">
            <Trophy size={13} className="text-emerald-400" />
          </div>
          <div className="flex-1">
            <h1 className="font-extrabold text-xs tracking-wider text-foreground/90 uppercase font-mono leading-none">
              Kyonayr Predictor
            </h1>
            <p className="text-[7px] text-muted-foreground/45 uppercase tracking-widest font-extrabold font-mono mt-0.5">STATISTICS ENGINE</p>
          </div>
          {/* Mobile: credits badge */}
          {user && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-zinc-900 border border-white/[0.04] shadow-3xs">
              <Coins size={9} className="text-emerald-400" />
              <span className="text-[9px] font-bold text-foreground/95 font-mono">
                {user.credits === -1 ? "∞" : user.credits}
              </span>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-8 h-8 flex items-center justify-center rounded-xl bg-zinc-900 border border-white/[0.02] text-muted-foreground hover:text-foreground/95 hover:bg-white/[0.01] transition-colors cursor-pointer"
          >
            <LogOut size={12} />
          </button>
        </header>

        {/* No credits banner */}
        {creditsExhausted && (
          <div className="flex-shrink-0 bg-rose-500/5 border-b border-rose-500/10 px-4 py-2.5">
            <p className="text-xs text-rose-400/90 text-center font-semibold tracking-wide">
              ⚠️ Kredit prediksi gratis Anda telah habis.
            </p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-thin">
          <div className="max-w-2xl mx-auto space-y-3">
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
            <div className="max-w-2xl mx-auto flex flex-wrap gap-2 justify-center md:justify-start animate-fade-in">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  disabled={loading || !!creditsExhausted}
                  className="text-[9px] font-bold uppercase tracking-wider px-3.5 py-1.5 rounded-xl bg-zinc-900/10 border border-white/[0.03] hover:border-white/[0.06] hover:bg-white/[0.01] text-muted-foreground/60 hover:text-foreground/90 transition-all duration-200 disabled:opacity-50 cursor-pointer shadow-3xs"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="px-4 pb-4 pt-3 flex-shrink-0 border-t border-white/[0.04] bg-zinc-950/80 backdrop-blur-md">
          <div className="max-w-2xl mx-auto">
            <div className={`flex items-end gap-3 bg-zinc-900/10 border rounded-2xl px-4 py-3 shadow-inner transition-all duration-200 ${
              creditsExhausted 
                ? "border-rose-500/10 opacity-60" 
                : "border-white/[0.04] focus-within:border-white/[0.08]"
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
                placeholder={creditsExhausted ? "Kredit habis..." : "Ketik prediksi tim, contoh: Chelsea vs Arsenal..."}
                disabled={loading || !!creditsExhausted}
                className="flex-1 bg-transparent resize-none text-xs text-foreground placeholder:text-muted-foreground/30 outline-none min-h-[20px] max-h-[120px] py-1 disabled:opacity-50 font-medium leading-relaxed"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim() || !!creditsExhausted}
                className="flex-shrink-0 w-7 h-7 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 hover:scale-[1.02] flex items-center justify-center transition-all duration-200 disabled:bg-zinc-900 disabled:text-zinc-700 disabled:scale-100 disabled:opacity-30 mb-0.5 cursor-pointer disabled:cursor-not-allowed shadow-sm"
              >
                <Send size={11} />
              </button>
            </div>
            <p className="text-[8px] text-muted-foreground/30 text-center mt-2.5 font-bold uppercase tracking-widest font-mono">
              Enter untuk mengirim &bull; Shift+Enter untuk baris baru &bull;{" "}
              <span className="text-emerald-500/60 font-extrabold">BOLAMISTIS ANALYTICS</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
