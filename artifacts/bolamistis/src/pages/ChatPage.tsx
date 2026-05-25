import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Zap } from "lucide-react";
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

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "ai",
  text: "Selamat datang di BolaMistis AI!\n\nSaya bisa memprediksi skor pertandingan sepak bola berdasarkan data statistik nyata.\n\nCoba tanyakan sesuatu seperti:\n**Chelsea vs Arsenal besok malam**",
  timestamp: new Date(),
};

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
        <div
          data-testid={`message-user-${message.id}`}
          className="max-w-[75%] bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-2.5 text-sm leading-relaxed"
        >
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
          data-testid={`message-ai-${message.id}`}
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

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      const json = await res.json();

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        text: json.reply || "Maaf, tidak ada respons dari server.",
        data: json.data,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "error",
        text: "Gagal terhubung ke server. Pastikan koneksi internet Anda stabil dan coba lagi.",
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
            <Zap size={18} className="text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-bold text-sm leading-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              BolaMistis AI
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
              data-testid={`prompt-${p}`}
              onClick={() => sendMessage(p)}
              disabled={loading}
              className="w-full text-left text-xs px-3 py-2 rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>

        <div className="mt-auto pt-4 border-t border-sidebar-border">
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
            <Zap size={15} className="text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-bold text-sm" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              BolaMistis AI
            </h1>
            <p className="text-[10px] text-muted-foreground">Football Score Predictor</p>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4" data-testid="chat-messages">
          <div className="max-w-2xl mx-auto">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Quick prompts (shown when chat is empty) */}
        {showPrompts && (
          <div className="px-4 pb-2 flex-shrink-0">
            <div className="max-w-2xl mx-auto flex flex-wrap gap-2">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  data-testid={`quick-prompt-${p}`}
                  onClick={() => sendMessage(p)}
                  disabled={loading}
                  className="text-xs px-3 py-1.5 rounded-full bg-card border border-border hover:border-primary/40 hover:bg-primary/5 text-muted-foreground hover:text-foreground transition-all disabled:opacity-50"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="px-4 pb-4 pt-2 flex-shrink-0 border-t border-border bg-background">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-end gap-2 bg-card border border-border rounded-2xl px-4 py-2 focus-within:border-primary/50 transition-colors">
              <textarea
                ref={inputRef}
                data-testid="input-message"
                rows={1}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
                }}
                onKeyDown={handleKeyDown}
                placeholder="Contoh: Chelsea vs Arsenal besok..."
                disabled={loading}
                className="flex-1 bg-transparent resize-none text-sm text-foreground placeholder:text-muted-foreground outline-none min-h-[24px] max-h-[120px] py-1 disabled:opacity-50"
              />
              <button
                data-testid="button-send"
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim()}
                className="flex-shrink-0 w-8 h-8 rounded-xl bg-primary hover:bg-primary/90 flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed mb-0.5"
              >
                <Send size={14} className="text-primary-foreground" />
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground text-center mt-1.5">
              Tekan Enter untuk kirim &bull; Shift+Enter untuk baris baru
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
