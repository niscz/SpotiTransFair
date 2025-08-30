// frontend/src/pages/create-playlist.tsx
import { Footer } from "@/components/landing/footer";
import GetHeaders from "@/components/create-playlist/get-headers";
import InputFields from "@/components/create-playlist/input-fields";
import InlineLiveStats from "@/components/landing/inline-live-stats";

export default function CreatePlaylist() {
    return (
        <>
            {/* Mobile View */}
            <main className="lg:hidden flex w-screen h-screen flex-col items-center justify-center p-4">
                <h2 className="text-2xl font-bold text-center text-neutral-800 dark:text-white">
                    You need a laptop to use the tool. We recommend to use Chrome/Firefox (DevTools).
                    <p className="m-4 text-sm text-neutral-500 dark:text-neutral-400 font-normal">
                        {"(Enter full screen mode if you're on a laptop/PC)"}
                    </p>
                </h2>
            </main>

            {/* Desktop View */}
            <main className="hidden lg:flex w-screen flex-col items-center justify-center">
                <div className="mb-10">
                    <GetHeaders />
                </div>
                <h2 className="my-10 text-center mb-3 text-2xl font-bold mx-auto relative z-20 py-4 bg-clip-text text-transparent bg-gradient-to-b from-neutral-800 via-neutral-700 to-neutral-700 dark:from-neutral-800 dark:via-white dark:to-white w-full">
                    Create Playlist
                </h2>
                <InputFields />
                <div className="my-10">
                    <InlineLiveStats />
                </div>
                <Footer />
            </main>
        </>
    );
}
