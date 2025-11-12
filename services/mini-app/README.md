# maxOn mini-app

Single Page Application for the MAX mini-app platform. The UI mimics the dark look & feel described in the product brief and works entirely on mock data so it can be integrated before the backend is ready.

## Available scripts

```bash
npm install
npm run dev
npm run build
npm run preview
```

## Environment

Use `.env` (see `.env.example`) to configure the `VITE_MAX_WEB_APP_SRC` pointing to the hosted `max-web-app.js`. The SDK is loaded lazily and the init data is stored inside the `MaxAppContext`.

## Docker

```
docker build -t maxon-mini-app services/mini-app
docker run -p 4173:4173 maxon-mini-app
```

## Structure

- `src/app` — app shell & layout
- `src/features` — domain-oriented sections (today, calendar, goals, leaderboard, chat)
- `src/services` — abstraction for chat/max integrations
- `src/mocks` — placeholder data structures
- `src/store` — React contexts for app + chat state

Each feature has clear entry components so wiring real APIs later is straightforward.

