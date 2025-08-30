// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { ThemeProvider } from "@/components/theme-provider";
import { PlaylistProvider } from "@/context/playlist-context";

import "./index.css";
import App from "./pages/App.tsx";
import CreatePlaylist from "./pages/create-playlist.tsx";
import Announcements from "./pages/announcements.tsx";

const rootEl = document.getElementById("root");
if (!rootEl) {
    throw new Error("Root element #root not found");
}

createRoot(rootEl).render(
    <StrictMode>
        <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
            <PlaylistProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/" element={<App />} />
                        <Route path="/create-playlist" element={<CreatePlaylist />} />
                        <Route path="/announcements" element={<Announcements />} />
                    </Routes>
                </BrowserRouter>
            </PlaylistProvider>
        </ThemeProvider>
    </StrictMode>
);
