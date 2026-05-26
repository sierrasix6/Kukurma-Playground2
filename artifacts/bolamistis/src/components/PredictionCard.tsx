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
      <div className="w-10 h-10 rounded-xl bg-card border border-border/80 flex items-center justify-center p-1.5 shadow-2xs">
        <img
          src={badge}
          alt={name}
          className="w-full h-full object-contain"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
            const next = (e.target as HTMLImageElement).nextSibling as HTMLElement;
            if (next) next.style.display = "flex";
          }}
        />
      </div>
    );
  }

  return (
    <div className="w-10 h-10 rounded-xl bg-muted border border-border flex items-center justify-center text-xs font-bold text-muted-foreground shadow-2xs">
      {initials}
    </div>
  );
}

function FormPill({ outcome }: { outcome: "W" | "D" | "L" }) {
  const colors = {
    W: "text-emerald-500 border border-emerald-500/15 bg-emerald-500/5",
    D: "text-amber-500 border border-amber-500/15 bg-amber-500/5",
    L: "text-rose-500 border border-rose-500/15 bg-rose-500/5",
  };
  return (
    <span className={`inline-flex items-center justify-center w-5.5 h-5.5 rounded-md text-[10px] font-bold tracking-tight shadow-3xs ${colors[outcome]}`}>
      {outcome}
    </span>
  );
}

function StrengthBar({ value, max, side }: { value: number; max: number; side: "left" | "right" }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 50;
  return (
    <div className={`flex items-center gap-2 w-full ${side === "right" ? "flex-row-reverse" : ""}`}>
      <span className="text-[10px] font-bold text-foreground/80 font-mono w-5 text-center">{value}</span>
      <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-700"
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
    <div className="mt-3 rounded-2xl border border-border/80 bg-card/45 backdrop-blur-md overflow-hidden shadow-sm transition-all duration-300 hover:border-border hover:shadow-md max-w-md md:max-w-full">
      {/* Header banner */}
      <div className="px-4 py-2.5 bg-muted/20 border-b border-border/60 flex items-center justify-between">
        <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-wider">Statistik & Prediksi</span>
        {matchDate && (
          <span className="text-[9px] text-muted-foreground font-bold tracking-tight">{matchDate}</span>
        )}
      </div>

      {/* Teams + Score */}
      <div className="px-5 py-6 flex items-center gap-4">
        {/* Home team */}
        <div className="flex-1 flex flex-col items-center gap-2.5 text-center min-w-0">
          <TeamBadge name={homeTeam.name} badge={homeTeam.badge} />
          <div className="w-full">
            <p className="font-bold text-xs text-foreground leading-tight truncate">{homeTeam.name}</p>
            <p className="text-[10px] text-muted-foreground/75 mt-0.5 font-medium truncate">{homeTeam.league || "Home Team"}</p>
          </div>
        </div>

        {/* Prediction Score */}
        <div className="flex flex-col items-center gap-1.5 px-3 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="text-3xl font-extrabold font-mono text-primary leading-none tracking-tighter">
              {prediction.home_score}
            </span>
            <span className="text-sm text-muted-foreground/50 font-semibold">-</span>
            <span className="text-3xl font-extrabold font-mono text-foreground/80 leading-none tracking-tighter">
              {prediction.away_score}
            </span>
          </div>
          <span className="text-[8px] uppercase tracking-widest text-muted-foreground font-bold">
            Prediksi Skor
          </span>
        </div>

        {/* Away team */}
        <div className="flex-1 flex flex-col items-center gap-2.5 text-center min-w-0">
          <TeamBadge name={awayTeam.name} badge={awayTeam.badge} />
          <div className="w-full">
            <p className="font-bold text-xs text-foreground leading-tight truncate">{awayTeam.name}</p>
            <p className="text-[10px] text-muted-foreground/75 mt-0.5 font-medium truncate">{awayTeam.league || "Away Team"}</p>
          </div>
        </div>
      </div>

      {/* Strength Comparison */}
      <div className="px-5 pb-4.5 border-t border-border/40 pt-3.5">
        <p className="text-[9px] uppercase tracking-widest text-muted-foreground font-bold mb-2.5">
          Skor Kekuatan (Weighted Form)
        </p>
        <div className="grid grid-cols-2 gap-4">
          <StrengthBar value={homeTeam.strength} max={maxStrength * 1.1} side="left" />
          <StrengthBar value={awayTeam.strength} max={maxStrength * 1.1} side="right" />
        </div>
      </div>

      {/* Form Pills */}
      {(homeTeam.last_results.length > 0 || awayTeam.last_results.length > 0) && (
        <div className="px-5 pb-4.5 grid grid-cols-2 gap-4">
          <div>
            <p className="text-[9px] uppercase tracking-widest text-muted-foreground font-bold mb-2">
              Form {homeTeam.name.split(" ")[0]}
            </p>
            <div className="flex gap-1">
              {homeTeam.last_results.map((r, i) => (
                <FormPill key={i} outcome={r.outcome} />
              ))}
            </div>
          </div>
          <div>
            <p className="text-[9px] uppercase tracking-widest text-muted-foreground font-bold mb-2">
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

      {/* H2H Matches */}
      {h2h.length > 0 && (
        <div className="px-5 pb-4 border-t border-border/40 pt-3.5">
          <p className="text-[9px] uppercase tracking-widest text-muted-foreground font-bold mb-3">
            Pertemuan Terakhir (H2H)
          </p>
          <div className="space-y-2">
            {h2h.slice(0, 3).map((match, i) => (
              <div key={i} className="flex items-center justify-between text-[11px] font-medium">
                <span className="text-muted-foreground/80 font-mono text-[10px]">{match.date}</span>
                <div className="flex items-center gap-1.5 text-foreground/85">
                  <span className="truncate max-w-[80px] text-right">{match.home}</span>
                  <span className="text-primary font-bold font-mono px-1 rounded bg-primary/5 border border-primary/10 text-[10px]">{match.score}</span>
                  <span className="truncate max-w-[80px]">{match.away}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer / Data Source */}
      <div className="px-5 py-2.5 bg-muted/10 border-t border-border/40 flex items-center justify-between">
        <p className="text-[9px] text-muted-foreground/60 font-medium">
          Sumber: ESPN Public API &bull; real-time stats
        </p>
      </div>
    </div>
  );
}
