import requests
from typing import Optional

HEADERS = {"User-Agent": "BolaMistisAI/1.0 (football predictor)"}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUES = [
    ("eng.1", "English Premier League"),
    ("esp.1", "La Liga"),
    ("ger.1", "Bundesliga"),
    ("ita.1", "Serie A"),
    ("fra.1", "Ligue 1"),
    ("por.1", "Primeira Liga"),
    ("ned.1", "Eredivisie"),
    ("eng.2", "Championship"),
    ("mex.1", "Liga MX"),
    ("bra.1", "Brasileirao"),
    ("arg.1", "Liga Profesional"),
    ("usa.1", "MLS"),
]

NAME_ALIASES: dict[str, str] = {
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "manchester united": "Manchester United",
    "man city": "Manchester City",
    "manchester city": "Manchester City",
    "spurs": "Tottenham Hotspur",
    "tottenham": "Tottenham Hotspur",
    "psg": "Paris Saint-Germain",
    "paris saint-germain": "Paris Saint-Germain",
    "inter milan": "Internazionale",
    "inter": "Internazionale",
    "ac milan": "AC Milan",
    "milan": "AC Milan",
    "atletico": "Atletico Madrid",
    "atletico madrid": "Atletico Madrid",
    "bayern": "Bayern Munich",
    "dortmund": "Borussia Dortmund",
    "bvb": "Borussia Dortmund",
    "newcastle": "Newcastle United",
    "west ham": "West Ham United",
    "leicester": "Leicester City",
    "wolves": "Wolverhampton Wanderers",
    "brighton": "Brighton & Hove Albion",
    "bournemouth": "AFC Bournemouth",
    "nott'm forest": "Nottingham Forest",
    "nottingham forest": "Nottingham Forest",
    "real": "Real Madrid",
    "barca": "FC Barcelona",
    "barcelona": "FC Barcelona",
}

_TEAM_INDEX: dict[str, dict] = {}
_LEAGUE_INDEX: dict[str, list[dict]] = {}


def _build_index(force: bool = False) -> None:
    global _TEAM_INDEX, _LEAGUE_INDEX
    if _TEAM_INDEX and not force:
        return
    for slug, league_name in LEAGUES:
        try:
            url = f"{ESPN_BASE}/{slug}/teams"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            data = resp.json()
            teams_in_league = []
            for sport in data.get("sports", []):
                for league in sport.get("leagues", []):
                    for t in league.get("teams", []):
                        team = t.get("team", {})
                        name = team.get("displayName", "")
                        tid = team.get("id", "")
                        logos = team.get("logos", [])
                        logo = logos[0].get("href", "") if logos else ""
                        entry = {
                            "id": tid,
                            "name": name,
                            "logo": logo,
                            "league": league_name,
                            "league_slug": slug,
                        }
                        if name and name not in _TEAM_INDEX:
                            _TEAM_INDEX[name] = entry
                        teams_in_league.append(entry)
            _LEAGUE_INDEX[slug] = teams_in_league
        except Exception:
            continue


def _resolve_name(raw: str) -> str:
    key = raw.lower().strip()
    if key in NAME_ALIASES:
        return NAME_ALIASES[key]
    for k, v in NAME_ALIASES.items():
        if key in k or k in key:
            return v
    return raw.strip().title()


def _find_team(name: str) -> Optional[dict]:
    _build_index()
    canonical = _resolve_name(name)
    if canonical in _TEAM_INDEX:
        return _TEAM_INDEX[canonical]
    name_lower = canonical.lower()
    for tname, entry in _TEAM_INDEX.items():
        if name_lower == tname.lower():
            return entry
    for tname, entry in _TEAM_INDEX.items():
        if name_lower in tname.lower() or tname.lower() in name_lower:
            return entry
    for word in canonical.split():
        if len(word) >= 4:
            for tname, entry in _TEAM_INDEX.items():
                if word.lower() in tname.lower():
                    return entry
    return None


def _get_last_results(team_id: str, team_name: str, league_slug: str, limit: int = 5) -> list[dict]:
    results = []
    try:
        url = f"{ESPN_BASE}/{league_slug}/teams/{team_id}/schedule"
        resp = requests.get(url, params={"limit": 40}, headers=HEADERS, timeout=8)
        events = resp.json().get("events", [])
        for event in reversed(events):
            comps = event.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                continue
            competitors = comp.get("competitors", [])
            home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
            home_name = home_comp.get("team", {}).get("displayName", "")
            away_name = away_comp.get("team", {}).get("displayName", "")

            home_score_raw = home_comp.get("score", {})
            away_score_raw = away_comp.get("score", {})
            if isinstance(home_score_raw, dict):
                home_score = int(home_score_raw.get("value", 0) or 0)
            else:
                home_score = int(home_score_raw or 0)
            if isinstance(away_score_raw, dict):
                away_score = int(away_score_raw.get("value", 0) or 0)
            else:
                away_score = int(away_score_raw or 0)

            is_home = home_name.lower() == team_name.lower() or team_id == home_comp.get("team", {}).get("id", "")
            if is_home:
                ts, os_, opponent = home_score, away_score, away_name
            else:
                ts, os_, opponent = away_score, home_score, home_name

            if ts > os_:
                outcome = "W"
            elif ts == os_:
                outcome = "D"
            else:
                outcome = "L"

            results.append({
                "date": event.get("date", "")[:10],
                "opponent": opponent,
                "score": f"{ts}-{os_}",
                "outcome": outcome,
                "venue": "home" if is_home else "away",
            })
            if len(results) >= limit:
                break
    except Exception:
        pass
    return results


def _get_h2h(team1: dict, team2: dict) -> list[dict]:
    h2h = []
    try:
        slug = team1["league_slug"]
        url = f"{ESPN_BASE}/{slug}/teams/{team1['id']}/schedule"
        resp = requests.get(url, params={"limit": 40}, headers=HEADERS, timeout=8)
        events = resp.json().get("events", [])
        t2_name = team2["name"].lower()
        for event in reversed(events):
            comps = event.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                continue
            competitors = comp.get("competitors", [])
            names = [c.get("team", {}).get("displayName", "").lower() for c in competitors]
            if any(t2_name in n or n in t2_name for n in names):
                home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})

                hs = home_comp.get("score", {})
                as_ = away_comp.get("score", {})
                hs = int(hs.get("value", 0) if isinstance(hs, dict) else (hs or 0))
                as_ = int(as_.get("value", 0) if isinstance(as_, dict) else (as_ or 0))

                h2h.append({
                    "date": event.get("date", "")[:10],
                    "home": home_comp.get("team", {}).get("displayName", ""),
                    "away": away_comp.get("team", {}).get("displayName", ""),
                    "score": f"{hs}-{as_}",
                })
                if len(h2h) >= 5:
                    break
    except Exception:
        pass
    return h2h


def calculate_strength(results: list[dict]) -> int:
    strength = 0
    for r in results:
        if r["outcome"] == "W":
            strength += 3
        elif r["outcome"] == "D":
            strength += 1
    return strength


def predict_score(strength_a: int, strength_b: int) -> tuple[int, int]:
    diff = strength_a - strength_b
    if diff >= 9:
        return 3, 0
    elif diff >= 6:
        return 3, 1
    elif diff >= 3:
        return 2, 1
    elif diff >= 1:
        return 1, 0
    elif diff == 0:
        return 1, 1
    elif diff >= -2:
        return 0, 1
    elif diff >= -5:
        return 1, 2
    elif diff >= -8:
        return 1, 3
    else:
        return 0, 3


def fetch_team_data(team_name: str) -> dict:
    team_info = _find_team(team_name)
    if not team_info:
        return {
            "found": False,
            "name": _resolve_name(team_name),
            "last_results": [],
            "strength": 0,
        }
    last_results = _get_last_results(
        team_info["id"], team_info["name"], team_info["league_slug"]
    )
    strength = calculate_strength(last_results)
    return {
        "found": True,
        "name": team_info["name"],
        "id": team_info["id"],
        "league": team_info["league"],
        "league_slug": team_info["league_slug"],
        "badge": team_info["logo"],
        "last_results": last_results,
        "strength": strength,
    }


def get_h2h(team1_data: dict, team2_data: dict) -> list[dict]:
    if not team1_data.get("found") or not team2_data.get("found"):
        return []
    return _get_h2h(team1_data, team2_data)
