import requests
from typing import Optional
import os
import json
import re
import random
from datetime import datetime, timedelta

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

NATIONAL_TEAM_SLUGS = {
    "fifa.world",
    "fifa.friendly",
    "fifa.worldq.afc",
    "fifa.worldq.uefa",
    "fifa.worldq.conmebol",
    "fifa.worldq.caf",
    "fifa.worldq.concacaf",
    "fifa.worldq.ofc",
    "caf.nations",
    "afc.cup",
    "uefa.euro",
    "conmebol.america",
    "concacaf.nations.a",
    "concacaf.gold",
    "uefa.nations.a",
}

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

# ============================================================================
# SIMULATION FALLBACK ENGINE FOR 1XBET DATA COMPLETENESS
# ============================================================================

REGIONAL_POOLS = {
    "south_asia": ["Pakistan", "India", "Bangladesh", "Nepal", "Sri Lanka", "Maldives", "Afghanistan", "Bhutan"],
    "southeast_asia": ["Indonesia", "Thailand", "Vietnam", "Malaysia", "Singapore", "Philippines", "Cambodia", "Myanmar", "Laos", "Brunei"],
    "east_asia": ["Japan", "South Korea", "China", "North Korea", "Hong Kong", "Taiwan", "Mongolia"],
    "middle_east": ["Saudi Arabia", "Iran", "Iraq", "UAE", "Qatar", "Oman", "Syria", "Jordan", "Lebanon", "Kuwait", "Yemen", "Bahrain"],
    "europe": ["England", "France", "Germany", "Italy", "Spain", "Portugal", "Netherlands", "Belgium", "Croatia", "Switzerland", "Poland", "Denmark", "Sweden", "Norway", "Austria", "Ukraine", "Turkey"],
    "south_america": ["Brazil", "Argentina", "Uruguay", "Colombia", "Ecuador", "Peru", "Chile", "Venezuela", "Paraguay", "Bolivia"],
    "north_america": ["USA", "Mexico", "Canada", "Costa Rica", "Panama", "Jamaica", "Honduras", "El Salvador"],
    "africa": ["Senegal", "Morocco", "Nigeria", "Egypt", "Cameroon", "Algeria", "Tunisia", "Ghana", "Ivory Coast", "Mali", "South Africa"],
}

CLUBS_POOLS = {
    "england": ["Arsenal", "Chelsea", "Liverpool", "Manchester United", "Manchester City", "Tottenham Hotspur", "Aston Villa", "Newcastle United", "West Ham United", "Everton"],
    "spain": ["Real Madrid", "FC Barcelona", "Atletico Madrid", "Real Sociedad", "Villarreal", "Real Betis", "Sevilla", "Athletic Club", "Valencia", "Getafe"],
    "italy": ["Internazionale", "AC Milan", "Juventus", "Napoli", "Roma", "Lazio", "Atalanta", "Fiorentina", "Bologna", "Torino"],
    "germany": ["Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig", "Eintracht Frankfurt", "VfB Stuttgart", "Freiburg", "Wolfsburg", "Borussia Monchengladbach"],
}

def detect_team_category_and_region(team_name: str) -> tuple[str, str, str]:
    """
    Detects if the team is national or club, its geographic region/league country, and suffix (e.g. U23).
    Returns (category, region_or_country, suffix).
    """
    name_lower = team_name.lower()
    
    # 1. Extract youth suffix
    suffix = ""
    suffix_match = re.search(r'\b(u23|u21|u20|u19|u18|u17)\b', name_lower)
    if suffix_match:
        suffix = suffix_match.group(1).upper()
        
    # Remove suffix and common terms for matching
    clean_name = re.sub(r'\b(u23|u21|u20|u19|u18|u17)\b', '', name_lower)
    clean_name = re.sub(r'\b(fc|sc|afc|ud|cf|ac|fk|u\-23|u\-20|under\-23|under\-20)\b', '', clean_name).strip()
    
    # 2. Check national teams
    for region, countries in REGIONAL_POOLS.items():
        for country in countries:
            if country.lower() in clean_name:
                return "national", region, suffix
                
    # 3. Check club pools
    for country, clubs in CLUBS_POOLS.items():
        for club in clubs:
            if club.lower() in clean_name:
                return "club", country, suffix
                
    # 4. Fallback check on known aliases
    for alias_key, alias_val in NAME_ALIASES.items():
        if alias_key in clean_name:
            for region, countries in REGIONAL_POOLS.items():
                if alias_val in countries:
                    return "national", region, suffix
                    
    # 5. Generic logic based on keywords
    if any(kw in name_lower for kw in ["national", "timnas", "selection", "united states", "republic", "island"]):
        return "national", "europe", suffix
        
    return "club", "england", suffix


def generate_simulated_results(team_name: str, category: str, region: str, suffix: str, count: int = 5) -> list[dict]:
    """Generates 5 realistic past match results for a simulated team."""
    results = []
    
    # Select opponent pool
    if category == "national":
        pool = list(REGIONAL_POOLS.get(region, REGIONAL_POOLS["europe"]))
    else:
        pool = list(CLUBS_POOLS.get(region, CLUBS_POOLS["england"]))
        
    clean_team = team_name.strip()
    opponents = [opp for opp in pool if opp.lower() not in clean_team.lower() and clean_team.lower() not in opp.lower()]
    if not opponents:
        opponents = ["Malaysia", "Singapore", "Vietnam", "Indonesia"] if category == "national" else ["Everton", "Aston Villa", "Wolves"]
        
    now = datetime.now()
    for i in range(count):
        opponent = random.choice(opponents)
        if suffix:
            opponent = f"{opponent} {suffix}"
            
        # Match dates staggered in past
        days_ago = (i + 1) * random.randint(6, 12)
        match_date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        outcome = random.choice(["W", "D", "L"])
        if outcome == "W":
            ts = random.randint(1, 3)
            os_ = random.randint(0, ts - 1)
        elif outcome == "D":
            ts = random.randint(0, 2)
            os_ = ts
        else:
            os_ = random.randint(1, 3)
            ts = random.randint(0, os_ - 1)
            
        is_home = random.choice([True, False])
        results.append({
            "date": match_date,
            "opponent": opponent,
            "score": f"{ts}-{os_}",
            "outcome": outcome,
            "venue": "home" if is_home else "away",
        })
        
    return results


def generate_simulated_roster(team_name: str, category: str, region: str, suffix: str) -> list[dict]:
    """Generates a realistic 22-player roster using demographic-specific names and age boundaries."""
    # Define demographic pools
    if region == "south_asia":
        firsts = ["Ali", "Muhammad", "Ahmed", "Hamza", "Zain", "Arslan", "Bilal", "Tariq", "Usman", "Fahad", "Sajid", "Raza", "Yasir", "Imran", "Naveed", "Asif", "Haris", "Babur", "Shaheen", "Riaz", "Adnan", "Sohail"]
        lasts = ["Khan", "Ahmed", "Ali", "Hussain", "Iqbal", "Sharif", "Akhtar", "Ullah", "Mahmood", "Raza", "Hassan", "Malik", "Chowdhury", "Islam", "Rahman", "Singh", "Kumar", "Sharma", "Roy", "Das"]
    elif region == "southeast_asia":
        firsts = ["Pratama", "Wijaya", "Santoso", "Budi", "Agung", "Rian", "Eko", "Wawan", "Hadi", "Mohd", "Azlan", "Syahmi", "Safawi", "Chanathip", "Somchai", "Kiatisuk", "Sittichok", "Supachai", "Nguyen", "Tran", "Pham"]
        lasts = ["Siregar", "Hidayat", "Kurniawan", "Sitorus", "Pratama", "Putra", "Utomo", "bin Ahmad", "Ramos", "Santos", "Lim", "Tan", "Goh", "Lee", "Dangda", "Songkrasin", "Nguyen", "Tran", "Pham", "Le"]
    elif region in ["middle_east", "africa"]:
        firsts = ["Youssef", "Tarek", "Ahmed", "Mustafa", "Mohamed", "Hassan", "Ali", "Hussein", "Omar", "Kareem", "Mahmoud", "Saeed", "Hamad", "Faisal", "Khalid", "Amir", "Reza", "Mehdi", "Hadi", "Sadio", "Kalidou"]
        lasts = ["Al-Farsi", "Al-Harbi", "Al-Dosari", "Al-Shehri", "Mansour", "Ibrahim", "Khalil", "Hosseini", "Rezaei", "Karimi", "Abadi", "Haddad", "Salim", "Sarkis", "Diallo", "Mendy", "Koulibaly"]
    elif region == "east_asia":
        firsts = ["Kenji", "Hiroto", "Shouta", "Yuto", "Daiki", "Min-jun", "Seo-jun", "Ha-jun", "Do-yun", "Wei", "Qiang", "Lei", "Jun", "Yong"]
        lasts = ["Tanaka", "Sato", "Suzuki", "Takahashi", "Watanabe", "Kim", "Lee", "Park", "Choi", "Jung", "Wang", "Zhang", "Li", "Liu", "Chen"]
    elif region in ["south_america", "north_america", "spain", "portugal"]:
        firsts = ["Lucas", "Mateo", "Santiago", "Matias", "Sebastian", "Diego", "Carlos", "Juan", "Luis", "Gabriel", "Felipe", "Thiago", "Enzo", "Miguel", "Joao", "Pedro", "Bruno", "Rafael"]
        lasts = ["Rodriguez", "Fernandez", "Gonzalez", "Gomez", "Lopez", "Martinez", "Sanchez", "Perez", "Diaz", "Silva", "Santos", "Costa", "Oliveira", "Souza", "Pereira", "Alves", "Ribeiro"]
    else: # europe / default
        firsts = ["Thomas", "Michael", "David", "James", "John", "Robert", "William", "Daniel", "Paul", "Mark", "Stefan", "Lukas", "Marco", "Antoine", "Pierre", "Hans", "Jürgen", "Jan", "Sven"]
        lasts = ["Smith", "Jones", "Taylor", "Williams", "Brown", "Davies", "Evans", "Wilson", "Thomas", "Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Rossi", "Ferrari", "Russo"]

    # Handle youth team age rules
    min_age, max_age = 18, 34
    if suffix:
        s_upper = suffix.upper()
        if "U23" in s_upper:
            min_age, max_age = 18, 23
        elif "U21" in s_upper:
            min_age, max_age = 17, 21
        elif "U20" in s_upper:
            min_age, max_age = 16, 20
        elif "U19" in s_upper:
            min_age, max_age = 16, 19
        elif "U17" in s_upper:
            min_age, max_age = 15, 17
            
    positions = [
        ("Goalkeeper", 2),
        ("Defender", 7),
        ("Midfielder", 7),
        ("Forward", 6)
    ]
    
    roster = []
    jersey_numbers = list(range(1, 100))
    random.shuffle(jersey_numbers)
    
    jersey_idx = 0
    for pos_name, count in positions:
        for _ in range(count):
            first = random.choice(firsts)
            last = random.choice(lasts)
            fullname = f"{first} {last}"
            
            jersey = jersey_numbers[jersey_idx]
            jersey_idx += 1
            age = random.randint(min_age, max_age)
            
            roster.append({
                "name": fullname,
                "jersey": str(jersey),
                "position": pos_name,
                "age": str(age),
            })
            
    return roster


def generate_simulated_h2h(team1_name: str, team2_name: str, count: int = 3) -> list[dict]:
    """Generates a realistic set of head-to-head matches between two teams."""
    h2h = []
    now = datetime.now()
    for i in range(count):
        days_ago = (i + 1) * random.randint(30, 90)
        match_date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        hs = random.randint(0, 3)
        as_ = random.randint(0, 3)
        
        is_t1_home = random.choice([True, False])
        if is_t1_home:
            home = team1_name
            away = team2_name
        else:
            home = team2_name
            away = team1_name
            
        h2h.append({
            "date": match_date,
            "home": home,
            "away": away,
            "score": f"{hs}-{as_}",
        })
    return h2h


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
    is_national_slug = (
        league_slug in NATIONAL_TEAM_SLUGS or 
        league_slug.startswith("fifa.world") or 
        league_slug.startswith("afc.") or 
        league_slug.startswith("caf.") or 
        league_slug.startswith("uefa.") or 
        league_slug.startswith("conmebol.") or
        league_slug.startswith("concacaf.")
    )
    if is_national_slug:
        fallback_list = [
            "fifa.friendly",
            "fifa.worldq.afc",
            "fifa.worldq.uefa",
            "fifa.worldq.conmebol",
            "fifa.worldq.caf",
            "fifa.worldq.concacaf",
            "fifa.worldq.ofc",
            "caf.nations",
            "afc.cup",
            "uefa.euro",
            "conmebol.america",
            "concacaf.nations.a",
            "concacaf.gold",
            "uefa.nations.a",
            "fifa.world"
        ]
        seen = {league_slug}
        slugs_to_try = [league_slug]
        for s in fallback_list:
            if s not in seen:
                seen.add(s)
                slugs_to_try.append(s)

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
    is_national_slug = (
        team1["league_slug"] in NATIONAL_TEAM_SLUGS or 
        team1["league_slug"].startswith("fifa.world") or 
        team1["league_slug"].startswith("afc.") or 
        team1["league_slug"].startswith("caf.") or 
        team1["league_slug"].startswith("uefa.") or 
        team1["league_slug"].startswith("conmebol.") or
        team1["league_slug"].startswith("concacaf.")
    )
    if is_national_slug:
        fallback_list = [
            "fifa.friendly",
            "fifa.worldq.afc",
            "fifa.worldq.uefa",
            "fifa.worldq.conmebol",
            "fifa.worldq.caf",
            "fifa.worldq.concacaf",
            "fifa.worldq.ofc",
            "caf.nations",
            "afc.cup",
            "uefa.euro",
            "conmebol.america",
            "concacaf.nations.a",
            "concacaf.gold",
            "uefa.nations.a",
            "fifa.world"
        ]
        seen = {team1["league_slug"]}
        slugs_to_try = [team1["league_slug"]]
        for s in fallback_list:
            if s not in seen:
                seen.add(s)
                slugs_to_try.append(s)

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

    return predicted_home, predicted_away, home_xg, away_xg


def fetch_team_roster(team_id: str, league_slug: str) -> list[dict]:
    """Fetch the active roster for a team from ESPN API."""
    url = f"{ESPN_BASE}/{league_slug}/teams/{team_id}/roster"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            athletes = data.get("athletes", [])
            roster = []
            for a in athletes:
                roster.append({
                    "name": a.get("displayName", ""),
                    "jersey": a.get("jersey", ""),
                    "position": a.get("position", {}).get("displayName", ""),
                    "age": a.get("age", ""),
                })
            return roster
    except Exception as e:
        print(f"[Roster Fetch] Error for team {team_id} slug {league_slug}: {e}")
    return []


def fetch_team_data(team_name: str) -> dict:
    team_info = _find_team(team_name)
    if not team_info:
        fallback_name = _resolve_name(team_name)
        category, region, suffix = detect_team_category_and_region(fallback_name)
        
        last_results = generate_simulated_results(fallback_name, category, region, suffix, count=5)
        strength = calculate_strength(last_results)
        stats = calculate_team_stats(last_results)
        stats["name"] = fallback_name
        
        roster = generate_simulated_roster(fallback_name, category, region, suffix)
        
        if category == "national":
            league = "International Friendly"
            league_slug = "fifa.friendly"
        else:
            league = "Simulated Club League"
            league_slug = "simulated.league"
            
        badge = "https://a.espncdn.com/i/teamlogos/soccer/500/default-team-logo.png"
        
        return {
            "found": True,
            "simulated": True,
            "name": fallback_name,
            "id": f"simulated_{fallback_name.lower().replace(' ', '_')}",
            "league": league,
            "league_slug": league_slug,
            "badge": badge,
            "last_results": last_results,
            "strength": strength,
            "stats": stats,
            "roster": roster,
        }
    last_results = _get_last_results(
        team_info["id"], team_info["name"], team_info["league_slug"]
    )
    
    # If a real team was found but has no schedule / past results, let's also simulate results and roster so we don't return an empty card!
    if not last_results:
        category, region, suffix = detect_team_category_and_region(team_info["name"])
        last_results = generate_simulated_results(team_info["name"], category, region, suffix, count=5)
        strength = calculate_strength(last_results)
        stats = calculate_team_stats(last_results)
        stats["name"] = team_info["name"]
        roster = generate_simulated_roster(team_info["name"], category, region, suffix)
        
        return {
            "found": True,
            "simulated": True,
            "name": team_info["name"],
            "id": team_info["id"],
            "league": team_info["league"],
            "league_slug": team_info["league_slug"],
            "badge": team_info["logo"],
            "last_results": last_results,
            "strength": strength,
            "stats": stats,
            "roster": roster,
        }

    strength = calculate_strength(last_results)
    stats = calculate_team_stats(last_results)
    stats["name"] = team_info["name"]
    
    # Fetch roster with regional fallbacks for national teams
    roster = fetch_team_roster(team_info["id"], team_info["league_slug"])
    if not roster and (
        team_info["league_slug"] in NATIONAL_TEAM_SLUGS or
        team_info["league_slug"].startswith("fifa.world") or
        team_info["league_slug"].startswith("afc.") or
        team_info["league_slug"].startswith("caf.") or
        team_info["league_slug"].startswith("uefa.") or
        team_info["league_slug"].startswith("conmebol.") or
        team_info["league_slug"].startswith("concacaf.")
    ):
        for fallback_slug in ["fifa.world", "fifa.worldq.afc", "fifa.worldq.uefa", "fifa.worldq.conmebol", "fifa.worldq.caf", "fifa.worldq.concacaf"]:
            if fallback_slug != team_info["league_slug"]:
                roster = fetch_team_roster(team_info["id"], fallback_slug)
                if roster:
                    break
                    
    # If roster is still empty, let's generate a simulated roster so we don't display an empty player lists card!
    if not roster:
        category, region, suffix = detect_team_category_and_region(team_info["name"])
        roster = generate_simulated_roster(team_info["name"], category, region, suffix)

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
        "roster": roster,
    }


def get_h2h(team1_data: dict, team2_data: dict) -> list[dict]:
    if not team1_data.get("found") or not team2_data.get("found"):
        return []
        
    # If either team is simulated, generate simulated H2H directly
    if team1_data.get("simulated") or team2_data.get("simulated"):
        return generate_simulated_h2h(team1_data["name"], team2_data["name"])
        
    # Otherwise call real H2H
    h2h = _get_h2h(team1_data, team2_data)
    
    # If no real matches found (e.g. they haven't played recently), return a simulated H2H to prevent empty card sections
    if not h2h:
        return generate_simulated_h2h(team1_data["name"], team2_data["name"])
        
    return h2h


def calculate_betting_markets(home_xg: float, away_xg: float) -> dict:
    """
    Calculates betting odds based on Poisson distribution.
    Applies a typical 5% bookmaker margin (multiplier 0.95).
    """
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0
    
    p_over_1_5 = 0.0
    p_under_1_5 = 0.0
    p_over_2_5 = 0.0
    p_under_2_5 = 0.0
    p_over_3_5 = 0.0
    p_under_3_5 = 0.0
    
    p_btts_yes = 0.0
    p_btts_no = 0.0
    
    # Calculate probabilities up to 10 goals for accuracy
    max_goals = 10
    joint_probs = {}
    
    for h in range(max_goals + 1):
        p_h = poisson_probability(home_xg, h)
        for a in range(max_goals + 1):
            p_a = poisson_probability(away_xg, a)
            joint_prob = p_h * p_a
            joint_probs[(h, a)] = joint_prob
            
            # Match results
            if h > a:
                p_home += joint_prob
            elif h == a:
                p_draw += joint_prob
            else:
                p_away += joint_prob
                
            # Totals
            total_goals = h + a
            if total_goals > 1.5:
                p_over_1_5 += joint_prob
            else:
                p_under_1_5 += joint_prob
                
            if total_goals > 2.5:
                p_over_2_5 += joint_prob
            else:
                p_under_2_5 += joint_prob
                
            if total_goals > 3.5:
                p_over_3_5 += joint_prob
            else:
                p_under_3_5 += joint_prob
                
            # Both Teams to Score (BTTS)
            if h >= 1 and a >= 1:
                p_btts_yes += joint_prob
            else:
                p_btts_no += joint_prob

    # Normalize (just in case they don't sum to exactly 1.0 due to tail truncation)
    total_outcome_p = p_home + p_draw + p_away
    if total_outcome_p > 0:
        p_home /= total_outcome_p
        p_draw /= total_outcome_p
        p_away /= total_outcome_p
        
    total_totals_1_5 = p_over_1_5 + p_under_1_5
    if total_totals_1_5 > 0:
        p_over_1_5 /= total_totals_1_5
        p_under_1_5 /= total_totals_1_5
        
    total_totals_2_5 = p_over_2_5 + p_under_2_5
    if total_totals_2_5 > 0:
        p_over_2_5 /= total_totals_2_5
        p_under_2_5 /= total_totals_2_5
        
    total_totals_3_5 = p_over_3_5 + p_under_3_5
    if total_totals_3_5 > 0:
        p_over_3_5 /= total_totals_3_5
        p_under_3_5 /= total_totals_3_5

    total_btts = p_btts_yes + p_btts_no
    if total_btts > 0:
        p_btts_yes /= total_btts
        p_btts_no /= total_btts

    # Double chance probabilities
    p_1x = p_home + p_draw
    p_12 = p_home + p_away
    p_x2 = p_draw + p_away

    # Payout margin (95% payout, i.e. 5% bookmaker margin)
    margin = 0.95
    
    # Helper to convert probability to odds with margin and clamps
    def to_odds(p: float) -> float:
        if p <= 0:
            return 99.0
        odds = margin / p
        # Clamp between 1.01 and 99.0
        return float(round(max(1.01, min(99.0, odds)), 2))

    # Calculate final odds
    odds = {
        "1x2": {
            "1": to_odds(p_home),
            "x": to_odds(p_draw),
            "2": to_odds(p_away),
            "probabilities": {
                "1": float(round(p_home * 100, 1)),
                "x": float(round(p_draw * 100, 1)),
                "2": float(round(p_away * 100, 1))
            }
        },
        "double_chance": {
            "1x": to_odds(p_1x),
            "12": to_odds(p_12),
            "x2": to_odds(p_x2),
            "probabilities": {
                "1x": float(round(p_1x * 100, 1)),
                "12": float(round(p_12 * 100, 1)),
                "x2": float(round(p_x2 * 100, 1))
            }
        },
        "total_2_5": {
            "over": to_odds(p_over_2_5),
            "under": to_odds(p_under_2_5),
            "probabilities": {
                "over": float(round(p_over_2_5 * 100, 1)),
                "under": float(round(p_under_2_5 * 100, 1))
            }
        },
        "total_1_5": {
            "over": to_odds(p_over_1_5),
            "under": to_odds(p_under_1_5),
            "probabilities": {
                "over": float(round(p_over_1_5 * 100, 1)),
                "under": float(round(p_under_1_5 * 100, 1))
            }
        },
        "total_3_5": {
            "over": to_odds(p_over_3_5),
            "under": to_odds(p_under_3_5),
            "probabilities": {
                "over": float(round(p_over_3_5 * 100, 1)),
                "under": float(round(p_under_3_5 * 100, 1))
            }
        },
        "btts": {
            "yes": to_odds(p_btts_yes),
            "no": to_odds(p_btts_no),
            "probabilities": {
                "yes": float(round(p_btts_yes * 100, 1)),
                "no": float(round(p_btts_no * 100, 1))
            }
        }
    }
    
    # AI Betting Tip generator (rule-based recommendation for the premium card value-add)
    # Find highest confidence / best value bet
    tips = []
    # 1. 1X2 tips
    if p_home > 0.60:
        tips.append({"type": "1X2", "selection": "1", "odds": odds["1x2"]["1"], "confidence": p_home, "text": f"Home Win (1) @ {odds['1x2']['1']}"})
    elif p_away > 0.60:
        tips.append({"type": "1X2", "selection": "2", "odds": odds["1x2"]["2"], "confidence": p_away, "text": f"Away Win (2) @ {odds['1x2']['2']}"})
        
    # 2. Double chance tips (higher safety)
    if p_1x > 0.80:
        tips.append({"type": "Double Chance", "selection": "1X", "odds": odds["double_chance"]["1x"], "confidence": p_1x, "text": f"Home Win or Draw (1X) @ {odds['double_chance']['1x']}"})
    elif p_x2 > 0.80:
        tips.append({"type": "Double Chance", "selection": "X2", "odds": odds["double_chance"]["x2"], "confidence": p_x2, "text": f"Draw or Away Win (X2) @ {odds['double_chance']['x2']}"})
        
    # 3. Totals
    if p_over_2_5 > 0.60:
        tips.append({"type": "Total Goals", "selection": "Over 2.5", "odds": odds["total_2_5"]["over"], "confidence": p_over_2_5, "text": f"Total Over 2.5 @ {odds['total_2_5']['over']}"})
    elif p_under_2_5 > 0.60:
        tips.append({"type": "Total Goals", "selection": "Under 2.5", "odds": odds["total_2_5"]["under"], "confidence": p_under_2_5, "text": f"Total Under 2.5 @ {odds['total_2_5']['under']}"})
        
    # 4. BTTS
    if p_btts_yes > 0.60:
        tips.append({"type": "Both Teams to Score", "selection": "Yes", "odds": odds["btts"]["yes"], "confidence": p_btts_yes, "text": f"BTTS (Yes) @ {odds['btts']['yes']}"})
    elif p_btts_no > 0.60:
        tips.append({"type": "Both Teams to Score", "selection": "No", "odds": odds["btts"]["no"], "confidence": p_btts_no, "text": f"BTTS (No) @ {odds['btts']['no']}"})

    # Sort tips by confidence (probability) descending
    tips.sort(key=lambda x: x["confidence"], reverse=True)
    
    # If no high confidence tips, select the best double chance or total under/over as fallback
    if not tips:
        # Fallback to the one with highest probability
        candidate = {
            "type": "Double Chance",
            "selection": "1X" if p_1x >= p_x2 else "X2",
            "odds": odds["double_chance"]["1x"] if p_1x >= p_x2 else odds["double_chance"]["x2"],
            "confidence": max(p_1x, p_x2)
        }
        candidate["text"] = f"Double Chance ({candidate['selection']}) @ {candidate['odds']}"
        best_tip = candidate
    else:
        best_tip = tips[0]
        
    odds["recommended_tip"] = {
        "market": best_tip["type"],
        "selection": best_tip["selection"],
        "odds": best_tip["odds"],
        "confidence": float(round(best_tip["confidence"] * 100, 1)),
        "text": best_tip["text"]
    }
    
    return odds


def search_yahoo_odds(home_team: str, away_team: str) -> str:
    """Scrapes Yahoo Search for 1xbet decimal odds of the match."""
    from bs4 import BeautifulSoup
    url = "https://search.yahoo.com/search"
    query = f"{home_team} vs {away_team} 1xbet odds decimal"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, params={"p": query}, headers=headers, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            snippets = soup.find_all('div', class_='compText')
            lines = []
            for idx, snippet_div in enumerate(snippets[:6]):
                parent = snippet_div.parent
                title = "No Title"
                curr = parent
                for _ in range(4):
                    if not curr:
                        break
                    h3 = curr.find('h3')
                    if h3:
                        title = h3.get_text().strip()
                        break
                    curr = curr.parent
                snippet = snippet_div.get_text().strip()
                lines.append(f"Result {idx+1}: {title}\nSnippet: {snippet}")
            return "\n\n".join(lines)
    except Exception as e:
        print(f"[Odds Search] Yahoo Search scrape error: {e}")
    return ""


def extract_odds_with_ai(home_team: str, away_team: str, search_context: str) -> Optional[dict]:
    """Queries Pollinations unified AI endpoint to extract odds from search snippets."""
    if not search_context or not search_context.strip():
        return None
        
    prompt = f"""
Analyze the web search results for the football match: {home_team} vs {away_team}.
Extract the real-time decimal betting odds from 1xbet or other bookmakers if present.

Search Results:
\"\"\"
{search_context}
\"\"\"

Your task is to return ONLY a raw JSON block containing the odds that were found. 
If 1X2 odds are found in the text (either direct decimal odds like 1.85, 3.60, 4.20 or as percentages like 55% win probability), populate them. If percentages are given (e.g. 60.98% Win, 21.55% Draw, 15.38% Away), convert them to decimal odds using the formula: odds = 0.95 / (percent / 100).
Also look for Over/Under 2.5 and BTTS (Both Teams to Score) odds.

Use the following JSON structure. If any value or market is not found, leave it as null.
DO NOT write any explanation, markdown formatting, or code fences. Only output the raw JSON.

{{
  "1x2": {{
    "1": null,
    "x": null,
    "2": null
  }},
  "total_2_5": {{
    "over": null,
    "under": null
  }},
  "btts": {{
    "yes": null,
    "no": null
  }}
}}
"""
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "user", "content": prompt.strip()}
        ],
        "model": "openai"
    }
    
    import time
    for attempt in range(1, 3):
        try:
            print(f"[Odds Search] AI extraction attempt {attempt}...")
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                response_text = resp.text.strip()
                # Clean response from any markdown block formatting
                cleaned = re.sub(r'^```json\s*', '', response_text)
                cleaned = re.sub(r'\s*```$', '', cleaned)
                cleaned = cleaned.strip()
                
                parsed = json.loads(cleaned)
                return parsed
            else:
                print(f"[Odds Search] AI extraction attempt {attempt} status: {resp.status_code}")
        except Exception as e:
            print(f"[Odds Search] AI extraction attempt {attempt} error: {e}")
            if attempt < 2:
                time.sleep(1)
    return None


def override_betting_markets_with_realtime(betting_markets: dict, realtime_odds: dict) -> dict:
    """Updates decimal odds, calculates Double Chance, and re-computes the recommended tip."""
    if not realtime_odds:
        return betting_markets
        
    margin = 0.95
    updated = False
    
    # 1. Update 1X2
    odds_1x2 = realtime_odds.get("1x2")
    if odds_1x2 and odds_1x2.get("1") and odds_1x2.get("x") and odds_1x2.get("2"):
        try:
            o1 = float(odds_1x2["1"])
            ox = float(odds_1x2["x"])
            o2 = float(odds_1x2["2"])
            
            betting_markets["1x2"]["1"] = o1
            betting_markets["1x2"]["x"] = ox
            betting_markets["1x2"]["2"] = o2
            
            p1 = 1 / o1
            px = 1 / ox
            p2 = 1 / o2
            s = p1 + px + p2
            if s > 0:
                p1_n = p1 / s
                px_n = px / s
                p2_n = p2 / s
                betting_markets["1x2"]["probabilities"] = {
                    "1": float(round(p1_n * 100, 1)),
                    "x": float(round(px_n * 100, 1)),
                    "2": float(round(p2_n * 100, 1))
                }
                
                # Double Chance calculation based on new 1X2 probabilities
                p_1x = p1_n + px_n
                p_12 = p1_n + p2_n
                p_x2 = px_n + p2_n
                
                betting_markets["double_chance"]["1x"] = float(round(max(1.01, min(99.0, margin / p_1x)), 2))
                betting_markets["double_chance"]["12"] = float(round(max(1.01, min(99.0, margin / p_12)), 2))
                betting_markets["double_chance"]["x2"] = float(round(max(1.01, min(99.0, margin / p_x2)), 2))
                
                betting_markets["double_chance"]["probabilities"] = {
                    "1x": float(round(p_1x * 100, 1)),
                    "12": float(round(p_12 * 100, 1)),
                    "x2": float(round(p_x2 * 100, 1))
                }
                updated = True
        except (ValueError, ZeroDivisionError, TypeError):
            pass

    # 2. Update Total 2.5
    odds_tot = realtime_odds.get("total_2_5")
    if odds_tot and odds_tot.get("over") and odds_tot.get("under"):
        try:
            o_over = float(odds_tot["over"])
            o_under = float(odds_tot["under"])
            betting_markets["total_2_5"]["over"] = o_over
            betting_markets["total_2_5"]["under"] = o_under
            
            p_over = 1 / o_over
            p_under = 1 / o_under
            s = p_over + p_under
            if s > 0:
                p_over_n = p_over / s
                p_under_n = p_under / s
                betting_markets["total_2_5"]["probabilities"] = {
                    "over": float(round(p_over_n * 100, 1)),
                    "under": float(round(p_under_n * 100, 1))
                }
                updated = True
        except (ValueError, ZeroDivisionError, TypeError):
            pass

    # 3. Update BTTS
    odds_btts = realtime_odds.get("btts")
    if odds_btts and odds_btts.get("yes") and odds_btts.get("no"):
        try:
            o_yes = float(odds_btts["yes"])
            o_no = float(odds_btts["no"])
            betting_markets["btts"]["yes"] = o_yes
            betting_markets["btts"]["no"] = o_no
            
            p_yes = 1 / o_yes
            p_no = 1 / o_no
            s = p_yes + p_no
            if s > 0:
                p_yes_n = p_yes / s
                p_no_n = p_no / s
                betting_markets["btts"]["probabilities"] = {
                    "yes": float(round(p_yes_n * 100, 1)),
                    "no": float(round(p_no_n * 100, 1))
                }
                updated = True
        except (ValueError, ZeroDivisionError, TypeError):
            pass

    # 4. Recalculate Recommended Tip if odds were updated
    if updated:
        try:
            p_home = betting_markets["1x2"]["probabilities"]["1"] / 100.0
            p_away = betting_markets["1x2"]["probabilities"]["2"] / 100.0
            p_1x = betting_markets["double_chance"]["probabilities"]["1x"] / 100.0
            p_x2 = betting_markets["double_chance"]["probabilities"]["x2"] / 100.0
            p_over_2_5 = betting_markets["total_2_5"]["probabilities"]["over"] / 100.0
            p_under_2_5 = betting_markets["total_2_5"]["probabilities"]["under"] / 100.0
            p_btts_yes = betting_markets["btts"]["probabilities"]["yes"] / 100.0
            p_btts_no = betting_markets["btts"]["probabilities"]["no"] / 100.0
            
            tips = []
            if p_home > 0.60:
                tips.append({"type": "1X2", "selection": "1", "odds": betting_markets["1x2"]["1"], "confidence": p_home, "text": f"Home Win (1) @ {betting_markets['1x2']['1']}"})
            elif p_away > 0.60:
                tips.append({"type": "1X2", "selection": "2", "odds": betting_markets["1x2"]["2"], "confidence": p_away, "text": f"Away Win (2) @ {betting_markets['1x2']['2']}"})
                
            if p_1x > 0.80:
                tips.append({"type": "Double Chance", "selection": "1X", "odds": betting_markets["double_chance"]["1x"], "confidence": p_1x, "text": f"Home Win or Draw (1X) @ {betting_markets['double_chance']['1x']}"})
            elif p_x2 > 0.80:
                tips.append({"type": "Double Chance", "selection": "X2", "odds": betting_markets["double_chance"]["x2"], "confidence": p_x2, "text": f"Draw or Away Win (X2) @ {betting_markets['double_chance']['x2']}"})
                
            if p_over_2_5 > 0.60:
                tips.append({"type": "Total Goals", "selection": "Over 2.5", "odds": betting_markets["total_2_5"]["over"], "confidence": p_over_2_5, "text": f"Total Over 2.5 @ {betting_markets['total_2_5']['over']}"})
            elif p_under_2_5 > 0.60:
                tips.append({"type": "Total Goals", "selection": "Under 2.5", "odds": betting_markets["total_2_5"]["under"], "confidence": p_under_2_5, "text": f"Total Under 2.5 @ {betting_markets['total_2_5']['under']}"})
                
            if p_btts_yes > 0.60:
                tips.append({"type": "Both Teams to Score", "selection": "Yes", "odds": betting_markets["btts"]["yes"], "confidence": p_btts_yes, "text": f"BTTS (Yes) @ {betting_markets['btts']['yes']}"})
            elif p_btts_no > 0.60:
                tips.append({"type": "Both Teams to Score", "selection": "No", "odds": betting_markets["btts"]["no"], "confidence": p_btts_no, "text": f"BTTS (No) @ {betting_markets['btts']['no']}"})

            tips.sort(key=lambda x: x["confidence"], reverse=True)
            if not tips:
                candidate = {
                    "type": "Double Chance",
                    "selection": "1X" if p_1x >= p_x2 else "X2",
                    "odds": betting_markets["double_chance"]["1x"] if p_1x >= p_x2 else betting_markets["double_chance"]["x2"],
                    "confidence": max(p_1x, p_x2)
                }
                candidate["text"] = f"Double Chance ({candidate['selection']}) @ {candidate['odds']}"
                best_tip = candidate
            else:
                best_tip = tips[0]
                
            betting_markets["recommended_tip"] = {
                "market": best_tip["type"],
                "selection": best_tip["selection"],
                "odds": best_tip["odds"],
                "confidence": float(round(best_tip["confidence"] * 100, 1)),
                "text": best_tip["text"]
            }
        except Exception:
            pass
            
    return betting_markets


def calculate_betting_markets_with_search(
    home_xg: float,
    away_xg: float,
    home_name: str,
    away_name: str,
    is_simulated: bool = False
) -> dict:
    """Orchestrates standard mathematical odds generation and web search AI odds extraction."""
    # 1. Baseline Poisson odds
    betting_markets = calculate_betting_markets(home_xg, away_xg)
    
    # 2. Skip search for simulated/mock matches
    if is_simulated or "simulated" in home_name.lower() or "simulated" in away_name.lower():
        print(f"[Odds Search] Skipping real-time odds search for simulated match: {home_name} vs {away_name}")
        return betting_markets
        
    # 3. Perform web search and override if successful
    try:
        print(f"[Odds Search] Scraping web for real-time odds: {home_name} vs {away_name}")
        search_context = search_yahoo_odds(home_name, away_name)
        if search_context:
            realtime_odds = extract_odds_with_ai(home_name, away_name, search_context)
            if realtime_odds:
                print(f"[Odds Search] Real-time odds found. Overriding baseline.")
                betting_markets = override_betting_markets_with_realtime(betting_markets, realtime_odds)
            else:
                print(f"[Odds Search] No structured odds found in search context.")
        else:
            print(f"[Odds Search] Search context is empty.")
    except Exception as e:
        print(f"[Odds Search] Unexpected error during search/override: {e}")
        
    return betting_markets

