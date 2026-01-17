# SpotiTransFair

[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: GNU GPLv3](https://img.shields.io/badge/License-GNU_GPLv3-yellow.svg?style=for-the-badge)](https://www.gnu.org/licenses/)
[![GitHub stars](https://img.shields.io/github/stars/niscz/SpotiTransFair?style=for-the-badge&logo=github&label=Star%20on%20GitHub)](https://github.com/niscz/SpotiTransFair)

Transfer your Spotify playlists to **YouTube Music** or **TIDAL** with a secure, high-performance, and self-hostable web application. SpotiTransFair features an interactive review process, detailed operational dashboard, and a robust background worker architecture.

## 🚀 Key Features

- **Multi-Provider Support**: Seamlessly migrate playlists from **Spotify** to **YouTube Music** or **TIDAL**.
- **Interactive Review Flow**:
  - **Match & Review**: Matches are found in the background. You can review uncertain matches or missing tracks before finalizing the import.
  - **Search Alternatives**: If a track isn't found automatically, search the target platform manually within the UI and select the correct match.
- **Persistent Connections**: Connect your Spotify, TIDAL, and YouTube Music accounts once. Credentials are securely stored, allowing for multiple imports without re-authenticating.
- **Ops Dashboard**: Monitor your import jobs with interactive charts showing status distribution, daily volume, provider mix, and match quality.
- **Privacy & Security**:
  - Self-hosted: You control your data.
  - YouTube Music headers are handled securely on your server.
- **Robust Architecture**: Built with **FastAPI** and **SQLModel**, using **Redis** and **RQ** for reliable background processing. Fully Dockerized for easy deployment.

## 🛠️ Getting Started

Run the entire stack (Backend, Worker, Postgres, Redis) with a single command using Docker Compose.

### Prerequisites

- [Docker](https://www.docker.com/get-started) & [Docker Compose](https://docs.docker.com/compose/install/)
- Spotify Developer Credentials (for Spotify access)
- TIDAL Developer Credentials (optional, if using TIDAL)

### 1. Clone the Repository

```bash
git clone https://github.com/niscz/SpotiTransFair.git
cd SpotiTransFair
```

### 2. Configure Environment Variables

1.  Create a `.env` file from the example:
    ```bash
    cp .env.example .env
    ```
2.  **Spotify**: Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/), create an App, and get your `Client ID` and `Client Secret`.
    - Set Redirect URI to: `http://localhost:8001/callback/spotify`
3.  **TIDAL** (Optional): If you plan to import to TIDAL, obtain your Client ID and Secret.
    - Set Redirect URI to: `http://localhost:8001/callback/tidal`
4.  Edit the `.env` file and add your credentials:

    ```env
    SPOTIPY_CLIENT_ID=your_spotify_client_id
    SPOTIPY_CLIENT_SECRET=your_spotify_client_secret

    # Optional: TIDAL Credentials
    TIDAL_CLIENT_ID=your_tidal_client_id
    TIDAL_CLIENT_SECRET=your_tidal_client_secret
    ```

### 3. Build and Run

```bash
docker-compose up --build
```

### 4. Access the Application

Open your browser and navigate to:
**➡️ `http://localhost:8001`**

## 📖 How to Use

1.  **Connect Accounts**: Go to the **Connect** page (`/connect`).
    -   **Spotify**: Login via OAuth.
    -   **TIDAL**: Login via OAuth (if using TIDAL).
    -   **YouTube Music**: Follow the on-screen instructions to paste your browser authentication headers.
2.  **Select Playlists**: Go to the **Playlists** page (`/playlists`). You will see your Spotify playlists. Select the ones you want to migrate and choose the target provider (TIDAL or YouTube Music).
3.  **Wait for Matching**: A background job will search for tracks on the target provider. You can monitor progress on the Dashboard.
4.  **Review**: Once matching is done (Status: "Waiting Review"), click on the job ID.
    -   Review items marked as "Uncertain" or "Not Found".
    -   Use the search tool to find the correct track if the automatic match failed.
    -   Confirm or Reject matches.
5.  **Finalize**: Click "Finalize Import" to start adding the tracks to the target playlist.

## 🔧 Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SPOTIPY_CLIENT_ID` | **Required**. Spotify App Client ID. | - |
| `SPOTIPY_CLIENT_SECRET` | **Required**. Spotify App Client Secret. | - |
| `TIDAL_CLIENT_ID` | TIDAL App Client ID (if using TIDAL). | - |
| `TIDAL_CLIENT_SECRET` | TIDAL App Client Secret (if using TIDAL). | - |
| `SECRET_KEY` | Secret key for session signing. | Random/Generated |
| `DATABASE_URL` | PostgreSQL connection string. | `postgresql://user:password@postgres:5432/spotitransfair` |
| `REDIS_URL` | Redis connection string. | `redis://redis:6379/0` |
| `STATS_FILE` | Path to stats file (legacy). | `/data/stats.json` |
| `GEOIP_DB` | Path to GeoIP database. | `/geoip/GeoLite2-Country.mmdb` |

## 📄 License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.
