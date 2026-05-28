import { useState } from "react";
import { Users } from "lucide-react";

interface LastResult {
  date: string;
  opponent: string;
  score: string;
  outcome: "W" | "D" | "L";
  venue: string;
}

interface RosterPlayer {
  name: string;
  jersey: string;
  position: string;
  age: string;
}

interface TeamData {
  name: string;
  league: string;
  badge: string;
  strength: number;
  last_results: LastResult[];
  roster?: RosterPlayer[];
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
      <div className="w-10 h-10 rounded-xl bg-zinc-900/60 border border-white/[0.04] flex items-center justify-center p-1.5 shadow-2xs">
        <img
          src={badge}
          alt={name}
          className="w-full h-full object-contain filter drop-shadow-sm"
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
    <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-white/[0.04] flex items-center justify-center text-[10px] font-bold text-muted-foreground/75 shadow-2xs font-mono">
      {initials}
    </div>
  );
}

function FormPill({ outcome }: { outcome: "W" | "D" | "L" }) {
  const colors = {
    W: "text-emerald-400 border-emerald-500/15 bg-emerald-500/5",
    D: "text-zinc-400 border-white/[0.06] bg-white/[0.02]",
    L: "text-rose-400 border-rose-500/15 bg-rose-500/5",
  };
  return (
    <span className={`inline-flex items-center justify-center w-5.5 h-5.5 rounded-lg text-[9px] font-extrabold tracking-tight font-mono border ${colors[outcome]}`}>
      {outcome}
    </span>
  );
}

function PowerBalance({ homeVal, awayVal }: { homeVal: number; awayVal: number }) {
  const total = homeVal + awayVal || 1;
  const homePct = Math.round((homeVal / total) * 100);
  const awayPct = 100 - homePct;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-[9px] font-bold text-muted-foreground/60 font-mono tracking-widest uppercase">
        <span className="text-emerald-400/90">{homePct}%</span>
        <span>INDEX KEKUATAN</span>
        <span className="text-zinc-400/90">{awayPct}%</span>
      </div>
      <div className="h-1 w-full bg-zinc-950 border border-white/[0.02] rounded-full overflow-hidden flex">
        <div
          className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-l-full transition-all duration-700"
          style={{ width: `${homePct}%` }}
        />
        <div
          className="h-full bg-zinc-800 transition-all duration-700"
          style={{ width: `${awayPct}%` }}
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
  const [showRoster, setShowRoster] = useState(false);

  const groupRoster = (players: RosterPlayer[] | undefined) => {
    if (!players) return { GK: [], DEF: [], MID: [], FWD: [] };
    const gk: RosterPlayer[] = [];
    const def: RosterPlayer[] = [];
    const mid: RosterPlayer[] = [];
    const fwd: RosterPlayer[] = [];
    players.forEach((p) => {
      const pos = p.position.toLowerCase();
      if (pos.includes("goalkeeper") || pos.includes("kiper")) {
        gk.push(p);
      } else if (pos.includes("defender") || pos.includes("back") || pos.includes("bek")) {
        def.push(p);
      } else if (pos.includes("midfielder") || pos.includes("gelandang")) {
        mid.push(p);
      } else {
        fwd.push(p);
      }
    });
    return { GK: gk, DEF: def, MID: mid, FWD: fwd };
  };

  const homeGroups = groupRoster(homeTeam.roster);
  const awayGroups = groupRoster(awayTeam.roster);
  const hasRoster = (homeTeam.roster && homeTeam.roster.length > 0) || (awayTeam.roster && awayTeam.roster.length > 0);

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.04] bg-zinc-900/10 backdrop-blur-md p-5 shadow-xs transition-all duration-300 hover:border-white/[0.08] max-w-md md:max-w-full space-y-5">
      
      {/* Top Header Row */}
      <div className="flex items-center justify-between text-[8px] font-bold text-muted-foreground/50 uppercase tracking-widest font-mono">
        <span>STATISTIK ENGINE &bull; PREDIKSI</span>
        {matchDate && <span>{matchDate}</span>}
      </div>

      {/* Main Scoreboard Layout */}
      <div className="flex items-center gap-4 py-1">
        {/* Home Team */}
        <div className="flex-1 flex flex-col items-center gap-2 text-center min-w-0">
          <TeamBadge name={homeTeam.name} badge={homeTeam.badge} />
          <div className="w-full">
            <p className="font-bold text-xs text-foreground/90 leading-tight truncate">{homeTeam.name}</p>
            <p className="text-[8px] text-muted-foreground/45 mt-0.5 font-bold truncate uppercase tracking-widest font-mono">{homeTeam.league || "Home Team"}</p>
          </div>
        </div>

        {/* Score Predictor */}
        <div className="flex flex-col items-center gap-0.5 px-4 py-2 rounded-xl bg-zinc-950/60 border border-white/[0.03] flex-shrink-0 min-w-[90px] shadow-3xs">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl font-extrabold font-mono text-emerald-400 leading-none tracking-tighter">
              {prediction.home_score}
            </span>
            <span className="text-muted-foreground/20 font-bold text-base leading-none">-</span>
            <span className="text-2xl font-extrabold font-mono text-foreground/80 leading-none tracking-tighter">
              {prediction.away_score}
            </span>
          </div>
          <span className="text-[6px] uppercase tracking-widest text-muted-foreground/40 font-extrabold font-mono mt-1">
            PREDIKSI SKOR
          </span>
        </div>

        {/* Away Team */}
        <div className="flex-1 flex flex-col items-center gap-2 text-center min-w-0">
          <TeamBadge name={awayTeam.name} badge={awayTeam.badge} />
          <div className="w-full">
            <p className="font-bold text-xs text-foreground/90 leading-tight truncate">{awayTeam.name}</p>
            <p className="text-[8px] text-muted-foreground/45 mt-0.5 font-bold truncate uppercase tracking-widest font-mono">{awayTeam.league || "Away Team"}</p>
          </div>
        </div>
      </div>

      {/* Power Balance Bar */}
      <div className="border-t border-white/[0.02] pt-3.5">
        <PowerBalance homeVal={homeTeam.strength} awayVal={awayTeam.strength} />
      </div>

      {/* Form Grid */}
      {(homeTeam.last_results.length > 0 || awayTeam.last_results.length > 0) && (
        <div className="grid grid-cols-2 gap-4 border-t border-white/[0.02] pt-3.5">
          <div className="space-y-1.5">
            <p className="text-[8px] uppercase tracking-widest text-muted-foreground/40 font-bold font-mono">
              FORM Tuan Rumah
            </p>
            <div className="flex gap-1">
              {homeTeam.last_results.slice(0, 5).map((r, i) => (
                <FormPill key={i} outcome={r.outcome} />
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <p className="text-[8px] uppercase tracking-widest text-muted-foreground/40 font-bold font-mono">
              FORM Tamu
            </p>
            <div className="flex gap-1">
              {awayTeam.last_results.slice(0, 5).map((r, i) => (
                <FormPill key={i} outcome={r.outcome} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Roster / Skuad Pemain */}
      {hasRoster && (
        <div className="border-t border-white/[0.02] pt-3.5 space-y-2.5">
          <button
            onClick={() => setShowRoster(!showRoster)}
            className="flex items-center justify-between w-full text-left text-[8px] font-bold text-muted-foreground/45 hover:text-foreground/90 uppercase tracking-widest font-mono cursor-pointer"
          >
            <div className="flex items-center gap-1.5">
              <Users size={10} className="text-zinc-500" />
              <span>SKUAD UTAMA / ROSTER</span>
            </div>
            <span className="text-[7px] bg-zinc-900 border border-white/[0.04] px-1.5 py-0.5 rounded font-mono font-bold hover:bg-zinc-800 transition-all">
              {showRoster ? "TUTUP" : "LIHAT SKUAD"}
            </span>
          </button>
          
          {showRoster && (
            <div className="grid grid-cols-2 gap-4 pt-1.5 animate-fade-in text-[10px]">
              {/* Home Team Roster */}
              <div className="space-y-2.5 border-r border-white/[0.02] pr-2">
                <p className="font-bold text-[9px] text-emerald-400 truncate uppercase font-mono">{homeTeam.name}</p>
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 scrollbar-thin">
                  {Object.entries(homeGroups).map(([pos, players]) => (
                    players.length > 0 && (
                      <div key={pos} className="space-y-1">
                        <p className="text-[7.5px] font-bold text-muted-foreground/40 font-mono tracking-widest uppercase">{pos}</p>
                        <div className="space-y-0.5">
                          {players.slice(0, 8).map((p, idx) => (
                            <div key={idx} className="flex justify-between items-center py-0.5 hover:bg-white/[0.01] px-1 rounded transition-colors text-foreground/85">
                              <span className="truncate max-w-[110px] font-medium">{p.name}</span>
                              <span className="text-muted-foreground/40 font-mono text-[8px]">{p.jersey ? `#${p.jersey}` : ""}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  ))}
                </div>
              </div>
              
              {/* Away Team Roster */}
              <div className="space-y-2.5 pl-2">
                <p className="font-bold text-[9px] text-zinc-400 truncate uppercase font-mono">{awayTeam.name}</p>
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 scrollbar-thin">
                  {Object.entries(awayGroups).map(([pos, players]) => (
                    players.length > 0 && (
                      <div key={pos} className="space-y-1">
                        <p className="text-[7.5px] font-bold text-muted-foreground/40 font-mono tracking-widest uppercase">{pos}</p>
                        <div className="space-y-0.5">
                          {players.slice(0, 8).map((p, idx) => (
                            <div key={idx} className="flex justify-between items-center py-0.5 hover:bg-white/[0.01] px-1 rounded transition-colors text-foreground/85">
                              <span className="truncate max-w-[110px] font-medium">{p.name}</span>
                              <span className="text-muted-foreground/40 font-mono text-[8px]">{p.jersey ? `#${p.jersey}` : ""}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Head-to-Head Matches */}
      {h2h.length > 0 && (
        <div className="border-t border-white/[0.02] pt-3.5 space-y-2.5">
          <p className="text-[8px] uppercase tracking-widest text-muted-foreground/40 font-bold font-mono">
            PERTEMUAN TERAKHIR (H2H)
          </p>
          <div className="overflow-hidden rounded-xl border border-white/[0.03] bg-zinc-950/20">
            <table className="w-full border-collapse text-left text-[10px]">
              <tbody>
                {h2h.slice(0, 3).map((match, i) => (
                  <tr key={i} className="border-b border-white/[0.01] last:border-0 hover:bg-white/[0.01] transition-colors">
                    <td className="py-2 px-3 text-muted-foreground/35 font-mono text-[8px]">{match.date}</td>
                    <td className="py-2 px-1 text-right font-semibold text-foreground/75 truncate max-w-[85px]">{match.home}</td>
                    <td className="py-2 px-2 text-center font-mono text-emerald-400 font-bold bg-emerald-500/[0.01] w-12 border-x border-white/[0.01]">
                      {match.score}
                    </td>
                    <td className="py-2 px-1 text-left font-semibold text-foreground/75 truncate max-w-[85px]">{match.away}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer / Data Source */}
      <div className="flex justify-between items-center border-t border-white/[0.02] pt-3 text-[7px] text-muted-foreground/35 font-bold uppercase tracking-widest font-mono">
        <span>ESPN PUBLIC API &bull; REALTIME DATA</span>
        <span>BOLAMISTIS ANALYTICS</span>
      </div>

    </div>
  );
}
