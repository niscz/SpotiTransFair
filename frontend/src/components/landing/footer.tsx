// frontend/src/components/landing/footer.tsx

export function Footer() {
    return (
        <footer className="border-t w-full mt-28 py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            <div className="container mx-auto px-4">
                {/* Main author credit */}
                <p className="mb-2">
                    Built by{" "}
                    <a
                        href="https://github.com/niscz"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 dark:text-blue-400 hover:underline"
                    >
                        @niscz
                    </a>
                </p>

                {/* License Notice Section */}
                <div className="mt-8 text-xs text-gray-400 dark:text-gray-500 max-w-3xl mx-auto space-y-2">
                    <p className="font-semibold">
                        SpotiTransFair - A tool to transfer Spotify playlists to YouTube Music.
                        <br />
                        Copyright (C) 2025 niscz (based on the original work by <a href="https://github.com/Pushan2005">@Pushan2005</a>)
                    </p>
                    <p>
                        This program is free software: you can redistribute it and/or modify
                        it under the terms of the GNU General Public License as published by
                        the Free Software Foundation, either version 3 of the License, or
                        (at your option) any later version.
                    </p>
                    <p>
                        This program is distributed in the hope that it will be useful,
                        but WITHOUT ANY WARRANTY; without even the implied warranty of
                        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
                        GNU General Public License for more details.
                    </p>
                    <p>
                        You should have received a copy of the GNU General Public License
                        along with this program. If not, see{" "}
                        <a
                            href="https://www.gnu.org/licenses/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline hover:text-gray-300"
                        >
                            https://www.gnu.org/licenses/
                        </a>.
                    </p>
                </div>
            </div>
        </footer>
    );
}