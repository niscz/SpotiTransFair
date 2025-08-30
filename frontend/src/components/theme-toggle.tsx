// frontend/src/components/theme-toggle.tsx
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/theme-provider";

export default function ThemeToggle() {
    const { theme, setTheme } = useTheme();

    // Live-Auswertung für "system"
    const systemPrefersDark =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;

    const isDark = theme === "dark" || (theme === "system" && systemPrefersDark);
    const label = isDark ? "Switch to light theme" : "Switch to dark theme";

    const toggle = () => setTheme(isDark ? "light" : "dark");

    return (
        <button
            type="button"
            aria-label={label}
            aria-pressed={isDark}
            onClick={toggle}
            className="
                relative inline-flex h-7 w-12 items-center rounded-full
                bg-neutral-200 dark:bg-neutral-700
                transition-colors
                overflow-hidden
                ring-1 ring-black/5 dark:ring-white/10
                focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                p-0 border-0
            "
        >
            {/* statische Icons im Track */}
            <Sun className="pointer-events-none absolute left-1 h-4 w-4 text-neutral-600 dark:text-neutral-400" />
            <Moon className="pointer-events-none absolute right-1 h-4 w-4 text-neutral-400 dark:text-neutral-200" />

            {/* Thumb – kein translateX, sondern links/rechts binden */}
            <span
                className={`pointer-events-none absolute top-0.5 h-6 w-6 rounded-full
                    bg-white dark:bg-neutral-100 shadow transition-all duration-200
                    ${isDark ? "right-0.5" : "left-0.5"}`}
            />
        </button>
    );
}
