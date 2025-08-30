// frontend/src/components/landing/live-stats.tsx
import { useEffect, useRef } from "react";
import { animate } from "motion";

type Stats = { playlists: number; songs: number };

type Props = {
    variant?: "home" | "create"; // home: "Join the community..." | create: "Thanks for using..."
    pollMs?: number; // default 10s
};

const fmt = (n: number) => Math.round(n).toLocaleString();

export default function LiveStats({ variant = "home", pollMs = 10_000 }: Props) {
    // Spans für Zahlen
    const playlistsEl = useRef<HTMLSpanElement | null>(null);
    const songsEl = useRef<HTMLSpanElement | null>(null);

    // Letzter bekannter Zahlenstand (Start: 0, 0 nur beim Initial-Load!)
    const lastPlaylists = useRef<number>(0);
    const lastSongs = useRef<number>(0);

    // Läuft gerade eine Animation? (je Zahl separat)
    const playlistsAnim = useRef<ReturnType<typeof animate> | null>(null);
    const songsAnim = useRef<ReturnType<typeof animate> | null>(null);

    // Hilfsfunktion zum Animieren von A -> B; wenn gleich, keine Animation
    function animateNumber(
        el: HTMLSpanElement | null,
        last: { current: number },
        next: number,
        animRef: { current: ReturnType<typeof animate> | null },
        duration = 1.0
    ) {
        if (!el) return;

        if (next === last.current) {
            // nichts zu tun
            return;
        }

        // laufende Animation abbrechen
        animRef.current?.stop();

        // Von letztem Stand zu neuem Stand animieren
        animRef.current = animate(last.current, next, {
            duration,
            // (ohne .finished / ohne easing-Typen-Stress)
            onUpdate: (v: number) => {
                el.textContent = fmt(v);
            },
            onComplete: () => {
                last.current = next;
                el.textContent = fmt(next);
            },
        });
    }

    // Initial fetch + Intervall
    useEffect(() => {
        let mounted = true;
        // Beim ersten Render zählt er von 0 -> erster Wert
        const initialLoad = async () => {
            try {
                const res = await fetch("/api/stats");
                if (!res.ok) return;
                const data = (await res.json()) as Stats;
                if (!mounted) return;

                // Initial: von 0 -> data.*
                animateNumber(playlistsEl.current, lastPlaylists, data.playlists, playlistsAnim, 1.0);
                animateNumber(songsEl.current, lastSongs, data.songs, songsAnim, 1.0);
            } catch {
                // silently ignore
            }
        };

        const tick = async () => {
            try {
                const res = await fetch("/api/stats");
                if (!res.ok) return;
                const data = (await res.json()) as Stats;
                if (!mounted) return;

                // Nur zählen, wenn sich Werte geändert haben — und dann vom letzten Stand nach oben
                animateNumber(playlistsEl.current, lastPlaylists, data.playlists, playlistsAnim, 0.8);
                animateNumber(songsEl.current, lastSongs, data.songs, songsAnim, 0.8);
            } catch {
                // silently ignore
            }
        };

        initialLoad();
        const id = window.setInterval(tick, pollMs);

        return () => {
            mounted = false;
            window.clearInterval(id);
            playlistsAnim.current?.stop();
            songsAnim.current?.stop();
        };
    }, [pollMs]);

    // Text je nach Variante
    const prefix =
        variant === "home"
            ? "Join the community that has transferred over"
            : "Thanks for using SpotiTransFair, we transferred a total of";

    const middle = variant === "home" ? "playlists and" : "playlists with";
    const suffix = "songs!";

    return (
        <div className="w-full max-w-[1000px] px-4 text-center">
            <p className="text-lg md:text-xl text-gray-600 dark:text-gray-400">
                {prefix}{" "}
                <span className="mx-2 text-2xl md:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-neutral-800 dark:from-white to-neutral-700 dark:to-gray-400">
                    <span ref={playlistsEl}>0</span>
                </span>{" "}
                {middle}{" "}
                <span className="mx-2 text-2xl md:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-neutral-800 dark:from-white to-neutral-700 dark:to-gray-400">
                    <span ref={songsEl}>0</span>
                </span>{" "}
                {suffix}
            </p>
        </div>
    );
}
