# BolaMistis AI

Aplikasi web prediksi skor sepak bola berbasis chat. User ketik nama tim dan tanggal, sistem mencari data statistik nyata secara otomatis (tanpa API key) dan menghitung prediksi skor.

## Run & Operate

- `python3 /home/runner/workspace/artifacts/api-server/python/main.py` — run Python FastAPI backend (port 8080)
- `pnpm --filter @workspace/bolamistis run dev` — run React frontend
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- **Backend:** Python 3.11 + FastAPI + Uvicorn (menggantikan Express untuk artifact api-server)
- **Frontend:** React + Vite + Tailwind CSS + shadcn/ui (artifact: bolamistis)
- **Data Source:** ESPN Public API (gratis, tanpa API key) — 132 tim dari 12 liga dunia
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/api-server/python/main.py` — FastAPI app, endpoint `/api/chat` dan `/api/predict`
- `artifacts/api-server/python/data_fetcher.py` — ESPN API integration, team search, last results, H2H
- `artifacts/api-server/python/nlp_extractor.py` — NLP untuk ekstrak nama tim & tanggal dari teks bebas
- `artifacts/bolamistis/src/pages/ChatPage.tsx` — main chat UI
- `artifacts/bolamistis/src/components/PredictionCard.tsx` — prediction stats card
- `lib/api-spec/openapi.yaml` — OpenAPI spec (hanya endpoint Node.js /healthz)

## Architecture decisions

- Backend Python FastAPI berjalan di port 8080 (sama dengan artifact api-server Node.js yang diganti)
- Data fetching menggunakan ESPN Public API — tidak perlu API key, mendukung 130+ tim dari 12 liga
- NLP extraction menggunakan regex (tidak butuh model ML) — cukup untuk nama tim populer
- Prediction algorithm berbasis weighted form points: W=3, D=1, L=0 atas 5 laga terakhir
- React frontend call langsung ke `/api/chat` via fetch (bukan generated hooks karena backend Python)

## Product

- Chat interface mirip WhatsApp/ChatGPT
- User ketik "Chelsea vs Arsenal besok" → sistem fetch data ESPN → hitung prediksi → tampilkan:
  - Skor prediksi (misal: 1-0)
  - Data statistik 5 laga terakhir per tim
  - Head-to-head history
  - Comparison strength bar
  - Badge logo tim dari ESPN

## "The Challenge" — Solusi Data Gratis

**ESPN Public API** (`site.api.espn.com`) — GRATIS, tanpa API key, tanpa rate limit ketat:
- `GET /apis/site/v2/sports/soccer/{league}/teams` — daftar tim + logo
- `GET /apis/site/v2/sports/soccer/{league}/teams/{id}/schedule` — jadwal & hasil

Liga yang didukung: EPL, La Liga, Bundesliga, Serie A, Ligue 1, Liga Portugal, Eredivisie, Championship, Liga MX, Brasileirao, Liga Argentina, MLS.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- ESPN API mengembalikan `score` sebagai dict `{value: N}` atau string tergantung versi — code sudah handle keduanya
- Python backend dijalankan langsung via `python3 main.py`, bukan via pnpm
- Artifact api-server sekarang menjalankan Python bukan Node.js (artifact.toml sudah diupdate)
- Team index dibangun saat startup (12 API calls) — first request ~5-8 detik, setelahnya cepat

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
