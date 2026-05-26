import requests
from typing import Optional
import os
import json
import re

CACHE_PATH = os.path.join(os.path.dirname(__file__), "team_index_cache.json")

def safe_int_score(score_raw) -> int:
    """Safely parse score from ESPN API payload to prevent ValueError."""
    if isinstance(score_raw, dict):
        val = score_raw.get("value")
        if val is None:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                # Try to extract numbers
                digits = "".join(c for c in str(val) if c.isdigit())
                return int(digits) if digits else 0
    else:
        if score_raw is None:
            return 0
        score_str = str(score_raw).strip()
        try:
            return int(score_str)
        except (ValueError, TypeError):
            try:
                return int(float(score_str))
            except (ValueError, TypeError):
                match = re.search(r'\d+', score_str)
                if match:
                    return int(match.group())
                return 0

HEADERS = {"User-Agent": "KyonayrPlayground/1.0 (football predictor)"}

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

    # Try loading from cache file
    if not force and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
                _TEAM_INDEX = cached.get("team_index", {})
                _LEAGUE_INDEX = cached.get("league_index", {})
                if _TEAM_INDEX:
                    return
        except Exception:
            pass

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

    # Save to cache file
    if _TEAM_INDEX:
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({"team_index": _TEAM_INDEX, "league_index": _LEAGUE_INDEX}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass



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
                home_score = safe_int_score(home_score_raw)
                away_score = safe_int_score(away_score_raw)


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
                    hs = safe_int_score(hs)
                    as_ = safe_int_score(as_)

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
            "home_avg_scored": 1.2,
            "home_avg_conceded": 1.2,
            "away_avg_scored": 1.2,
            "away_avg_conceded": 1.2,
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
    home_scored = 0
    home_conceded = 0
    home_count = 0
    away_scored = 0
    away_conceded = 0
    away_count = 0

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

        if r.get("venue") == "home":
            home_scored += scored
            home_conceded += conceded
            home_count += 1
        elif r.get("venue") == "away":
            away_scored += scored
            away_conceded += conceded
            away_count += 1

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

    home_avg_scored = home_scored / home_count if home_count > 0 else avg_scored
    home_avg_conceded = home_conceded / home_count if home_count > 0 else avg_conceded
    away_avg_scored = away_scored / away_count if away_count > 0 else avg_scored
    away_avg_conceded = away_conceded / away_count if away_count > 0 else avg_conceded

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
        "home_avg_scored": round(home_avg_scored, 2),
        "home_avg_conceded": round(home_avg_conceded, 2),
        "away_avg_scored": round(away_avg_scored, 2),
        "away_avg_conceded": round(away_avg_conceded, 2),
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "clean_sheets": clean_sheets,
        "failed_to_score": failed_to_score,
        "form_label": form_label,
        "form_icons": form_icons,
        "goal_diff": total_scored - total_conceded,
    }


def poisson_probability(lmbda: float, k: int) -> float:
    """Calculates Poisson probability for k events with mean lmbda."""
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    import math
    try:
        return (lmbda ** k * math.exp(-lmbda)) / math.factorial(k)
    except Exception:
        return 0.0


def find_most_probable_score(home_xg: float, away_xg: float) -> tuple[int, int]:
    """Calculates the 6x6 score probability matrix and returns the mode scoreline."""
    best_score = (0, 0)
    max_prob = -1.0
    for h in range(6):
        for a in range(6):
            prob = poisson_probability(home_xg, h) * poisson_probability(away_xg, a)
            if prob > max_prob:
                max_prob = prob
                best_score = (h, a)
    return best_score


def predict_score(home_stats: dict, away_stats: dict, home_advantage: bool = True, h2h: list[dict] = None) -> tuple[int, int]:
    """
    Genius expected-goals model using Poisson probability modes,
    venue-specific stats (home/away splits), and H2H goal rate blending.
    """
    LEAGUE_AVG = 1.35  # typical goals per team per game across top leagues
    HA = 1.15 if home_advantage else 1.0
    DEF_FLOOR = 0.30
    ATK_FLOOR = 0.40

    # 1. Use venue specific averages if available (blend 60% overall, 40% venue-specific)
    h_scored_base = home_stats.get("home_avg_scored", home_stats.get("avg_scored", LEAGUE_AVG))
    h_conceded_base = home_stats.get("home_avg_conceded", home_stats.get("avg_conceded", LEAGUE_AVG))
    a_scored_base = away_stats.get("away_avg_scored", away_stats.get("avg_scored", LEAGUE_AVG))
    a_conceded_base = away_stats.get("away_avg_conceded", away_stats.get("avg_conceded", LEAGUE_AVG))

    ha_scored = max(0.6 * home_stats.get("avg_scored", LEAGUE_AVG) + 0.4 * h_scored_base, ATK_FLOOR)
    ha_conceded = max(0.6 * home_stats.get("avg_conceded", LEAGUE_AVG) + 0.4 * h_conceded_base, DEF_FLOOR)
    aa_scored = max(0.6 * away_stats.get("avg_scored", LEAGUE_AVG) + 0.4 * a_scored_base, ATK_FLOOR)
    aa_conceded = max(0.6 * away_stats.get("avg_conceded", LEAGUE_AVG) + 0.4 * a_conceded_base, DEF_FLOOR)

    # 2. Dixon-Coles-inspired base xG
    home_xg = (ha_scored / LEAGUE_AVG) * (aa_conceded / LEAGUE_AVG) * LEAGUE_AVG * HA
    away_xg = (aa_scored / LEAGUE_AVG) * (ha_conceded / LEAGUE_AVG) * LEAGUE_AVG / HA

    # 3. Blending H2H direct matchup history (20% weight)
    if h2h:
        h2h_home_goals = 0
        h2h_away_goals = 0
        valid_matches = 0
        home_name = home_stats.get("name", "").lower()
        away_name = away_stats.get("name", "").lower()
        for m in h2h:
            try:
                parts = m["score"].split("-")
                hs = int(parts[0])
                as_ = int(parts[1])
                m_home = m["home"].lower()
                m_away = m["away"].lower()
                
                # Check match direction
                if home_name and (home_name in m_home or m_home in home_name):
                    h2h_home_goals += hs
                    h2h_away_goals += as_
                    valid_matches += 1
                elif home_name and (home_name in m_away or m_away in home_name):
                    h2h_home_goals += as_
                    h2h_away_goals += hs
                    valid_matches += 1
            except Exception:
                continue
        if valid_matches > 0:
            avg_h2h_home = h2h_home_goals / valid_matches
            avg_h2h_away = h2h_away_goals / valid_matches
            home_xg = 0.8 * home_xg + 0.2 * avg_h2h_home
            away_xg = 0.8 * away_xg + 0.2 * avg_h2h_away

    # 4. Win streak momentum bonus
    if home_stats.get("win_streak", 0) >= 3:
        home_xg *= 1.12
    if away_stats.get("win_streak", 0) >= 3:
        away_xg *= 1.12

    # 5. Clean sheet ability
    if home_stats.get("clean_sheets", 0) >= 3:
        away_xg *= 0.88
    if away_stats.get("clean_sheets", 0) >= 3:
        home_xg *= 0.88

    # 6. Weighted points strength anchor
    home_wp = home_stats.get("weighted_points", 10.0)
    away_wp = away_stats.get("weighted_points", 10.0)
    total_wp = home_wp + away_wp or 1
    wp_ratio = (home_wp - away_wp) / total_wp
    home_xg += wp_ratio * 0.65
    away_xg -= wp_ratio * 0.65

    # 7. Clamp to [0, 5]
    home_xg = max(0.0, min(5.0, home_xg))
    away_xg = max(0.0, min(5.0, away_xg))

    # 8. Poisson distribution mode simulation
    predicted_home, predicted_away = find_most_probable_score(home_xg, away_xg)

    # 9. Tiebreaker
    if predicted_home == 0 and predicted_away == 0:
        if home_wp > away_wp + 2.5:
            predicted_home = 1
        elif away_wp > home_wp + 2.5:
            predicted_away = 1

    return predicted_home, predicted_away


def fetch_team_data(team_name: str) -> dict:
    team_info = _find_team(team_name)
    if not team_info:
        fallback_name = _resolve_name(team_name)
        return {
            "found": False,
            "name": fallback_name,
            "last_results": [],
            "strength": 0,
            "stats": {**calculate_team_stats([]), "name": fallback_name},
        }
    last_results = _get_last_results(
        team_info["id"], team_info["name"], team_info["league_slug"]
    )
    strength = calculate_strength(last_results)
    stats = calculate_team_stats(last_results)
    stats["name"] = team_info["name"]
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
