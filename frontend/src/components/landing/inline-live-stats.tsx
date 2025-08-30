// frontend/src/components/landing/inline-live-stats.tsx
import { useEffect, useRef } from "react";
import { animate } from "motion";

type Stats = { playlists: number; songs: number };

function useAnimatedCounter(initial = 0) {
    const nodeRef = useRef<HTMLSpanElement>(null);
    const currentRef = useRef<number>(initial);

    const setTo = (to: number) => {
        const node = nodeRef.current;
        if (!node) {
            currentRef.current = to;
            return;
        }
        const from = Number.isFinite(currentRef.current) ? currentRef.current : 0;
        const end = Number.isFinite(to) ? to : 0;
        const delta = Math.abs(end - from);

        const duration = Math.min(2, Math.max(0.4, delta / 500));

        animate(from, end, {
            duration,
            onUpdate: (v) => {
                node.textContent = Math.round(v).toLocaleString();
            },
            onComplete: () => {
                currentRef.current = end;
            },
        });
    };

    return { ref: nodeRef, setTo, valueRef: currentRef };
}

export default function InlineLiveStats({ refreshMs = 10_000 }: { refreshMs?: number }) {
    const playlists = useAnimatedCounter(0);
    const songs = useAnimatedCounter(0);
    const firstLoaded = useRef(false);
    const timer = useRef<number | null>(null);

    async function fetchStatsOnce() {
        try {
            const res = await fetch("/api/stats", { method: "GET" });
            if (!res.ok) return;
            const data: Stats = await res.json();

            const nextPlaylists = Math.max(0, data.playlists || 0);
            const nextSongs = Math.max(0, data.songs || 0);

            if (!firstLoaded.current) {
                playlists.setTo(nextPlaylists);
                songs.setTo(nextSongs);
                firstLoaded.current = true;
            } else {
                playlists.setTo(Math.max(playlists.valueRef.current ?? 0, nextPlaylists));
                songs.setTo(Math.max(songs.valueRef.current ?? 0, nextSongs));
            }
        } catch {
        }
    }

    useEffect(() => {
        fetchStatsOnce();
        timer.current = window.setInterval(fetchStatsOnce, refreshMs) as unknown as number;
        return () => {
            if (timer.current) window.clearInterval(timer.current);
        };
    }, [refreshMs]);

    return (
        <div className="w-full max-w-[1000px] px-4 text-center">
            <p className="text-sm md:text-base text-gray-600 dark:text-gray-400">
                Thanks for using SpotiTransFair — we’ve transferred a total of{" "}
                <span className="mx-1 text-lg md:text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-b from-neutral-800 dark:from-white to-neutral-700 dark:to-gray-400">
                    <span ref={playlists.ref}>0</span>
                </span>{" "}
                playlists with{" "}
                <span className="mx-1 text-lg md:text-xl font-semibold text-transparent bg-clip-text bg-gradient-to-b from-neutral-800 dark:from-white to-neutral-700 dark:to-gray-400">
                    <span ref={songs.ref}>0</span>
                </span>{" "}
                songs.
            </p>
        </div>
    );
}
