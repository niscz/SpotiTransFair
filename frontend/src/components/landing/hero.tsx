// frontend/src/components/landing/hero.tsx
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Navbar from "@/nav-bar.tsx";
import { Link } from "react-router-dom";
import { usePlaylist } from "@/context/playlist-context";

export default function Hero() {
    const { playlistUrl, setPlaylistUrl } = usePlaylist();

    return (
        <main className="flex justify-center items-center mt-5">
            <div className="w-full max-w-[1000px] px-4">
                <Navbar />
                <div className="flex flex-col justify-center items-center mt-20 md:mt-30 lg:mt-40">
                    <div className="text-center">
                        <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold max-w-3xl mx-auto text-center mt-4 relative z-20 py-4 bg-clip-text text-transparent bg-gradient-to-b from-neutral-800 via-neutral-700 to-neutral-700 dark:from-neutral-800 dark:via-white dark:to-white">
                            Transfer your Spotify Playlist to YouTube Music
                        </h1>
                        <p className="text-center text-base sm:text-lg md:text-xl pb-4 transition-colors first:mt-0 bg-clip-text text-transparent bg-gradient-to-r from-black to-zinc-950 dark:from-gray-400 dark:to-gray-300">
                            SpotiTransFair is a free service that allows you to
                            transfer your Spotify playlists to YouTube Music in
                            a few simple steps.
                        </p>
                        <form className="flex flex-col items-center justify-center gap-4 sm:flex-row sm:gap-3 mt-8">
                            <span className="text-lg sm:text-xl font-medium tracking-tight transition-colors bg-clip-text text-transparent bg-gradient-to-r from-zinc-800 to-zinc-700">
                                Paste your Spotify Link here
                            </span>
                            <Input
                                placeholder="open.spotify.com/playlist/. . ."
                                value={playlistUrl}
                                onChange={(e) => setPlaylistUrl(e.target.value)}
                                className="w-full sm:w-auto max-w-lg py-2 text-lg"
                            />
                            <Link to="/create-playlist">
                                <Button className="w-full sm:w-auto py-2 text-md">
                                    Get Started
                                </Button>
                            </Link>
                        </form>
                    </div>
                </div>
            </div>
        </main>
    );
}
