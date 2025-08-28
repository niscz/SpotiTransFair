// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { PlaylistProvider } from "@/context/playlist-context";
import { ThemeProvider } from "@/components/theme-provider";

import "./index.css";
import App from "./pages/App.tsx";
import CreatePlaylist from "./pages/create-playlist.tsx";
import Announcements from "./pages/announcements.tsx";

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <PlaylistProvider>
            <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
                <BrowserRouter>
                    <Routes>
                        <Route path="/" element={<App />} />
                        <Route
                            path="/create-playlist"
                            element={<CreatePlaylist />}
                        />
                        <Route
                            path="/announcements"
                            element={<Announcements />}
                        />
                    </Routes>
                </BrowserRouter>
            </ThemeProvider>
        </PlaylistProvider>
    </StrictMode>
);
