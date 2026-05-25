import re
from datetime import datetime, timedelta

TEAM_KEYWORDS = [
    "chelsea", "arsenal", "liverpool", "manchester united", "man united", "man utd",
    "manchester city", "man city", "tottenham", "spurs", "newcastle", "west ham",
    "aston villa", "everton", "brighton", "fulham", "wolves", "leicester", "brentford",
    "crystal palace", "nottingham forest", "bournemouth", "southampton", "ipswich",
    "barcelona", "real madrid", "atletico madrid", "sevilla", "psg",
    "paris saint-germain", "lyon", "marseille", "monaco",
    "juventus", "ac milan", "inter milan", "roma", "napoli", "lazio",
    "bayern munich", "borussia dortmund", "rb leipzig", "bayer leverkusen",
    "ajax", "benfica", "porto", "celtic", "rangers",
    "flamengo", "palmeiras", "boca juniors", "river plate",
    "persib", "persija", "arema", "bali united", "psis semarang", "borneo fc",
    # Indonesian national team names
    "meksiko", "ceko", "republik ceko", "inggris", "jerman", "prancis",
    "belanda", "brasil", "spanyol", "portugis", "italia", "belgia",
    "kroasia", "polandia", "swiss", "ukraina", "turki", "maroko",
    "jepang", "korea selatan", "korea", "australia", "ekuador", "kolombia",
    "uruguay", "chili", "peru", "ghana", "nigeria", "kamerun", "mesir",
    "aljazair", "arab saudi", "kanada", "kosta rika", "rusia", "swedia",
    "denmark", "norwegia", "skotlandia", "hungaria", "rumania", "serbia",
    "yunani", "austria", "slowakia", "islandia", "indonesia", "thailand",
    "vietnam", "malaysia", "filipina", "tiongkok", "senegal", "venezuela",
    "paraguay", "bolivia", "iran", "as",
    # English national team names
    "mexico", "czech republic", "england", "germany", "france", "netherlands",
    "brazil", "spain", "portugal", "italy", "belgium", "croatia", "poland",
    "switzerland", "ukraine", "turkey", "morocco", "japan", "south korea",
    "colombia", "chile", "senegal", "ghana", "nigeria", "cameroon",
    "egypt", "algeria", "saudi arabia", "canada", "costa rica", "russia",
    "sweden", "denmark", "norway", "scotland", "hungary", "romania",
    "greece", "slovakia", "iceland", "argentina", "usa", "united states",
]

VS_PATTERNS = [
    r'(.+?)\s+(?:vs\.?|versus|vs|lawan|melawan|kontra|x|-)\s+(.+)',
    r'(.+?)\s+(?:vs\.?|versus|vs|lawan|melawan|kontra|x|-)\s+(.+)',
]

DATE_PATTERNS = {
    r'\bbesok\b': 1,
    r'\blusa\b': 2,
    r'\bmalam ini\b|\bmalam\s+ini\b': 0,
    r'\bhari ini\b|\btoday\b': 0,
    r'\btomorrow\b': 1,
    r'\bweekend\b|\bakhir pekan\b': 6,
    r'\bminggu depan\b|\bnext week\b': 7,
}

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}


def extract_date(text: str) -> str:
    text_lower = text.lower()
    today = datetime.now()

    for pattern, days_ahead in DATE_PATTERNS.items():
        if re.search(pattern, text_lower):
            target = today + timedelta(days=days_ahead)
            return target.strftime("%Y-%m-%d")

    date_re = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', text)
    if date_re:
        day, month = int(date_re.group(1)), int(date_re.group(2))
        year = int(date_re.group(3)) if date_re.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    for month_name, month_num in MONTH_MAP.items():
        month_re = re.search(rf'(\d{{1,2}})\s+{month_name}', text_lower)
        if month_re:
            day = int(month_re.group(1))
            try:
                return datetime(today.year, month_num, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

    return today.strftime("%Y-%m-%d")


def clean_team_name(name: str) -> str:
    name = name.strip()
    noise_words = [
        r'\bprediksi\b', r'\bskor\b', r'\bpertandingan\b', r'\bbesok\b', r'\bmalam\b',
        r'\bhari\b', r'\bini\b', r'\btanggal\b', r'\bpada\b', r'\bsiapa\b',
        r'\bmenang\b', r'\bkankan\b', r'\bbakal\b', r'\bakan\b', r'\bdi\b',
        r'\bhome\b', r'\bkandang\b', r'\btamu\b', r'\bdandang\b',
        r'\bwho\b', r'\bwill\b', r'\bwin\b', r'\btonight\b', r'\btomorrow\b',
        r'\bpredict\b', r'\bmatch\b', r'\bgame\b', r'\bscore\b',
        r'\blusa\b', r'\bweekend\b', r'\bakhir\b', r'\bpekan\b',
        r'\bminggu\b', r'\bdepan\b', r'\bnext\b', r'\bweek\b',
        # Month names (Indonesian and English)
        r'\bjanuary\b', r'\bfebruary\b', r'\bmarch\b', r'\bapril\b',
        r'\bmay\b', r'\bjune\b', r'\bjuly\b', r'\baugust\b',
        r'\bseptember\b', r'\boctober\b', r'\bnovember\b', r'\bdecember\b',
        r'\bjanuari\b', r'\bfebruari\b', r'\bmaret\b',
        r'\bmei\b', r'\bjuni\b', r'\bjuli\b', r'\bagustus\b',
        r'\boktober\b', r'\bdesember\b',
        r'\?', r'!', r',', r'\.',
    ]
    for word in noise_words:
        name = re.sub(word, '', name, flags=re.IGNORECASE).strip()
    # Strip standalone numbers (dates, years like 12, 2026)
    name = re.sub(r'\b\d{1,4}\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_teams_and_date(user_message: str) -> dict:
    text = user_message.strip()

    for pattern in VS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            home_raw = clean_team_name(match.group(1))
            away_raw = clean_team_name(match.group(2))
            date = extract_date(text)
            return {
                "home_team": home_raw,
                "away_team": away_raw,
                "date": date,
                "confidence": "high",
            }

    found_teams = []
    text_lower = text.lower()
    for team in sorted(TEAM_KEYWORDS, key=len, reverse=True):
        if team in text_lower and team not in [t.lower() for t in found_teams]:
            found_teams.append(team.title())
            if len(found_teams) == 2:
                break

    if len(found_teams) >= 2:
        date = extract_date(text)
        return {
            "home_team": found_teams[0],
            "away_team": found_teams[1],
            "date": date,
            "confidence": "medium",
        }

    return {
        "home_team": None,
        "away_team": None,
        "date": extract_date(text),
        "confidence": "low",
        "error": "Tidak bisa mendeteksi nama tim. Coba format: 'Chelsea vs Arsenal'",
    }
