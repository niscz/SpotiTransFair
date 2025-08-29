# SpotiTransFair

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: GNU GPLv3](https://img.shields.io/badge/License-GNU_GPLv3-yellow.svg?style=for-the-badge)](https://www.gnu.org/licenses/)

Transfer your Spotify playlists to YouTube Music with a secure, high-performance, and self-hostable application.

<!-- Replace with a screenshot or GIF of the app -->
![SpotiTransFair Screenshot](./githubcontent/screenshot.png)

## 🚀 Key Features

-   **Seamless Playlist Transfer**: Convert any public Spotify playlist to a new YouTube Music playlist.
-   **Fast & Efficient**: Utilizes parallel processing to search for tracks, making transfers incredibly fast, even for large playlists.
-   **Private & Secure**: Creates playlists as "Private" on your YouTube Music account by default.
-   **Detailed Reporting**: Get a list of any tracks that couldn't be found on YouTube Music.
-   **Dockerized for Easy Deployment**: Get the entire application (Frontend + Backend) running with a single command.
-   **Modern Tech Stack**: Built with React, TypeScript, Flask, and a high-performance ASGI server setup.

## 🌱 Project Evolution: From Concept to Production-Ready

This project is a heavily refactored, secured, and dockerized version of the original concept from the [SpotTransfer](https://github.com/Pushan2005/SpotTransfer) repository by **[Pushan2005](https://github.com/Pushan2005)**. We extend our sincere thanks to him for the initial groundwork.

Our goal was to take this great idea and re-engineer it into a robust, scalable, and secure application that follows modern DevOps and software engineering best practices.

### Key Improvements Made

-   **🚀 Performance Overhaul**:
    -   **Asynchronous Architecture**: Replaced the original synchronous Flask development server with a production-grade Gunicorn setup using modern `Uvicorn` workers. This allows the server to handle many concurrent requests without blocking.
    -   **Parallel Track Searching**: Implemented `concurrent.futures` in the backend to search for all playlist tracks on YouTube Music simultaneously, drastically reducing the total processing time from minutes to mere seconds for large playlists.

-   **🛡️ Security Hardening**:
    -   **Solved Critical Race Condition**: Eliminated the critical bug where simultaneous user requests could result in playlists being created on the wrong accounts by removing shared file-based authentication.
    -   **Secure In-Memory Handling**: User authentication headers are now handled securely in-memory for each request and are never written to the server's disk.
    -   **Robust Error Handling**: Replaced generic error responses with a secure system that logs detailed errors on the server while showing user-friendly, safe messages on the client, preventing internal detail leaks.

-   **🐳 Full Dockerization & DevOps**:
    -   **One-Command Setup**: The entire application, consisting of a React frontend and a Python backend, is containerized and managed with Docker Compose for an incredibly simple setup.
    -   **Multi-Stage Dockerfiles**: Implemented multi-stage builds for both frontend and backend, resulting in minimal, optimized, and more secure production images.
    -   **Nginx Reverse Proxy**: Deployed a production-standard Nginx reverse proxy within the frontend container. This correctly serves the React application and securely routes API traffic to the backend, solving all cross-origin (CORS) and network-related issues.

-   **🔧 Code Quality & Stability**:
    -   **Complete Refactor**: The backend Python code was refactored to be more modular, maintainable, and robust, including the creation of dedicated API client classes.
    -   **Bug Squashing Marathon**: Solved numerous infrastructure bugs.
    -   **Frontend Consistency**: Ensured a consistent and professional user experience.

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
-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

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

1.  **Get Your Auth Headers**: The application will guide you through the process of getting your authentication headers from your browser's developer tools while you are logged into YouTube Music.
2.  **Provide Spotify Playlist**: Paste the public URL of the Spotify playlist you want to transfer.
3.  **Connect & Clone**: Click "Connect" to ensure the backend is running, then click "Clone Playlist" to start the transfer.
4.  **Done!**: The playlist will be created in your YouTube Music account.

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

-   **Backend**: Python, Flask, Gunicorn, Uvicorn
-   **Frontend**: React, TypeScript, Vite, TailwindCSS
-   **APIs**: Spotify Web API, `ytmusicapi` (unofficial YouTube Music API)
-   **Deployment**: Docker, Docker Compose, Nginx

## 📄 License

This project is licensed under the **GNU General Public License v3.0**. As a derivative work of the original [SpotTransfer project](https://github.com/Pushan2005/SpotTransfer), it inherits the GPL-3.0 license. See the [LICENSE](LICENSE) file for the full license text.

## 🙏 Acknowledgments

-   A big thank you to **[Pushan2005](https://github.com/Pushan2005)** for creating the [original SpotTransfer project](https://github.com/Pushan2005/SpotTransfer) that inspired this enhanced version.