import requests
from typing import Optional

HEADERS = {"User-Agent": "BolaMistisAI/1.0 (football predictor)"}

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUES = [
    # Club leagues
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
    # International / national team competitions
    ("fifa.world", "FIFA World Cup"),
    ("concacaf.nations.a", "CONCACAF Nations League"),
    ("concacaf.gold", "CONCACAF Gold Cup"),
    ("conmebol.america", "Copa America"),
    ("uefa.euro", "UEFA Euro"),
    ("uefa.nations.a", "UEFA Nations League A"),
    ("fifa.friendly", "International Friendly"),
]

NAME_ALIASES: dict[str, str] = {
    # Club aliases
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
    # Indonesian national team name aliases
    "meksiko": "Mexico",
    "mexico": "Mexico",
    "ceko": "Czech Republic",
    "republik ceko": "Czech Republic",
    "czech": "Czech Republic",
    "inggris": "England",
    "jerman": "Germany",
    "prancis": "France",
    "belanda": "Netherlands",
    "nederland": "Netherlands",
    "hollanda": "Netherlands",
    "brasil": "Brazil",
    "brazil": "Brazil",
    "spanyol": "Spain",
    "portugis": "Portugal",
    "portugal": "Portugal",
    "italia": "Italy",
    "belgia": "Belgium",
    "kroasia": "Croatia",
    "polandia": "Poland",
    "swiss": "Switzerland",
    "ukraina": "Ukraine",
    "turki": "Turkey",
    "maroko": "Morocco",
    "jepang": "Japan",
    "korea selatan": "South Korea",
    "korea": "South Korea",
    "australia": "Australia",
    "ekuador": "Ecuador",
    "kolombia": "Colombia",
    "uruguay": "Uruguay",
    "chili": "Chile",
    "peru": "Peru",
    "ghana": "Ghana",
    "nigeria": "Nigeria",
    "kamerun": "Cameroon",
    "mesir": "Egypt",
    "aljazair": "Algeria",
    "arab saudi": "Saudi Arabia",
    "as": "United States",
    "usa": "United States",
    "amerika serikat": "United States",
    "kanada": "Canada",
    "kosta rika": "Costa Rica",
    "panama": "Panama",
    "jamaika": "Jamaica",
    "rusia": "Russia",
    "swedia": "Sweden",
    "denmark": "Denmark",
    "norwegia": "Norway",
    "finlandia": "Finland",
    "skotlandia": "Scotland",
    "hungaria": "Hungary",
    "rumania": "Romania",
    "serbia": "Serbia",
    "yunani": "Greece",
    "austria": "Austria",
    "slowakia": "Slovakia",
    "islandia": "Iceland",
    "indonesia": "Indonesia",
    "thailand": "Thailand",
    "vietnam": "Vietnam",
    "malaysia": "Malaysia",
    "filipina": "Philippines",
    "tiongkok": "China",
    "kamerun": "Cameroon",
    "senegal": "Senegal",
    "venezuela": "Venezuela",
    "paraguay": "Paraguay",
    "bolivia": "Bolivia",
    "iran": "Iran",
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
            if resp.status_code != 200:
                continue
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
                        if not logo:
                            logo = f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png"
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


def _search_espn(query: str) -> Optional[dict]:
    """Search ESPN for a team by name — fallback when not in local index."""
    try:
        url = "https://site.api.espn.com/apis/common/v3/search"
        resp = requests.get(
            url,
            params={"query": query, "limit": 5, "sport": "soccer", "type": "team"},
            headers=HEADERS,
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        results = resp.json().get("results", [])
        for section in results:
            for item in section.get("contents", []):
                if item.get("type") != "team":
                    continue
                tid = item.get("id", "")
                name = item.get("displayName", item.get("name", ""))
                logo = item.get("logos", [{}])[0].get("href", "")
                if not logo and tid:
                    logo = f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png"
                # Try to find a league slug for this team
                league_slug = _guess_league_slug(item)
                return {
                    "id": tid,
                    "name": name,
                    "logo": logo,
                    "league": item.get("league", {}).get("displayName", "International"),
                    "league_slug": league_slug,
                }
    except Exception:
        pass
    return None


def _guess_league_slug(item: dict) -> str:
    """Guess ESPN league slug from search result metadata."""
    league = item.get("league", {})
    slug = league.get("slug", "")
    if slug:
        return slug
    name = league.get("displayName", "").lower()
    if "premier" in name:
        return "eng.1"
    if "la liga" in name:
        return "esp.1"
    if "bundesliga" in name:
        return "ger.1"
    if "serie a" in name:
        return "ita.1"
    if "ligue 1" in name:
        return "fra.1"
    if "world cup" in name:
        return "fifa.world"
    if "concacaf" in name:
        return "concacaf.nations.a"
    if "copa" in name or "america" in name:
        return "conmebol.america"
    if "euro" in name:
        return "uefa.euro"
    if "nations" in name:
        return "uefa.nations.a"
    return "fifa.friendly"


def _resolve_name(raw: str) -> str:
    key = raw.lower().strip()
    if key in NAME_ALIASES:
        return NAME_ALIASES[key]
    for k, v in NAME_ALIASES.items():
        if key == k:
            return v
    return raw.strip().title()


def _find_team(name: str) -> Optional[dict]:
    _build_index()
    canonical = _resolve_name(name)

    # Exact match
    if canonical in _TEAM_INDEX:
        return _TEAM_INDEX[canonical]

    name_lower = canonical.lower()

    # Case-insensitive exact
    for tname, entry in _TEAM_INDEX.items():
        if name_lower == tname.lower():
            return entry

    # Substring match
    for tname, entry in _TEAM_INDEX.items():
        if name_lower in tname.lower() or tname.lower() in name_lower:
            return entry

    # Word match (min 4 chars)
    for word in canonical.split():
        if len(word) >= 4:
            for tname, entry in _TEAM_INDEX.items():
                if word.lower() in tname.lower():
                    return entry

    # ESPN search fallback
    found = _search_espn(canonical)
    if found:
        _TEAM_INDEX[found["name"]] = found
        return found

    # Try raw name via ESPN search
    found = _search_espn(name)
    if found:
        _TEAM_INDEX[found["name"]] = found
        return found

    return None


def _get_last_results(team_id: str, team_name: str, league_slug: str, limit: int = 5) -> list[dict]:
    results = []
    slugs_to_try = [league_slug]
    # For national teams, also try alternative competition slugs
    if league_slug in ("fifa.world", "concacaf.nations.a", "concacaf.gold",
                       "conmebol.america", "uefa.euro", "uefa.nations.a", "fifa.friendly"):
        slugs_to_try = [
            "fifa.friendly", "concacaf.nations.a", "uefa.nations.a",
            "conmebol.america", "concacaf.gold", "uefa.euro", "fifa.world",
        ]

    for slug in slugs_to_try:
        if len(results) >= limit:
            break
        try:
            url = f"{ESPN_BASE}/{slug}/teams/{team_id}/schedule"
            resp = requests.get(url, params={"limit": 40}, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                continue
            events = resp.json().get("events", [])
            for event in reversed(events):
                if len(results) >= limit:
                    break
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

                is_home = (
                    home_name.lower() == team_name.lower()
                    or team_id == home_comp.get("team", {}).get("id", "")
                )
                if is_home:
                    ts, os_, opponent = home_score, away_score, away_name
                else:
                    ts, os_, opponent = away_score, home_score, home_name

                if not opponent:
                    continue

                outcome = "W" if ts > os_ else ("D" if ts == os_ else "L")
                results.append({
                    "date": event.get("date", "")[:10],
                    "opponent": opponent,
                    "score": f"{ts}-{os_}",
                    "outcome": outcome,
                    "venue": "home" if is_home else "away",
                })
        except Exception:
            continue

    return results[:limit]


def _get_h2h(team1: dict, team2: dict) -> list[dict]:
    h2h = []
    slugs_to_try = [team1["league_slug"]]
    if team1["league_slug"] in ("fifa.world", "concacaf.nations.a", "concacaf.gold",
                                "conmebol.america", "uefa.euro", "uefa.nations.a", "fifa.friendly"):
        slugs_to_try = [
            "fifa.friendly", "concacaf.nations.a", "uefa.nations.a",
            "conmebol.america", "concacaf.gold", "uefa.euro",
        ]

    t2_name = team2["name"].lower()
    for slug in slugs_to_try:
        if len(h2h) >= 5:
            break
        try:
            url = f"{ESPN_BASE}/{slug}/teams/{team1['id']}/schedule"
            resp = requests.get(url, params={"limit": 40}, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                continue
            events = resp.json().get("events", [])
            for event in reversed(events):
                if len(h2h) >= 5:
                    break
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
        except Exception:
            continue

    return h2h


def calculate_strength(results: list[dict]) -> int:
    """Legacy simple strength — kept for compatibility."""
    strength = 0
    for r in results:
        if r["outcome"] == "W":
            strength += 3
        elif r["outcome"] == "D":
            strength += 1
    return strength


def calculate_team_stats(results: list[dict]) -> dict:
    """Rich stats used by the smart prediction engine."""
    if not results:
        return {
            "weighted_points": 0.0,
            "avg_scored": 1.2,
            "avg_conceded": 1.2,
            "win_streak": 0,
            "loss_streak": 0,
            "clean_sheets": 0,
            "failed_to_score": 0,
            "form_label": "Tidak ada data",
            "form_icons": [],
            "goal_diff": 0,
        }

    position_weights = [3.0, 2.5, 2.0, 1.5, 1.0]
    total_scored = 0
    total_conceded = 0
    weighted_pts = 0.0
    total_weight = 0.0
    win_streak = 0
    loss_streak = 0
    clean_sheets = 0
    failed_to_score = 0
    form_icons = []

    icon_map = {"W": "W", "D": "D", "L": "L"}

    for i, r in enumerate(results):
        w = position_weights[i] if i < len(position_weights) else 1.0
        try:
            parts = r["score"].split("-")
            scored = int(parts[0])
            conceded = int(parts[1])
        except Exception:
            scored, conceded = 0, 0

        total_scored += scored
        total_conceded += conceded
        if scored == 0:
            failed_to_score += 1
        if conceded == 0:
            clean_sheets += 1

        form_icons.append(icon_map.get(r["outcome"], "?"))

        if r["outcome"] == "W":
            weighted_pts += 3 * w
            if i == win_streak:
                win_streak += 1
        elif r["outcome"] == "D":
            weighted_pts += 1 * w
        else:
            if i == loss_streak:
                loss_streak += 1

        total_weight += w

    n = len(results)
    avg_scored = total_scored / n
    avg_conceded = total_conceded / n

    recent = results[:3]
    recent_pts = sum(
        3 if r["outcome"] == "W" else 1 if r["outcome"] == "D" else 0
        for r in recent
    )
    if recent_pts >= 7:
        form_label = "Forma Luar Biasa"
    elif recent_pts >= 5:
        form_label = "Forma Bagus"
    elif recent_pts >= 3:
        form_label = "Forma Sedang"
    elif recent_pts >= 1:
        form_label = "Forma Kurang Baik"
    else:
        form_label = "Forma Sangat Buruk"

    return {
        "weighted_points": round(weighted_pts, 1),
        "avg_scored": round(avg_scored, 2),
        "avg_conceded": round(avg_conceded, 2),
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "clean_sheets": clean_sheets,
        "failed_to_score": failed_to_score,
        "form_label": form_label,
        "form_icons": form_icons,
        "goal_diff": total_scored - total_conceded,
    }


def predict_score(home_stats: dict, away_stats: dict, home_advantage: bool = True) -> tuple[int, int]:
    """
    Smart expected-goals model.
    Uses attack/defense rates with home advantage and streak bonus.
    Falls back gracefully if stats are minimal.
    """
    LEAGUE_AVG = 1.35  # typical goals per team per game across top leagues
    HA = 1.15 if home_advantage else 1.0

    ha_scored = home_stats.get("avg_scored", LEAGUE_AVG)
    ha_conceded = home_stats.get("avg_conceded", LEAGUE_AVG)
    aa_scored = away_stats.get("avg_scored", LEAGUE_AVG)
    aa_conceded = away_stats.get("avg_conceded", LEAGUE_AVG)

    # Dixon-Coles-inspired xG:
    # home_xg = (home_attack_rate × away_defense_rate / LEAGUE_AVG²) × LEAGUE_AVG × HA
    home_xg = (ha_scored / LEAGUE_AVG) * (aa_conceded / LEAGUE_AVG) * LEAGUE_AVG * HA
    away_xg = (aa_scored / LEAGUE_AVG) * (ha_conceded / LEAGUE_AVG) * LEAGUE_AVG / HA

    # Win streak momentum bonus
    if home_stats.get("win_streak", 0) >= 3:
        home_xg *= 1.12
    if away_stats.get("win_streak", 0) >= 3:
        away_xg *= 1.12

    # Clean sheet ability — tighten defense
    if home_stats.get("clean_sheets", 0) >= 3:
        away_xg *= 0.85
    if away_stats.get("clean_sheets", 0) >= 3:
        home_xg *= 0.85

    # Weighted points strength adjustment
    home_wp = home_stats.get("weighted_points", 10.0)
    away_wp = away_stats.get("weighted_points", 10.0)
    total_wp = home_wp + away_wp or 1
    wp_ratio = (home_wp - away_wp) / total_wp  # -1 to +1
    home_xg += wp_ratio * 0.3
    away_xg -= wp_ratio * 0.3

    # Clamp to [0, 5]
    home_xg = max(0.0, min(5.0, home_xg))
    away_xg = max(0.0, min(5.0, away_xg))

    return round(home_xg), round(away_xg)


def fetch_team_data(team_name: str) -> dict:
    team_info = _find_team(team_name)
    if not team_info:
        return {
            "found": False,
            "name": _resolve_name(team_name),
            "last_results": [],
            "strength": 0,
            "stats": calculate_team_stats([]),
        }
    last_results = _get_last_results(
        team_info["id"], team_info["name"], team_info["league_slug"]
    )
    strength = calculate_strength(last_results)
    stats = calculate_team_stats(last_results)
    return {
        "found": True,
        "name": team_info["name"],
        "id": team_info["id"],
        "league": team_info["league"],
        "league_slug": team_info["league_slug"],
        "badge": team_info["logo"],
        "last_results": last_results,
        "strength": strength,
        "stats": stats,
    }


def get_h2h(team1_data: dict, team2_data: dict) -> list[dict]:
    if not team1_data.get("found") or not team2_data.get("found"):
        return []
    return _get_h2h(team1_data, team2_data)
