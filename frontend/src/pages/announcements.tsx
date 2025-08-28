// frontend/src/pages/announcements.tsx
import { Footer } from "@/components/landing/footer";
import Navbar from "@/nav-bar.tsx";

interface Announcement {
    id: string;
    date: string;
    title: string;
    content: string;
    type: "info" | "warning" | "success" | "error";
}

const announcements: Announcement[] = [
    {
        id: "1",
        date: "August 28, 2025",
        title: "SpotiTransFair Launch",
        content: `SpotiTransFair is now live! 🎉`,
        type: "success",
    },
];

function getTypeIcon(type: Announcement["type"]) {
    switch (type) {
        case "warning":
            return "⚠️";
        case "error":
            return "❌";
        case "success":
            return "✅";
        default:
            return "ℹ️";
    }
}

export default function Announcements() {
    return (
        <main className="flex w-screen flex-col items-center justify-center">
            <div className="w-full max-w-[1000px] px-4">
                <Navbar />
                <div className="flex flex-col justify-center items-center mt-20 md:mt-30 lg:mt-40">
                    <div className="text-center mb-12">
                        <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold max-w-3xl mx-auto text-center mt-4 relative z-20 py-4 bg-clip-text text-transparent bg-gradient-to-b from-neutral-800 via-neutral-700 to-neutral-700 dark:from-neutral-800 dark:via-white dark:to-white">
                            Announcements
                        </h1>
                        <p className="text-center text-base sm:text-lg md:text-xl pb-4 transition-colors first:mt-0 bg-clip-text text-transparent bg-gradient-to-r from-black to-zinc-950 dark:from-gray-400 dark:to-gray-300">
                            Latest updates and important information about
                            SpotiTransFair
                        </p>
                    </div>

                    <div className="w-full max-w-4xl">
                        {announcements
                            .slice()
                            .reverse()
                            .map((announcement, index) => (
                                <div key={announcement.id}>
                                    <section
                                        id={`announcement-${announcement.id}`}
                                        className="py-6"
                                    >
                                        <div className="flex items-start gap-3">
                                            <span className="text-lg mt-1 flex-shrink-0">
                                                {getTypeIcon(announcement.type)}
                                            </span>
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3 mb-2">
                                                    <h2 className="text-lg font-semibold text-neutral-800 dark:text-white">
                                                        {announcement.title}
                                                    </h2>
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        {announcement.date}
                                                    </span>
                                                </div>
                                                <div className="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-line leading-relaxed">
                                                    {announcement.content}
                                                </div>
                                                {announcement.id === "7" && (
                                                    <div className="mt-3">
                                                        <a
                                                            href="https://github.com/niscz/SpotiTransFair"
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="inline-flex items-center gap-2 px-3 py-1.5 bg-neutral-800 dark:bg-white text-white dark:text-black text-sm rounded-lg hover:bg-neutral-700 dark:hover:bg-gray-100 transition-colors"
                                                        >
                                                            <span>📚</span>
                                                            View Self-Hosting
                                                            Guide
                                                        </a>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </section>
                                    {index < announcements.length - 1 && (
                                        <div className="border-t-2 border-white dark:border-gray-600"></div>
                                    )}
                                </div>
                            ))}
                    </div>
                </div>
                <Footer />
            </div>
        </main>
    );
}
