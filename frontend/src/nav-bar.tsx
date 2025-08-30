// frontend/src/nav-bar.tsx
import ThemeToggle from "@/components/theme-toggle";
import { FaGithub } from "react-icons/fa";
import { Link } from "react-router-dom";

export default function Navbar() {
    return (
        <nav className="flex w-full justify-between items-center mt-6 px-4 sm:px-10">
            <Link
                to="/"
                className="text-lg font-medium text-black hover:text-zinc-700"
            >
                <span className="bg-gradient-to-r from-white via-zinc-300 to-zinc-400 text-transparent bg-clip-text font-bold text-2xl">
                    SpotiTransFair
                </span>
            </Link>
            <div className="flex items-center gap-8">
                <Link
                    to="/announcements"
                    className="text-black dark:text-white hover:text-zinc-700 dark:hover:text-zinc-300 text-lg font-medium transition-colors"
                >
                    Announcements
                </Link>
                <a
                    href="https://github.com/niscz/SpotiTransFair"
                    className="text-black dark:text-white hover:text-zinc-700 flex items-center"
                >
                    <FaGithub className="w-6 h-6 sm:mr-2" />
                    <span className="hidden sm:inline text-lg font-medium">
                        GitHub
                    </span>
                </a>
                <ThemeToggle />
            </div>
        </nav>
    );
}
