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

interface Prediction {
  home_score: number;
  away_score: number;
  score_str: string;
}

interface PredictionCardProps {
  homeTeam: TeamData;
  awayTeam: TeamData;
  h2h: H2HMatch[];
  prediction: Prediction;
  matchDate?: string;
}

function TeamBadge({ name, badge }: { name: string; badge: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  if (badge) {
    return (
      <img
        src={badge}
        alt={name}
        className="w-10 h-10 object-contain"
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
          const next = (e.target as HTMLImageElement).nextSibling as HTMLElement;
          if (next) next.style.display = "flex";
        }}
      />
    );
  }

  return (
    <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center text-sm font-bold text-muted-foreground">
      {initials}
    </div>
  );
}

function FormPill({ outcome }: { outcome: "W" | "D" | "L" }) {
  const colors = {
    W: "bg-green-500/20 text-green-400 border border-green-500/30",
    D: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
    L: "bg-red-500/20 text-red-400 border border-red-500/30",
  };
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${colors[outcome]}`}>
      {outcome}
    </span>
  );
}

function StrengthBar({ value, max, label, side }: { value: number; max: number; label: string; side: "left" | "right" }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 50;
  return (
    <div className={`flex items-center gap-2 ${side === "right" ? "flex-row-reverse" : ""}`}>
      <span className="text-xs text-muted-foreground w-6 text-center font-mono">{value}</span>
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function PredictionCard({
  homeTeam,
  awayTeam,
  prediction,
  h2h,
  matchDate,
}: PredictionCardProps) {
  const maxStrength = Math.max(homeTeam.strength, awayTeam.strength, 1);

  return (
    <div className="mt-3 rounded-xl border border-border bg-background/60 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2 bg-muted/40 border-b border-border flex items-center justify-between">
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Analisis Pertandingan</span>
        {matchDate && (
          <span className="text-xs text-muted-foreground">{matchDate}</span>
        )}
      </div>

      {/* Teams + Score */}
      <div className="px-4 py-5 flex items-center gap-3">
        {/* Home team */}
        <div className="flex-1 flex flex-col items-center gap-2 text-center">
          <TeamBadge name={homeTeam.name} badge={homeTeam.badge} />
          <div>
            <p className="font-semibold text-sm leading-tight">{homeTeam.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{homeTeam.league || "Home"}</p>
          </div>
        </div>

        {/* Score */}
        <div className="flex flex-col items-center gap-1 px-2">
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold font-mono text-primary leading-none">
              {prediction.home_score}
            </span>
            <span className="text-xl text-muted-foreground font-light">-</span>
            <span className="text-4xl font-bold font-mono text-foreground/70 leading-none">
              {prediction.away_score}
            </span>
          </div>
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">
            Prediksi
          </span>
        </div>

        {/* Away team */}
        <div className="flex-1 flex flex-col items-center gap-2 text-center">
          <TeamBadge name={awayTeam.name} badge={awayTeam.badge} />
          <div>
            <p className="font-semibold text-sm leading-tight">{awayTeam.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{awayTeam.league || "Away"}</p>
          </div>
        </div>
      </div>

      {/* Strength comparison */}
      <div className="px-4 pb-3">
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium mb-2">
          Kekuatan Tim (5 Laga Terakhir)
        </p>
        <div className="grid grid-cols-2 gap-2">
          <StrengthBar value={homeTeam.strength} max={maxStrength * 1.2} label={homeTeam.name} side="left" />
          <StrengthBar value={awayTeam.strength} max={maxStrength * 1.2} label={awayTeam.name} side="right" />
        </div>
      </div>

      {/* Form */}
      {(homeTeam.last_results.length > 0 || awayTeam.last_results.length > 0) && (
        <div className="px-4 pb-4 grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium mb-1.5">
              Form {homeTeam.name.split(" ")[0]}
            </p>
            <div className="flex gap-1">
              {homeTeam.last_results.map((r, i) => (
                <FormPill key={i} outcome={r.outcome} />
              ))}
            </div>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium mb-1.5">
              Form {awayTeam.name.split(" ")[0]}
            </p>
            <div className="flex gap-1">
              {awayTeam.last_results.map((r, i) => (
                <FormPill key={i} outcome={r.outcome} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* H2H */}
      {h2h.length > 0 && (
        <div className="px-4 pb-4 border-t border-border pt-3">
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium mb-2">
            Head-to-Head Terakhir
          </p>
          <div className="space-y-1">
            {h2h.slice(0, 3).map((match, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{match.date}</span>
                <span className="font-medium">{match.home} <span className="text-primary font-mono">{match.score}</span> {match.away}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data source */}
      <div className="px-4 py-2 bg-muted/20 border-t border-border">
        <p className="text-[10px] text-muted-foreground">
          Data: ESPN Public API &mdash; gratis, tanpa API key
        </p>
      </div>
    </div>
  );
}
