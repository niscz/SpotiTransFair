// frontend/src/components/theme-provider.tsx
import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light" | "system";

type ThemeProviderProps = {
    children: React.ReactNode;
    defaultTheme?: Theme;
    storageKey?: string;
};

type ThemeProviderState = {
    theme: Theme;
    setTheme: (theme: Theme) => void;
};

const initialState: ThemeProviderState = {
    theme: "system",
    setTheme: () => null,
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

export function ThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "vite-ui-theme",
}: ThemeProviderProps) {
    const [theme, setTheme] = useState<Theme>(() => {
        if (typeof window === "undefined") return defaultTheme;
        const fromStorage = window.localStorage.getItem(storageKey) as Theme | null;
        return fromStorage ?? defaultTheme;
    });

    // Apply theme to <html> class and keep in sync with system when needed
    useEffect(() => {
        if (typeof document === "undefined") return;

        const root = document.documentElement;
        root.classList.remove("light", "dark");

        if (theme === "system") {
            const systemIsDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
            root.classList.add(systemIsDark ? "dark" : "light");
        } else {
            root.classList.add(theme);
        }
    }, [theme]);

    // If theme = system, react to OS changes
    useEffect(() => {
        if (theme !== "system" || typeof window === "undefined") return;

        const mql = window.matchMedia("(prefers-color-scheme: dark)");
        const handler = () => {
            const root = document.documentElement;
            root.classList.remove("light", "dark");
            root.classList.add(mql.matches ? "dark" : "light");
        };

        mql.addEventListener("change", handler);
        return () => mql.removeEventListener("change", handler);
    }, [theme]);

    const value: ThemeProviderState = {
        theme,
        setTheme: (t: Theme) => {
            if (typeof window !== "undefined") {
                window.localStorage.setItem(storageKey, t);
            }
            setTheme(t);
        },
    };

    return (
        <ThemeProviderContext.Provider value={value}>
            {children}
        </ThemeProviderContext.Provider>
    );
}

export const useTheme = () => {
    const ctx = useContext(ThemeProviderContext);
    if (ctx === undefined) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return ctx;
};
