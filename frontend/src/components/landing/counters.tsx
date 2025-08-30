// frontend/src/components/landing/counters.tsx
import { useEffect, useState, useRef } from "react";
import { animate } from "motion";

interface Stats {
    playlists: number;
    songs: number;
}

// A reusable animated counter component
function AnimatedCounter({ to }: { to: number }) {
    const nodeRef = useRef<HTMLSpanElement>(null);

    useEffect(() => {
        const node = nodeRef.current;
        if (!node) return;

        const controls = animate(0, to, {
            duration: 2,
            ease: "easeOut",
            onUpdate(value) {
                // Use toLocaleString to format numbers with commas (e.g., 1,234)
                node.textContent = Math.round(value).toLocaleString();
            },
        });

        return () => controls.stop();
    }, [to]);

    return <span ref={nodeRef}>0</span>;
}


export default function Counters() {
    const [stats, setStats] = useState<Stats | null>(null);

    useEffect(() => {
        async function fetchStats() {
            try {
                const res = await fetch(`/api/stats`);
                if (res.ok) {
                    const data = await res.json() as Stats;
                    setStats(data);
                }
            } catch (error) {
                console.error("Failed to fetch stats:", error);
            }
        }
        fetchStats();
    }, []);

    // Render nothing if stats haven't been loaded yet to avoid a flash of 0s
    if (!stats) {
        return <div className="h-16" />; // Placeholder for layout stability
    }

    return (
        <div className="w-full max-w-[1000px] px-4 text-center">
            <p className="text-lg md:text-xl text-gray-600 dark:text-gray-400">
                Join the community that has transferred over
                <br className="sm:hidden" />
                <span className="mx-2 text-2xl md:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-neutral-800 dark:from-white to-neutral-700 dark:to-gray-400">
                    <AnimatedCounter to={stats.playlists} />
                </span>
                playlists and
                <span className="mx-2 text-2xl md:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-neutral-800 dark:from-white to-neutral-700 dark:to-gray-400">
                    <AnimatedCounter to={stats.songs} />
                </span>
                songs!
            </p>
        </div>
    );
}
