# SpotiTransFair

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: GNU GPLv3](https://img.shields.io/badge/License-GNU_GPLv3-yellow.svg?style=for-the-badge)](https://www.gnu.org/licenses/)

Transfer your Spotify playlists to YouTube Music with a secure, high-performance, and self-hostable application.

![SpotiTransFair Screenshot](./githubcontent/screenshot.png)

## 🚀 Key Features

-   **Seamless Playlist Transfer**: Convert any public Spotify playlist to a new YouTube Music playlist.
-   **Fast & Efficient**: Parallelized track searches drastically cut transfer time. Tracks are added to YouTube Music in batches (default 100) for resiliency.
-   **Private & Secure by Design**: 
    -   Playlists default to PRIVATE (you can choose UNLISTED or PUBLIC).
    -   Your YouTube Music auth headers are processed in-memory per request and never written to disk.
-   **Region-Aware Market Selection**: UI preselects the market (e.g., US, DE, GB) based on your region (best-effort) — you can override it at any time.
-   **Detailed Reporting**: Get a “missed tracks” dialog if some songs weren’t found.
-   **Health Check & UX niceties**:
    -   One-click Connect button tests backend availability.
    -   Clear, user-friendly error dialogs with actionable hints.
-   **Dockerized for Easy Deployment**: One command to bring up Frontend + Backend with Nginx reverse proxy.
-   **Modern Tech Stack**: React + TypeScript frontend; Python backend served with Gunicorn + Uvicorn (ASGI).

## 🌱 Project Evolution: From Concept to Production-Ready

This project is a heavily refactored, secured, and dockerized version of the original concept from the [SpotTransfer](https://github.com/Pushan2005/SpotTransfer) repository by **[Pushan2005](https://github.com/Pushan2005)**.

The goal was to take this great idea and re-engineer it into a robust, scalable, and secure application that follows modern DevOps and software engineering best practices.

### Key Improvements Made

-   **🚀 Performance Overhaul**:
    -   **Asynchronous/Concurrent processing** for YouTube Music searches.
    -   **Batched adds**: to playlists (default 100 per request) for better stability and fewer transient API failures.

-   **🛡️ Security Hardening**:
    -   **Eliminated shared file-based auth** → no cross-user leakage.
    -   **Per-request, in-memory handling of headers**; sensitive data never persisted.
    -   **Non-Root**: Containers run as non-root users.

-   **🧭 API Ergonomics & UX**:
    -   **Market selector** in UI (default based on region).
    -   **Privacy selector** in UI (default PRIVATE).
    -   /api health endpoint + “Connect” button in UI.  
    -   Clear, consistent success and error dialogs; improved empty/timeout states.

-   **🔧 Code Quality & Stability**:
    -   **Complete Refactor** for clarity, stricter typing, and graceful fallbacks..
    -   **Bug Squashing Marathon**: Solved numerous infrastructure bugs.
    -   **Frontend Consistency**: Small tidy-ups across UI copy, validation, and dialogs.

-   **🐳 Full Dockerization & DevOps**:
    -   **One-Command Setup**: The entire application, consisting of a React frontend and a Python backend, is containerized and managed with Docker Compose for an incredibly simple setup.
    -   **Multi-Stage Dockerfiles**: Implemented multi-stage builds for both frontend and backend, resulting in minimal, optimized, and more secure production images.
    -   **Nginx Reverse Proxy**: Deployed a production-standard Nginx reverse proxy within the frontend container. This correctly serves the React application and securely routes API traffic to the backend, solving all cross-origin (CORS) and network-related issues.
    -   **Gunicorn/Uvicorn**: Production Gunicorn config with Uvicorn workers.


## 🤔 Why a Header-Based Approach? A Note on APIs

A common question is, "Why not use the official YouTube API with a simple OAuth login?"

The official way to interact with YouTube is through the **YouTube Data API v3**. While this API is excellent, its free tier is governed by a strict quota system.

-   **Daily Quota**: 10,000 units per day.
-   **Cost of Operations**:
    -   A single song search (`search.list`): **100 units**
    -   Adding a single song to a playlist (`playlistItems.insert`): **50 units**

Let's do the math for a **single 50-song playlist**:
-   **Searching**: 50 songs * 100 units/search = 5,000 units
-   **Adding**: 50 songs * 50 units/add = 2,500 units
-   **Total**: **7,500 units**

Transferring just one small playlist consumes 75% of the entire daily free quota. This makes it impossible to offer a reliable, free public service.

This header-based approach, while less user-friendly upfront, allows **SpotiTransFair** to remain a completely free and unlimited service for everyone.

## 🛠️ Getting Started (Installation)

With Docker, getting SpotiTransFair running on your local machine is incredibly simple.

### Prerequisites

-   [Git](https://git-scm.com/)
-   [Docker](https://www.docker.com/get-started) (Docker Compose included in Desktop; on Linux install Compose if needed)

### 1. Clone the Repository

```bash
git clone https://github.com/niscz/SpotiTransFair.git
cd SpotiTransFair
```

### 2. Configure Environment Variables

You need to provide your own Spotify API credentials.

1.  **Create a `.env` file** by copying the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Get Spotify Credentials**:
    -   Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
    -   Create a new App.
    -   You will find your `Client ID` and `Client Secret` there.

3.  **Edit the `.env` file** and add your credentials:
    ```env
    SPOTIPY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID
    SPOTIPY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET
    ```

### 3. Build and Run with Docker Compose

This single command will build the production-ready frontend and backend images and start both services.

```bash
docker-compose up --build
```

The first time you run this, it will download the necessary base images and install all dependencies. Subsequent runs will be much faster.

### 4. Access the Application

Once the containers are running, open your web browser and navigate to:

**➡️ `http://localhost:5173`**

## 📖 How to Use the App

1.  **Sign in to YouTube Music** in your browser [Youtube Music](https://music.youtube.com).
2.  **Get Auth Headers** (the UI has a step-by-step guide):
    -   Open DevTools → Network → filter /browse (POST, 200).
    -   Copy the **Request Headers** and paste them into the app.
3.  **Provide Spotify Playlist**: Paste the public URL of the Spotify playlist you want to transfer.
4.  **Pick options**:
    -   **Market**: defaults to a best-effort region guess; override if needed (e.g., US, DE, GB).
    -   **Privacy**: **PRIVATE** (default), **UNLISTED**, or **PUBLIC**.
5.  **Connect & Clone**: Click "Connect" to ensure the backend is running, then click "Clone Playlist" to start the transfer.
6.  **Done!**: The playlist will be created in your YouTube Music account. If we can’t find some songs, you’ll get a **missed tracks** list.

## ⚙️ Configuration & Behavior

-   **Batches**: Tracks are added in chunks of **100** (configurable in code) to reduce failures and speed up large transfers.
-   **Market**: Affects search results (e.g., region-specific availability).
-   **Privacy**: Controls the resulting YouTube Music playlist visibility.
-   **Security**:
    -   Headers are never logged or persisted.
    -   Containers run as non-root (appuser) in production stages.
-   **Health Check**:
    -   GET /api/ returns a simple JSON if the backend is up.
    -   The UI’s Connect button calls this endpoint.

## 🧪 API (for self-hosters / integrators)

-   **Health**: GET /api/
    -   Response: { "status": "ok" }

-   **Create Playlist**: POST /api/create
    -   Body:
        ```json
        {
        "playlist_link": "https://open.spotify.com/playlist/...",
        "auth_headers": "accept: */*\n... (full raw request headers) ...",
        "market": "US",
        "privacy_status": "PRIVATE"
        }
        ```
    -   Response (example):
        ```json
        {
        "playlist_id": "PLxxxxxxxxxxxx",
        "name": "My Migrated Playlist",
        "missed_tracks": { "count": 2, "tracks": ["Artist – Title", "…"] }
        }
        ```

    ***cURL example***
    ```bash
    curl -X POST http://localhost:5173/api/create \
        -H "Content-Type: application/json" \
        -d '{
            "playlist_link": "https://open.spotify.com/playlist/...",
            "auth_headers": "accept: */*\n...paste raw request headers here...",
            "market": "US",
            "privacy_status": "PRIVATE"
        }'
    ```

## 📂 Project Structure

```
SpotiTransFair/
├── backend
│   ├── Dockerfile
│   ├── config
│   │   └── gunicorn.conf.py
│   ├── main.py
│   ├── requirements.txt
│   ├── spotify.py
│   └── ytm.py
│
├── frontend
│   ├── Dockerfile
│   ├── components.json
│   ├── eslint.config.js
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── postcss.config.js
│   ├── public
│   │   └── favicon.png
│   ├── src
│   │   ├── assets
│   │   │   ├── headers.png
│   │   │   └── react.svg
│   │   ├── components
│   │   │   ├── create-playlist
│   │   │   │   ├── get-headers.tsx
│   │   │   │   └── input-fields.tsx
│   │   │   ├── landing
│   │   │   │   ├── footer.tsx
│   │   │   │   ├── hero.tsx
│   │   │   │   └── how-to-use.tsx
│   │   │   ├── theme-provider.tsx
│   │   │   └── ui
│   │   │       ├── alert-dialog.tsx
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── check.tsx
│   │   │       ├── input.tsx
│   │   │       └── textarea.tsx
│   │   ├── context
│   │   │   └── playlist-context.tsx
│   │   ├── index.css
│   │   ├── lib
│   │   │   └── utils.ts
│   │   ├── main.tsx
│   │   ├── nav-bar.tsx
│   │   ├── pages
│   │   │   ├── App.tsx
│   │   │   ├── announcements.tsx
│   │   │   └── create-playlist.tsx
│   │   └── vite-env.d.ts
│   ├── tailwind.config.js
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vercel.json
│   └── vite.config.ts
├── .env.example
├── docker-compose.yml
└── README.MD
```

## 💻 Technology Stack

-   **Backend**: Python, Flask (app), Gunicorn + Uvicorn (ASGI workers)
-   **Frontend**: React, TypeScript, Vite, TailwindCSS
-   **APIs**: Spotify Web API, `ytmusicapi` (unofficial YouTube Music API)
-   **Deployment**: Docker, Docker Compose, Nginx reverse proxy

## 🧩 Known Limitations

-   Source playlists must be public on Spotify.
-   YouTube Music availability varies by market/region; choosing the right market can improve match rates.
-   Some tracks won’t have exact matches on YouTube Music (covers, regional variants, unavailable releases).

## 🆘 Troubleshooting

-   **“Connection Error” / 502 from** /api/
    Usually the backend failed to boot. If you’re running outside Docker, ensure:
    -   **Python 3.10+** (the code uses modern type hints like str | None).
        If you must use Python 3.9, replace unions with typing.Optional[...], or run via Docker which ships a compatible runtime.
-   **Timeouts on very large playlists**
    Try again; batching is enabled, but YouTube Music can rate-limit aggressively. Self-hosting generally improves reliability.

## 🔐 Security Notes

-   Auth headers are handled in-memory only and never persisted.
-   Containers run as non-root (appuser) in production stages (frontend & backend).
-   Nginx terminates requests and proxies /api/* internally to the backend to avoid CORS complexity.

## 📣 Announcements

Check the Announcements page in the app for the latest updates.

## 📄 License

This project is licensed under the **GNU General Public License v3.0**. As a derivative work of the original [SpotTransfer project](https://github.com/Pushan2005/SpotTransfer), it inherits the GPL-3.0 license. See the [LICENSE](LICENSE) file for the full license text.

## 🙏 Acknowledgments

-   Thanks to **[Pushan2005](https://github.com/Pushan2005)** for the original idea and repo [SpotTransfer project](https://github.com/Pushan2005/SpotTransfer).