import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from nlp_extractor import extract_teams_and_date
from data_fetcher import fetch_team_data, get_h2h, predict_score

app = FastAPI(title="BolaMistis AI API", root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class PredictRequest(BaseModel):
    home_team: str
    away_team: str
    date: str | None = None


def build_reasoning(
    home_name: str,
    away_name: str,
    home_results: list[dict],
    away_results: list[dict],
    h2h: list[dict],
    home_strength: int,
    away_strength: int,
    predicted_home: int,
    predicted_away: int,
) -> str:
    lines = []

    if home_results:
        last = home_results[0]
        outcome_word = {"W": "menang", "D": "seri", "L": "kalah"}.get(last["outcome"], "bermain")
        lines.append(
            f"{home_name} terakhir {outcome_word} {last['score']} melawan {last['opponent']} ({last['date']})."
        )

    wins_h = sum(1 for r in home_results if r["outcome"] == "W")
    draws_h = sum(1 for r in home_results if r["outcome"] == "D")
    losses_h = sum(1 for r in home_results if r["outcome"] == "L")
    if home_results:
        lines.append(
            f"Dalam {len(home_results)} laga terakhir, {home_name}: {wins_h}M {draws_h}S {losses_h}K (kekuatan: {home_strength} poin)."
        )

    wins_a = sum(1 for r in away_results if r["outcome"] == "W")
    draws_a = sum(1 for r in away_results if r["outcome"] == "D")
    losses_a = sum(1 for r in away_results if r["outcome"] == "L")
    if away_results:
        lines.append(
            f"Dalam {len(away_results)} laga terakhir, {away_name}: {wins_a}M {draws_a}S {losses_a}K (kekuatan: {away_strength} poin)."
        )

    if h2h:
        h = h2h[0]
        lines.append(
            f"Head-to-head terakhir: {h['home']} vs {h['away']} skor {h['score']} ({h['date']})."
        )

    diff = home_strength - away_strength
    if diff > 5:
        lines.append(f"{home_name} jauh lebih kuat saat ini (selisih {diff} poin), diprediksi menang cukup telak.")
    elif diff > 0:
        lines.append(f"{home_name} sedikit lebih unggul (selisih {diff} poin), diprediksi menang tipis.")
    elif diff == 0:
        lines.append("Kedua tim setara kekuatannya, pertandingan diprediksi ketat.")
    elif diff > -5:
        lines.append(f"{away_name} sedikit lebih kuat (selisih {abs(diff)} poin), diprediksi menang tipis.")
    else:
        lines.append(f"{away_name} jauh lebih kuat saat ini (selisih {abs(diff)} poin).")

    lines.append(
        f"\nPrediksi Skor: {home_name} {predicted_home} - {predicted_away} {away_name}"
    )

    return "\n".join(lines)


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        return JSONResponse(
            {"reply": "Hei! Tanyakan prediksi pertandingan seperti: Chelsea vs Arsenal besok"},
            status_code=400,
        )

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
        }

    home_name = extracted["home_team"]
    away_name = extracted["away_team"]
    match_date = extracted.get("date", "")

    home_data = fetch_team_data(home_name)
    away_data = fetch_team_data(away_name)

    h2h = get_h2h(home_data, away_data)

    home_strength = home_data.get("strength", 0)
    away_strength = away_data.get("strength", 0)
    predicted_home, predicted_away = predict_score(home_strength, away_strength)

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
        }

    reasoning = build_reasoning(
        actual_home, actual_away,
        home_data.get("last_results", []),
        away_data.get("last_results", []),
        h2h,
        home_strength, away_strength,
        predicted_home, predicted_away,
    )

    data_points = {
        "home_team": {
            "name": actual_home,
            "league": home_data.get("league", ""),
            "badge": home_data.get("badge", ""),
            "strength": home_strength,
            "last_results": home_data.get("last_results", []),
        },
        "away_team": {
            "name": actual_away,
            "league": away_data.get("league", ""),
            "badge": away_data.get("badge", ""),
            "strength": away_strength,
            "last_results": away_data.get("last_results", []),
        },
        "h2h": h2h,
        "prediction": {
            "home_score": predicted_home,
            "away_score": predicted_away,
            "score_str": f"{predicted_home}-{predicted_away}",
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
    }


@app.post("/predict")
async def predict(req: PredictRequest):
    home_data = fetch_team_data(req.home_team)
    away_data = fetch_team_data(req.away_team)
    h2h = get_h2h(home_data, away_data)
    home_strength = home_data.get("strength", 0)
    away_strength = away_data.get("strength", 0)
    predicted_home, predicted_away = predict_score(home_strength, away_strength)
    return {
        "home_team": home_data,
        "away_team": away_data,
        "h2h": h2h,
        "prediction": {
            "home_score": predicted_home,
            "away_score": predicted_away,
            "score_str": f"{predicted_home}-{predicted_away}",
        },
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
