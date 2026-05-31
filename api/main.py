import os
import sys
import time
import requests
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Ensure api directory is in Python path for serverless imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp_extractor import extract_teams_and_date
from data_fetcher import fetch_team_data, get_h2h, predict_score, calculate_team_stats, calculate_betting_markets
from database import init_db, get_user_by_username, get_user_by_id, create_user, verify_password, deduct_credit, UNLIMITED
from auth import create_token, decode_token

app = FastAPI(title="Kyonayr Playground API", root_path="/api")

# CORS Origin Lockdowns
ALLOWED_ORIGINS_ENV = os.environ.get("ALLOWED_ORIGINS")
if ALLOWED_ORIGINS_ENV:
    allow_origins = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]
else:
    # Secure Vercel production default: restrict to local development and Vercel domains
    if os.environ.get("VERCEL") or os.environ.get("NODE_ENV") == "production":
        allow_origins = ["https://*.vercel.app"]
    else:
        allow_origins = ["*"]

allow_credentials = "*" not in allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)


@app.on_event("startup")
def startup():
    # Dynamically initialize database tables (works for Postgres or SQLite)
    init_db()


# ---------- Simple IP-Based Sliding-Window Rate Limiter ----------

RATE_LIMIT_CACHE = {}
RATE_LIMIT_WINDOW = 10  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # max requests per window


def check_rate_limit(request: Request, endpoint: str):
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    if not client_ip:
        return
    
    current_time = time.time()
    key = (client_ip, endpoint)
    
    if key not in RATE_LIMIT_CACHE:
        RATE_LIMIT_CACHE[key] = []
        
    RATE_LIMIT_CACHE[key] = [t for t in RATE_LIMIT_CACHE[key] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(RATE_LIMIT_CACHE[key]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak permintaan (Rate limit exceeded). Silakan coba lagi beberapa saat lagi."
        )
        
    RATE_LIMIT_CACHE[key].append(current_time)



    # Garbage collection
    if len(RATE_LIMIT_CACHE) > 5000:
        keys_to_delete = []
        for k, timestamps in RATE_LIMIT_CACHE.items():
            valid_timestamps = [t for t in timestamps if current_time - t < RATE_LIMIT_WINDOW]
            if not valid_timestamps:
                keys_to_delete.append(k)
            else:
                RATE_LIMIT_CACHE[k] = valid_timestamps
        for k in keys_to_delete:
            RATE_LIMIT_CACHE.pop(k, None)


# ---------- Hardened Request Models ----------

class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=3, max_length=100)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class PredictRequest(BaseModel):
    home_team: str = Field(..., min_length=1, max_length=100)
    away_team: str = Field(..., min_length=1, max_length=100)
    date: str | None = Field(None, max_length=30)


# ---------- Auth helpers ----------

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Login diperlukan")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan")
    return user


def user_to_response(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "credits": user["credits"],
    }


# ---------- Auth routes ----------

@app.post("/auth/register")
async def register(req: AuthRequest, request: Request):
    check_rate_limit(request, "auth")
    user = create_user(req.username.strip(), req.password)
    if not user:
        raise HTTPException(status_code=409, detail="Username sudah digunakan")
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": user_to_response(user)}


@app.post("/auth/login")
async def login(req: AuthRequest, request: Request):
    check_rate_limit(request, "auth")
    user = get_user_by_username(req.username.strip())
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": user_to_response(user)}


@app.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return user_to_response(current_user)


# ---------- Health ----------

@app.get("/healthz")
async def health():
    return {"status": "ok"}


# ---------- Smart prediction logic ----------

def _form_bar(icons: list[str]) -> str:
    color_text = {"W": "M", "D": "S", "L": "K"}
    return " ".join(color_text.get(i, "?") for i in icons)


def _h2h_record(h2h: list[dict], home_name: str) -> tuple[int, int, int]:
    hw, aw, draws = 0, 0, 0
    for m in h2h:
        try:
            hs, as_ = map(int, m["score"].split("-"))
        except Exception:
            continue
        if m["home"].lower() == home_name.lower():
            if hs > as_:
                hw += 1
            elif hs < as_:
                aw += 1
            else:
                draws += 1
        else:
            if as_ > hs:
                hw += 1
            elif as_ < hs:
                aw += 1
            else:
                draws += 1
    return hw, aw, draws


def _confidence_label(home_xg: int, away_xg: int, home_stats: dict, away_stats: dict) -> str:
    both_have_data = home_stats.get("weighted_points", 0) > 0 and away_stats.get("weighted_points", 0) > 0
    diff = abs(home_stats.get("weighted_points", 0) - away_stats.get("weighted_points", 0))
    if not both_have_data:
        return "Rendah"
    if diff >= 8:
        return "Tinggi"
    return "Sedang"


def build_reasoning(
    home_name: str,
    away_name: str,
    home_results: list[dict],
    away_results: list[dict],
    h2h: list[dict],
    home_stats: dict,
    away_stats: dict,
    predicted_home: int,
    predicted_away: int,
) -> str:
    lines = []

    # Form terkini
    lines.append("**Analisis Form Terkini:**")

    if home_results:
        form_str = _form_bar(home_stats.get("form_icons", []))
        lines.append(
            f"{home_name}: [{form_str}] — {home_stats['form_label']}\n"
            f"  Rata-rata gol: {home_stats['avg_scored']} dicetak / {home_stats['avg_conceded']} kebobolan per laga"
        )
    else:
        lines.append(f"{home_name}: Data tidak tersedia")

    if away_results:
        form_str = _form_bar(away_stats.get("form_icons", []))
        lines.append(
            f"{away_name}: [{form_str}] — {away_stats['form_label']}\n"
            f"  Rata-rata gol: {away_stats['avg_scored']} dicetak / {away_stats['avg_conceded']} kebobolan per laga"
        )
    else:
        lines.append(f"{away_name}: Data tidak tersedia")

    # Insight kunci
    insights = []

    if home_stats.get("win_streak", 0) >= 3:
        insights.append(f"{home_name} tengah dalam tren kemenangan {home_stats['win_streak']} laga beruntun.")
    if away_stats.get("win_streak", 0) >= 3:
        insights.append(f"{away_name} tengah dalam tren kemenangan {away_stats['win_streak']} laga beruntun.")

    if home_stats.get("loss_streak", 0) >= 3:
        insights.append(f"{home_name} sedang dalam tren kekalahan {home_stats['loss_streak']} laga beruntun.")
    if away_stats.get("loss_streak", 0) >= 3:
        insights.append(f"{away_name} sedang dalam tren kekalahan {away_stats['loss_streak']} laga beruntun.")

    if home_stats.get("clean_sheets", 0) >= 3:
        insights.append(f"{home_name} memiliki pertahanan sangat solid ({home_stats['clean_sheets']} clean sheet dari {len(home_results)} laga).")
    if away_stats.get("clean_sheets", 0) >= 3:
        insights.append(f"{away_name} memiliki pertahanan sangat solid ({away_stats['clean_sheets']} clean sheet dari {len(away_results)} laga).")

    ha_scored = home_stats.get("avg_scored", 0)
    aa_scored = away_stats.get("avg_scored", 0)
    ha_conceded = home_stats.get("avg_conceded", 99)
    aa_conceded = away_stats.get("avg_conceded", 99)

    if ha_scored > aa_scored + 0.6:
        insights.append(f"{home_name} lebih produktif di depan ({ha_scored} vs {aa_scored} gol/game).")
    elif aa_scored > ha_scored + 0.6:
        insights.append(f"{away_name} lebih produktif di depan ({aa_scored} vs {ha_scored} gol/game).")

    if ha_conceded < aa_conceded - 0.5:
        insights.append(f"Pertahanan {home_name} lebih rapat ({ha_conceded} vs {aa_conceded} gol kemasukan/game).")
    elif aa_conceded < ha_conceded - 0.5:
        insights.append(f"Pertahanan {away_name} lebih rapat ({aa_conceded} vs {ha_conceded} gol kemasukan/game).")

    if home_stats.get("failed_to_score", 0) >= 3:
        insights.append(f"{home_name} kesulitan mencetak gol — gagal skor di {home_stats['failed_to_score']} dari {len(home_results)} laga terakhir.")
    if away_stats.get("failed_to_score", 0) >= 3:
        insights.append(f"{away_name} kesulitan mencetak gol — gagal skor di {away_stats['failed_to_score']} dari {len(away_results)} laga terakhir.")

    if insights:
        lines.append("\n**Insight Kunci:**")
        lines.extend([f"- {insight}" for insight in insights])

    # Head-to-head
    if h2h:
        hw, aw, draws = _h2h_record(h2h, home_name)
        lines.append(f"\n**Head-to-Head ({len(h2h)} pertemuan terakhir):**")
        lines.append(f"{home_name} {hw} — {draws} imbang — {aw} {away_name}")
        last = h2h[0]
        lines.append(f"Pertemuan terakhir: {last['home']} vs {last['away']}  {last['score']}  ({last['date']})")

        if hw > aw + 1:
            lines.append(f"Secara historis {home_name} dominan dalam head-to-head ini.")
        elif aw > hw + 1:
            lines.append(f"Secara historis {away_name} dominan dalam head-to-head ini.")
        else:
            lines.append("Head-to-head kedua tim sangat seimbang.")

    # Perbandingan kekuatan
    home_wp = home_stats.get("weighted_points", 0)
    away_wp = away_stats.get("weighted_points", 0)
    lines.append(f"\n**Skor Kekuatan (Weighted Form):**")
    lines.append(f"{home_name}: {home_wp} poin  |  {away_name}: {away_wp} poin")

    wp_diff = home_wp - away_wp
    if wp_diff > 8:
        verdict = f"{home_name} jauh lebih dominan saat ini."
    elif wp_diff > 3:
        verdict = f"{home_name} unggul tipis dalam form terkini."
    elif wp_diff > -3:
        verdict = "Kedua tim dalam kondisi yang sangat seimbang — laga akan sangat kompetitif."
    elif wp_diff > -8:
        verdict = f"{away_name} sedikit lebih baik dalam form terkini."
    else:
        verdict = f"{away_name} jauh lebih dominan saat ini."
    lines.append(verdict)

    # Confidence & verdict
    confidence = _confidence_label(predicted_home, predicted_away, home_stats, away_stats)
    lines.append(f"\n**Prediksi Skor: {home_name} {predicted_home} - {predicted_away} {away_name}**")
    lines.append(f"Tingkat keyakinan prediksi: **{confidence}**")
    lines.append("_(Prediksi berbasis model Expected Goals dengan analisis form, pertahanan, keunggulan kandang, dan momentum tren.)_")

    return "\n".join(lines)


def generate_llm7_reasoning(
    home_name: str,
    away_name: str,
    home_results: list[dict],
    away_results: list[dict],
    h2h: list[dict],
    home_stats: dict,
    away_stats: dict,
    predicted_home: int,
    predicted_away: int,
    home_roster: list[dict] = None,
    away_roster: list[dict] = None,
) -> str:
    """Queries LLM7.io API with Mistral Codestral model to generate professional match analysis."""
    try:
        url = "https://api.llm7.io/v1/chat/completions"
        
        h_results_str = "\n".join([f"- Lawan {r['opponent']}: {r['score']} ({r['outcome']}) di {r['venue']}" for r in home_results])
        a_results_str = "\n".join([f"- Lawan {r['opponent']}: {r['score']} ({r['outcome']}) di {r['venue']}" for r in away_results])
        h2h_str = "\n".join([f"- {m['home']} vs {m['away']}: {m['score']} ({m['date']})" for m in h2h]) if h2h else "Tidak ada catatan pertemuan baru-baru ini."
        
        h_roster_str = ", ".join([f"{p['name']} ({p['position']})" for p in home_roster[:18]]) if home_roster else "Tidak ada data roster pemain."
        a_roster_str = ", ".join([f"{p['name']} ({p['position']})" for p in away_roster[:18]]) if away_roster else "Tidak ada data roster pemain."

        prompt = f"""
Anda adalah analis sepak bola profesional, pengamat taktis, dan jurnalis olahraga senior.
Tugas Anda adalah menulis ulasan analisis pertandingan yang sangat mendalam, taktis, objektif, dan berbobot dalam Bahasa Indonesia.
PENTING: Jangan gunakan emoji dalam ulasan Anda (maksimal hanya boleh 1 emoji di seluruh ulasan). Tulis dengan nada bahasa jurnalistik yang formal, analitis, dan profesional.
PENTING: Tulis ulasan secara padat, ringkas, langsung pada intinya, dan hindari penjelasan bertele-tele. Tulis maksimal 2-3 paragraf singkat.

[Data Statistik Pertandingan]
Tim Tuan Rumah: {home_name}
Tim Tamu: {away_name}

Laga Terakhir {home_name}:
{h_results_str}
Statistik {home_name}: Rata-rata gol dicetak {home_stats.get('avg_scored')}, kebobolan {home_stats.get('avg_conceded')}. Streak menang: {home_stats.get('win_streak')}, Clean sheet: {home_stats.get('clean_sheets')}.

Laga Terakhir {away_name}:
{a_results_str}
Statistik {away_name}: Rata-rata gol dicetak {away_stats.get('avg_scored')}, kebobolan {away_stats.get('avg_conceded')}. Streak menang: {away_stats.get('win_streak')}, Clean sheet: {away_stats.get('clean_sheets')}.

Catatan Head-to-Head (H2H):
{h2h_str}

Skuad Pemain Utama {home_name}: {h_roster_str}
Skuad Pemain Utama {away_name}: {a_roster_str}

Prediksi Skor Matematis (Poisson Engine): {home_name} {predicted_home} - {predicted_away} {away_name}

[Struktur Output]
Tulis ulasan Anda dengan membaginya ke dalam 3 poin berikut:
1. **Analisis Taktis & Form Terkini**: Penjelasan performa terkini kedua tim. PENTING: Anda harus menyebutkan/merujuk 1-2 nama pemain kunci dari daftar Skuad Pemain Utama di atas dan peran taktis mereka.
2. **Kunci Pertandingan & Analisis Venue**: Bahas detail performa kandang vs tandang, pertahanan vs serangan, dan pengaruh keunggulan stadion.
3. **Prediksi Skor & Verdict**: Berikan penjelasan taktis dan logis yang membenarkan mengapa skor akhir diprediksi berkisar {predicted_home} - {predicted_away} (Anda dapat menyetujui atau menyesuaikan tipis skor prediksi ini berdasarkan analisis taktis Anda).
"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer unused"
        }
        # Try Qwen3-235B
        try:
            payload = {
                "model": "qwen3-235b",
                "messages": [
                    {"role": "user", "content": prompt.strip()}
                ],
                "temperature": 0.5
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content.strip():
                        print("[LLM7 Engine] Successfully used Qwen3-235B model.")
                        return content.strip()
        except Exception as qwen_err:
            print(f"[LLM7 Engine] Qwen3-235B failed: {qwen_err}. Falling back to codestral...")

        # Fallback to Mistral Codestral
        payload = {
            "model": "codestral-latest",
            "messages": [
                {"role": "user", "content": prompt.strip()}
            ],
            "temperature": 0.5
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content.strip():
                    print("[LLM7 Engine] Successfully used codestral-latest model.")
                    return content.strip()
    except Exception as e:
        print(f"[LLM7 Engine] Error: {e}")
    return ""


def generate_pollinations_get_reasoning(
    home_name: str,
    away_name: str,
    home_results: list[dict],
    away_results: list[dict],
    h2h: list[dict],
    home_stats: dict,
    away_stats: dict,
    predicted_home: int,
    predicted_away: int,
    home_roster: list[dict] = None,
    away_roster: list[dict] = None,
) -> str:
    """Queries Pollinations GET text API to generate professional match analysis."""
    try:
        h_results_str = "\n".join([f"- Lawan {r['opponent']}: {r['score']} ({r['outcome']}) di {r['venue']}" for r in home_results])
        a_results_str = "\n".join([f"- Lawan {r['opponent']}: {r['score']} ({r['outcome']}) di {r['venue']}" for r in away_results])
        h2h_str = "\n".join([f"- {m['home']} vs {m['away']}: {m['score']} ({m['date']})" for m in h2h]) if h2h else "Tidak ada catatan pertemuan baru-baru ini."
        
        h_roster_str = ", ".join([f"{p['name']} ({p['position']})" for p in home_roster[:15]]) if home_roster else "Tidak ada data roster pemain."
        a_roster_str = ", ".join([f"{p['name']} ({p['position']})" for p in away_roster[:15]]) if away_roster else "Tidak ada data roster pemain."

        prompt = f"""
Anda adalah analis sepak bola profesional, pengamat taktis, dan jurnalis olahraga senior.
Tugas Anda adalah menulis ulasan analisis pertandingan yang sangat mendalam, taktis, objektif, dan berbobot dalam Bahasa Indonesia.
PENTING: Jangan gunakan emoji dalam ulasan Anda (maksimal hanya boleh 1 emoji di seluruh ulasan). Tulis dengan nada bahasa jurnalistik yang formal, analitis, dan profesional.
PENTING: Tulis ulasan secara padat, ringkas, langsung pada intinya, dan hindari penjelasan bertele-tele. Tulis maksimal 2-3 paragraf singkat.

[Data Statistik Pertandingan]
Tim Tuan Rumah: {home_name}
Tim Tamu: {away_name}

Laga Terakhir {home_name}:
{h_results_str}
Statistik {home_name}: Rata-rata gol dicetak {home_stats.get('avg_scored')}, kebobolan {home_stats.get('avg_conceded')}.

Laga Terakhir {away_name}:
{a_results_str}
Statistik {away_name}: Rata-rata gol dicetak {away_stats.get('avg_scored')}, kebobolan {away_stats.get('avg_conceded')}.

Catatan Head-to-Head (H2H):
{h2h_str}

Skuad Pemain Utama {home_name}: {h_roster_str}
Skuad Pemain Utama {away_name}: {a_roster_str}

Prediksi Skor Matematis (Poisson Engine): {home_name} {predicted_home} - {predicted_away} {away_name}

[Struktur Output]
Tulis ulasan Anda dengan membaginya ke dalam 3 poin berikut:
1. **Analisis Taktis & Form Terkini**: Penjelasan performa terkini kedua tim. PENTING: Sebutkan 1-2 nama pemain kunci dari Skuad Pemain Utama di atas dan peran taktis mereka.
2. **Kunci Pertandingan & Analisis Venue**: Bahas detail performa kandang vs tandang, pertahanan vs serangan, dan pengaruh keunggulan stadion.
3. **Prediksi Skor & Verdict**: Berikan penjelasan taktis dan logis yang membenarkan mengapa skor akhir diprediksi berkisar {predicted_home} - {predicted_away}.
"""
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [
                {"role": "user", "content": prompt.strip()}
            ],
            "model": "openai"
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200 and resp.text.strip():
            print("[Pollinations Engine] Successfully used openai model.")
            return resp.text.strip()
    except Exception as e:
        print(f"[Pollinations Engine] Error: {e}")
    return ""


def generate_gemini_reasoning(
    api_key: str,
    home_name: str,
    away_name: str,
    home_results: list[dict],
    away_results: list[dict],
    h2h: list[dict],
    home_stats: dict,
    away_stats: dict,
    predicted_home: int,
    predicted_away: int,
    home_roster: list[dict] = None,
    away_roster: list[dict] = None,
) -> str:
    """Queries Google Gemini API to generate professional match analysis."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        h_results_str = "\n".join([f"- Lawan {r['opponent']}: {r['score']} ({r['outcome']}) di {r['venue']}" for r in home_results])
        a_results_str = "\n".join([f"- Lawan {r['opponent']}: {r['score']} ({r['outcome']}) di {r['venue']}" for r in away_results])
        h2h_str = "\n".join([f"- {m['home']} vs {m['away']}: {m['score']} ({m['date']})" for m in h2h]) if h2h else "Tidak ada catatan pertemuan baru-baru ini."
        
        h_roster_str = ", ".join([f"{p['name']} ({p['position']})" for p in home_roster[:18]]) if home_roster else "Tidak ada data roster pemain."
        a_roster_str = ", ".join([f"{p['name']} ({p['position']})" for p in away_roster[:18]]) if away_roster else "Tidak ada data roster pemain."

        prompt = f"""
Anda adalah analis sepak bola profesional, pengamat taktis, dan jurnalis olahraga senior.
Tugas Anda adalah menulis ulasan analisis pertandingan yang sangat mendalam, taktis, objektif, dan berbobot dalam Bahasa Indonesia.
PENTING: Jangan gunakan emoji dalam ulasan Anda (maksimal hanya boleh 1 emoji di seluruh ulasan). Tulis dengan nada bahasa jurnalistik yang formal, analitis, dan profesional.
PENTING: Tulis ulasan secara padat, ringkas, langsung pada intinya, dan hindari penjelasan bertele-tele. Tulis maksimal 2-3 paragraf singkat.

[Data Statistik Pertandingan]
Tim Tuan Rumah: {home_name}
Tim Tamu: {away_name}

Laga Terakhir {home_name}:
{h_results_str}
Statistik {home_name}: Rata-rata gol dicetak {home_stats.get('avg_scored')}, kebobolan {home_stats.get('avg_conceded')}. Streak menang: {home_stats.get('win_streak')}, Clean sheet: {home_stats.get('clean_sheets')}.

Laga Terakhir {away_name}:
{a_results_str}
Statistik {away_name}: Rata-rata gol dicetak {away_stats.get('avg_scored')}, kebobolan {away_stats.get('avg_conceded')}. Streak menang: {away_stats.get('win_streak')}, Clean sheet: {away_stats.get('clean_sheets')}.

Catatan Head-to-Head (H2H):
{h2h_str}

Skuad Pemain Utama {home_name}: {h_roster_str}
Skuad Pemain Utama {away_name}: {a_roster_str}

Prediksi Skor Matematis (Poisson Engine): {home_name} {predicted_home} - {predicted_away} {away_name}

[Struktur Output]
Tulis ulasan Anda dengan membaginya ke dalam 3 poin berikut:
1. **Analisis Taktis & Form Terkini**: Penjelasan performa terkini kedua tim. PENTING: Anda harus menyebutkan/merujuk 1-2 nama pemain kunci dari Skuad Pemain Utama di atas dan peran taktis mereka.
2. **Kunci Pertandingan & Analisis Venue**: Bahas detail performa kandang vs tandang, pertahanan vs serangan, dan pengaruh keunggulan stadion.
3. **Prediksi Skor & Verdict**: Berikan penjelasan taktis dan logis yang membenarkan mengapa skor akhir diprediksi berkisar {predicted_home} - {predicted_away} (Anda dapat menyetujui atau menyesuaikan tipis skor prediksi ini berdasarkan analisis taktis Anda).
"""
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt.strip()}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 1000
            }
        }
        
        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    if text.strip():
                        return text.strip()
    except Exception as e:
        print(f"[Gemini Engine] Error: {e}")
    return ""


# ---------- Chat & Predict Endpoints ----------

@app.post("/chat")
async def chat(req: ChatRequest, request: Request, current_user: dict = Depends(get_current_user)):
    check_rate_limit(request, "chat")

    message = req.message.strip()
    extracted = extract_teams_and_date(message)

    if extracted["confidence"] == "low" or not extracted["home_team"]:
        return {
            "reply": (
                "Maaf, saya tidak bisa mendeteksi nama tim dari pesanmu.\n\n"
                "Coba format seperti ini:\n"
                "- Chelsea vs Arsenal besok\n"
                "- Prediksi skor Barcelona lawan Real Madrid\n"
                "- Siapa yang menang Liverpool vs Man City malam ini?"
            ),
            "extracted": extracted,
            "data_source": None,
            "credits_remaining": current_user["credits"],
        }

    credits = current_user["credits"]
    if credits != UNLIMITED and credits <= 0:
        raise HTTPException(
            status_code=402,
            detail="Kredit habis! Kamu sudah menggunakan semua 5 kredit prediksi.",
        )

    home_name = extracted["home_team"]
    away_name = extracted["away_team"]
    match_date = extracted.get("date", "")

    home_data = fetch_team_data(home_name)
    away_data = fetch_team_data(away_name)

    h2h = get_h2h(home_data, away_data)

    home_stats = home_data.get("stats", calculate_team_stats(home_data.get("last_results", [])))
    away_stats = away_data.get("stats", calculate_team_stats(away_data.get("last_results", [])))
    home_stats["name"] = home_data.get("name", home_name)
    away_stats["name"] = away_data.get("name", away_name)
    predicted_home, predicted_away, home_xg, away_xg = predict_score(home_stats, away_stats, h2h=h2h)
    betting_markets = calculate_betting_markets(home_xg, away_xg)

    actual_home = home_data.get("name", home_name)
    actual_away = away_data.get("name", away_name)

    if not home_data.get("found") or not away_data.get("found"):
        missing = []
        if not home_data.get("found"):
            missing.append(home_name)
        if not away_data.get("found"):
            missing.append(away_name)
        return {
            "reply": (
                f"Maaf, tidak bisa menemukan data untuk: **{', '.join(missing)}**.\n\n"
                "Coba gunakan nama tim yang lebih lengkap, misalnya Manchester United atau FC Barcelona."
            ),
            "extracted": extracted,
            "data_source": "ESPN Public API",
            "credits_remaining": credits,
        }

    # Deduct credit AFTER successful data fetch
    new_credits = deduct_credit(current_user["id"])

    api_key = request.headers.get("x-gemini-key") or os.environ.get("GEMINI_API_KEY")
    ai_generated = False
    reasoning = ""
    
    if api_key:
        print("[AI Engine] Querying Google Gemini API...")
        reasoning = generate_gemini_reasoning(
            api_key,
            actual_home, actual_away,
            home_data.get("last_results", []),
            away_data.get("last_results", []),
            h2h,
            home_stats,
            away_stats,
            predicted_home, predicted_away,
            home_roster=home_data.get("roster", []),
            away_roster=away_data.get("roster", []),
        )
        if reasoning:
            ai_generated = True
            
    if not reasoning:
        print("[AI Engine] Querying LLM7 Codestral Engine...")
        reasoning = generate_llm7_reasoning(
            actual_home, actual_away,
            home_data.get("last_results", []),
            away_data.get("last_results", []),
            h2h,
            home_stats,
            away_stats,
            predicted_home, predicted_away,
            home_roster=home_data.get("roster", []),
            away_roster=away_data.get("roster", []),
        )
        if reasoning:
            ai_generated = True

    if not reasoning:
        print("[AI Engine] Querying Pollinations GET Engine...")
        reasoning = generate_pollinations_get_reasoning(
            actual_home, actual_away,
            home_data.get("last_results", []),
            away_data.get("last_results", []),
            h2h,
            home_stats,
            away_stats,
            predicted_home, predicted_away,
            home_roster=home_data.get("roster", []),
            away_roster=away_data.get("roster", []),
        )
        if reasoning:
            ai_generated = True
            
    if not reasoning:
        print("[AI Engine] Falling back to local rules-based engine...")
        reasoning = build_reasoning(
            actual_home, actual_away,
            home_data.get("last_results", []),
            away_data.get("last_results", []),
            h2h,
            home_stats,
            away_stats,
            predicted_home, predicted_away,
        )

    data_points = {
        "home_team": {
            "name": actual_home,
            "league": home_data.get("league", ""),
            "badge": home_data.get("badge", ""),
            "strength": home_stats.get("weighted_points", 0),
            "last_results": home_data.get("last_results", []),
            "stats": home_stats,
            "roster": home_data.get("roster", []),
        },
        "away_team": {
            "name": actual_away,
            "league": away_data.get("league", ""),
            "badge": away_data.get("badge", ""),
            "strength": away_stats.get("weighted_points", 0),
            "last_results": away_data.get("last_results", []),
            "stats": away_stats,
            "roster": away_data.get("roster", []),
        },
        "h2h": h2h,
        "prediction": {
            "home_score": predicted_home,
            "away_score": predicted_away,
            "score_str": f"{predicted_home}-{predicted_away}",
            "betting_markets": betting_markets,
        },
        "match_date": match_date,
    }

    reply = (
        f"Berikut analisis pertandingan **{actual_home}** vs **{actual_away}**"
        + (f" ({match_date})" if match_date else "")
        + ":\n\n"
        + reasoning
    )

    return {
        "reply": reply,
        "extracted": extracted,
        "data": data_points,
        "data_source": "ESPN Public API (gratis, tanpa API key)",
        "credits_remaining": new_credits,
        "ai_generated_by_server": ai_generated,
    }


@app.post("/predict")
async def predict(req: PredictRequest, request: Request, current_user: dict = Depends(get_current_user)):
    check_rate_limit(request, "predict")
    
    credits = current_user["credits"]
    if credits != UNLIMITED and credits <= 0:
        raise HTTPException(status_code=402, detail="Kredit habis!")
        
    home_data = fetch_team_data(req.home_team)
    away_data = fetch_team_data(req.away_team)
    h2h = get_h2h(home_data, away_data)
    
    home_stats = home_data.get("stats", calculate_team_stats(home_data.get("last_results", [])))
    away_stats = away_data.get("stats", calculate_team_stats(away_data.get("last_results", [])))
    home_stats["name"] = home_data.get("name", req.home_team)
    away_stats["name"] = away_data.get("name", req.away_team)
    
    predicted_home, predicted_away, home_xg, away_xg = predict_score(home_stats, away_stats, h2h=h2h)
    betting_markets = calculate_betting_markets(home_xg, away_xg)
    new_credits = deduct_credit(current_user["id"])
    
    return {
        "home_team": home_data,
        "away_team": away_data,
        "h2h": h2h,
        "prediction": {
            "home_score": predicted_home,
            "away_score": predicted_away,
            "score_str": f"{predicted_home}-{predicted_away}",
            "betting_markets": betting_markets,
        },
        "credits_remaining": new_credits,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
