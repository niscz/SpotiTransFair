// frontend/src/components/create-playlist/input-fields.tsx
import { usePlaylist } from "@/context/playlist-context";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { FaExclamationCircle } from "react-icons/fa";
import React, { useEffect, useMemo, useState } from "react";

import {
    AlertDialog,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
    AlertDialogFooter,
    AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { FaGithub } from "react-icons/fa";
import { CheckIcon } from "@/components/ui/check.tsx";

// handliche Liste gängiger Spotify-Märkte (kurz gehalten, inkl. EU/NA/SA/AS/OCE)
const MARKET_CHOICES = [
    "US", "GB", "DE", "FR", "IT", "ES", "NL", "SE", "PL", "IE",
    "CA", "BR", "AR", "MX", "CL", "CO",
    "AU", "NZ", "JP", "KR", "IN", "ID", "SG", "TH", "MY", "VN", "PH",
    "TR", "AE", "SA", "ZA"
] as const;
type MarketChoice = typeof MARKET_CHOICES[number];

const PRIVACY_CHOICES = ["PRIVATE", "UNLISTED", "PUBLIC"] as const;
type PrivacyChoice = typeof PRIVACY_CHOICES[number];

export default function InputFields() {
    // ---- types for API result ----
    type Duplicates = { count: number; lines: string[] };
    type MissedTracks = { count: number; tracks: string[]; duplicates?: Duplicates };

    const [authHeaders, setAuthHeaders] = useState("");
    const [serverOnline, setServerOnline] = useState(false);

    const [isValidUrl, setIsValidUrl] = useState(true);
    const [dialogOpen, setdialogOpen] = useState(false);
    const [connectionDialogOpen, setConnectionDialogOpen] = useState(false);
    const [starPrompt, setStarPrompt] = useState(false);
    const [connectionError, setConnectionError] = useState(false);
    const [errorMessage, setErrorMessage] = useState<React.ReactNode>("");
    const [cloneError, setCloneError] = useState(false);
    const [cloneErrorMessage, setCloneErrorMessage] = useState<React.ReactNode>("");
    const [missedTracksDialog, setMissedTracksDialog] = useState(false);
    const [missedTracks, setMissedTracks] = useState<MissedTracks>({
        count: 0,
        tracks: [],
        duplicates: { count: 0, lines: [] },
    });

    // NEW: Market & Privacy UI state
    const [market, setMarket] = useState<MarketChoice | "CUSTOM">("US");
    const [customMarket, setCustomMarket] = useState("");
    const [autoMarket, setAutoMarket] = useState<string | null>(null);
    const [privacyStatus, setPrivacyStatus] = useState<PrivacyChoice>("PRIVATE");

    const { playlistUrl, setPlaylistUrl } = usePlaylist();

    // --- helpers ---
    const effectiveMarket = useMemo(() => {
        if (market === "CUSTOM") {
            return (customMarket || "").trim().toUpperCase();
        }
        return market;
    }, [market, customMarket]);

    const customMarketInvalid =
        market === "CUSTOM" && !/^[A-Z]{2}$/.test(effectiveMarket);

    const isCloneDisabled =
        !isValidUrl ||
        !authHeaders ||
        playlistUrl.trim() === "" ||
        !serverOnline ||
        customMarketInvalid;

    const validateUrl = (url: string) => /^(?:https?:\/\/)?open\.spotify\.com\/playlist\/.+/.test(url);

    const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const url = e.target.value;
        setPlaylistUrl(url);
        setIsValidUrl(validateUrl(url) || url === "");
    };

    // Auto-Market per IP, Fallback: Browser-Locale
    useEffect(() => {
        let cancelled = false;

        async function detectMarket() {
            // 1) IP-Geolocation (ohne API-Key, CORS-freundlich)
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 2500);
                const res = await fetch("https://ipwho.is/?fields=country_code", {
                    signal: controller.signal,
                });
                clearTimeout(timeout);
                const data = await res.json().catch(() => null);
                const cc = (data?.country_code || "").toUpperCase();
                if (!cancelled && /^[A-Z]{2}$/.test(cc)) {
                    setAutoMarket(cc);
                    if (MARKET_CHOICES.includes(cc as MarketChoice)) {
                        setMarket(cc as MarketChoice);
                    } else {
                        setMarket("CUSTOM");
                        setCustomMarket(cc);
                    }
                    return;
                }
            } catch {
                // ignore, fallback below
            }
            // 2) Fallback: navigator.language → "en-US" → "US"
            const loc = (navigator.language || "").split("-")[1];
            const cc = (loc || "").toUpperCase();
            if (!cancelled && /^[A-Z]{2}$/.test(cc)) {
                setAutoMarket(cc);
                if (MARKET_CHOICES.includes(cc as MarketChoice)) {
                    setMarket(cc as MarketChoice);
                } else {
                    setMarket("CUSTOM");
                    setCustomMarket(cc);
                }
            }
        }

        detectMarket();
        return () => {
            cancelled = true;
        };
    }, []);

    async function clonePlaylist() {
        const body = {
            playlist_link: playlistUrl,
            auth_headers: authHeaders,
            market: effectiveMarket || "US",
            privacy_status: privacyStatus,
        };

        try {
            setdialogOpen(true);
            const res = await fetch(`/api/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const data = await res.json();

            if (res.ok) {
                // tolerate older backend shapes gracefully
                const mt = (data?.missed_tracks ?? {}) as Partial<MissedTracks>;
                const missingCount = Number(mt?.count ?? 0);
                const tracks = Array.isArray(mt?.tracks) ? mt!.tracks : [];
                const dupCount = Number(mt?.duplicates?.count ?? 0);
                const dupLines = Array.isArray(mt?.duplicates?.lines) ? mt!.duplicates!.lines : [];

                setMissedTracks({
                    count: missingCount,
                    tracks,
                    duplicates: { count: dupCount, lines: dupLines },
                });

                // Öffne Dialog, wenn fehlende Titel ODER Duplikate vorhanden sind
                if (missingCount > 0 || dupCount > 0) setMissedTracksDialog(true);
                setStarPrompt(true);
            } else if (res.status === 500) {
                setCloneError(true);
                setCloneErrorMessage(
                    <>
                        Server timeout while cloning playlist. Please try again or{" "}
                        <a
                            href="https://github.com/niscz/SpotiTransFair/issues/new/choose"
                            className="text-blue-500 hover:underline"
                        >
                            report this issue
                        </a>
                    </>
                );
            } else {
                setCloneError(true);
                setCloneErrorMessage(
                    // nicer backend errors (new API returns {error:{code,message}})
                    data?.error?.message || data?.message || "Failed to clone playlist"
                );
            }
        } catch {
            setCloneError(true);
            setCloneErrorMessage("Network error while cloning playlist");
        } finally {
            setdialogOpen(false);
        }
    }

    async function testConnection() {
        setConnectionDialogOpen(true);
        setConnectionError(false);
        setServerOnline(false);

        try {
            const res = await fetch(`/api/`, { method: "GET", headers: { "Content-Type": "application/json" } });
            const data = await res.json();
            if (res.ok) {
                setServerOnline(true);
                console.log(data);
            } else if (res.status === 500) {
                setConnectionError(true);
                setErrorMessage(
                    <>
                        Server Error (500). The server likely hit a timeout. Please try again later or{" "}
                        <a
                            href="https://github.com/niscz/SpotiTransFair/issues/new/choose"
                            className="text-blue-500 hover:underline"
                        >
                            report this issue on GitHub
                        </a>
                        .
                    </>
                );
            }
        } catch {
            setConnectionError(true);
            setErrorMessage(
                <>
                    Unable to connect to server. If this issue persists, please contact me or{" "}
                    <a
                        href="https://github.com/niscz/SpotiTransFair/issues/new/choose"
                        className="text-blue-500 hover:underline"
                    >
                        open an issue on GitHub
                    </a>
                </>
            );
        } finally {
            setConnectionDialogOpen(false);
        }
    }

    return (
        <>
            <div className="w-full flex items-center justify-around">
                {/* LEFT: Auth headers */}
                <div className="flex flex-col gap-3 items-center justify-center">
                    <div className="space-y-1">
                        <h1 className="text-lg font-semibold">Paste headers here</h1>
                    </div>
                    <Textarea
                        placeholder="Paste your headers here"
                        value={authHeaders}
                        onChange={(e) => setAuthHeaders(e.target.value)}
                        id="auth-headers"
                        className="w-[40vw] h-[50vh]"
                    />
                </div>

                {/* RIGHT: Server connect + playlist + options */}
                <div className="flex flex-col gap-12 items-start justify-center">
                    {/* connect */}
                    <div className="flex flex-col w-full gap-3 items-center justify-center">
                        <div className="space-y-1 w-full">
                            <h1 className="text-lg font-semibold w-full">You need to be connected to the server</h1>
                            {serverOnline && <p className="text-green-500 text-sm">Connection Successful</p>}
                        </div>
                        <AlertDialog open={connectionDialogOpen} onOpenChange={setConnectionDialogOpen}>
                            <AlertDialogTrigger asChild>
                                <Button className="w-full" onClick={testConnection}>
                                    Connect
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Requesting connection...</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        Please wait till the server comes online. This may take upto a minute.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>

                    {/* playlist URL */}
                    <div className="flex flex-col gap-3 items-start justify-center">
                        <div className="space-y-1">
                            <h1 className="text-lg font-semibold">Paste Spotify playlist URL here</h1>
                            <div className="flex items-center gap-2">
                                <FaExclamationCircle />
                                <p className="text-sm text-gray-500">Make sure the playlist is public</p>
                            </div>
                            <div className="flex items-center gap-2 mt-2">
                                <FaExclamationCircle className="text-orange-500" />
                                <p className="text-sm text-gray-500">
                                    Timeout issues are common due to server limitations.
                                    <br />
                                    If you experience them, consider{" "}
                                    <a
                                        href="https://github.com/niscz/SpotiTransFair/?tab=readme-ov-file#-quick-start"
                                        className="text-blue-500 hover:underline"
                                    >
                                        self-hosting
                                    </a>{" "}
                                    for better reliability.
                                </p>
                            </div>
                        </div>
                        <Input
                            placeholder="Paste your playlist URL here"
                            value={playlistUrl}
                            onChange={handleUrlChange}
                            id="playlist-name"
                            className={`w-full ${!isValidUrl ? "border-red-500" : ""}`}
                        />
                        {!isValidUrl && <p className="text-red-500 text-sm">Please enter a valid Spotify playlist URL</p>}

                        {/* NEW: Options (Market + Privacy) */}
                        <div className="mt-4 w-full grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Market select */}
                            <div className="flex flex-col">
                                <label htmlFor="market" className="text-sm font-medium mb-1">
                                    Market
                                </label>
                                <div className="flex items-center gap-2">
                                    <select
                                        id="market"
                                        value={market === "CUSTOM" ? "CUSTOM" : market}
                                        onChange={(e) => {
                                            const v = e.target.value as MarketChoice | "CUSTOM";
                                            if (v === "CUSTOM") setMarket("CUSTOM");
                                            else setMarket(v);
                                        }}
                                        className="border rounded-md px-3 py-2 bg-background"
                                    >
                                        {MARKET_CHOICES.map((m) => (
                                            <option key={m} value={m}>
                                                {m}
                                            </option>
                                        ))}
                                        <option value="CUSTOM">Other…</option>
                                    </select>
                                </div>
                                {market === "CUSTOM" && (
                                    <div className="mt-2">
                                        <Input
                                            placeholder="Enter 2-letter country code (e.g., US)"
                                            value={customMarket}
                                            onChange={(e) => setCustomMarket(e.target.value)}
                                            className={`${customMarketInvalid ? "border-red-500" : ""}`}
                                        />
                                        {customMarketInvalid && (
                                            <p className="text-xs text-red-500 mt-1">Please enter a valid 2-letter country code.</p>
                                        )}
                                    </div>
                                )}
                                <p className="text-xs text-zinc-500 mt-1">
                                    {autoMarket ? (
                                        <>Auto-detected: <span className="font-mono">{autoMarket}</span></>
                                    ) : (
                                        "Auto-detecting your country…"
                                    )}
                                </p>
                            </div>

                            {/* Privacy select */}
                            <div className="flex flex-col">
                                <label htmlFor="privacy" className="text-sm font-medium mb-1">
                                    Privacy
                                </label>
                                <select
                                    id="privacy"
                                    value={privacyStatus}
                                    onChange={(e) => setPrivacyStatus(e.target.value as PrivacyChoice)}
                                    className="border rounded-md px-3 py-2 bg-background"
                                >
                                    <option value="PRIVATE">PRIVATE (default)</option>
                                    <option value="UNLISTED">UNLISTED</option>
                                    <option value="PUBLIC">PUBLIC</option>
                                </select>
                                <p className="text-xs text-zinc-500 mt-1">
                                    Controls the visibility of the newly created YouTube Music playlist.
                                </p>
                            </div>
                        </div>

                        {/* Clone button + dialogs */}
                        <AlertDialog open={dialogOpen} onOpenChange={setdialogOpen}>
                            <AlertDialogTrigger asChild>
                                <Button disabled={isCloneDisabled} className="w-full" onClick={clonePlaylist}>
                                    Clone Playlist
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Fetching playlist...</AlertDialogTitle>
                                    <AlertDialogDescription>This may take a few minutes</AlertDialogDescription>
                                </AlertDialogHeader>
                            </AlertDialogContent>
                        </AlertDialog>

                        <AlertDialog open={starPrompt} onOpenChange={setStarPrompt}>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>
                                        <div className="flex items-center">
                                            <CheckIcon />
                                            Your Playlist has been cloned!
                                        </div>
                                    </AlertDialogTitle>
                                    <AlertDialogDescription>
                                        <div className="ml-12 mb-2">
                                            <p>Please consider starring the project on GitHub.</p>
                                            <p>It's free and helps me a lot!</p>
                                        </div>
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <div className="flex items-center justify-between w-full">
                                        <Button>
                                            <a
                                                className="w-full flex items-center gap-2"
                                                href="https://github.com/niscz/SpotiTransFair"
                                            >
                                                ⭐ on GitHub
                                                <FaGithub className="w-6 h-6" />
                                            </a>
                                        </Button>
                                        <AlertDialogAction>Clone Another Playlist</AlertDialogAction>
                                    </div>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>
                </div>
            </div>

            {/* Connection Error */}
            <AlertDialog open={connectionError} onOpenChange={setConnectionError}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Connection Error</AlertDialogTitle>
                        <AlertDialogDescription>{errorMessage}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogAction onClick={() => setConnectionError(false)}>Try Again</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Clone Error */}
            <AlertDialog open={cloneError} onOpenChange={setCloneError}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Clone Error</AlertDialogTitle>
                        <AlertDialogDescription>{cloneErrorMessage}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogAction onClick={() => setCloneError(false)}>Try Again</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Missed tracks */}
            <AlertDialog open={missedTracksDialog} onOpenChange={setMissedTracksDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        {(() => {
                            const missingCount = missedTracks?.count ?? 0;
                            const dupCount = missedTracks?.duplicates?.count ?? 0;
                            const title =
                                missingCount > 0 && dupCount > 0
                                    ? "Some songs couldn't be found & duplicates were ignored"
                                    : missingCount > 0
                                    ? "Some songs couldn't be found"
                                    : "Duplicates were ignored";
                            return <AlertDialogTitle>{title}</AlertDialogTitle>;
                        })()}
                        <AlertDialogDescription>
                            <div className="mt-2">
                                {/* Missing */}
                                {missedTracks.count > 0 && (
                                    <>
                                        <p className="mb-2">
                                            {missedTracks.count} songs couldn't be found on YouTube Music:
                                        </p>
                                        <div className="max-h-[200px] overflow-y-auto">
                                            <ul className="list-disc list-inside">
                                                {missedTracks.tracks.map((track, index) => (
                                                    <li key={index} className="text-sm">
                                                        {track}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </>
                                )}

                                {/* Duplicates */}
                                {!!missedTracks.duplicates?.count && (
                                    <div className={`mt-4 ${missedTracks.count ? "border-t pt-4" : ""}`}>
                                        <p className="mb-2">
                                            {missedTracks.duplicates.count} duplicates ignored:
                                        </p>
                                        <div className="max-h-[200px] overflow-y-auto">
                                            <ul className="list-disc list-inside">
                                                {missedTracks.duplicates.lines.map((line, i) => (
                                                    <li key={i} className="text-sm">
                                                        {line}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="mt-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() =>
                                                    navigator.clipboard.writeText(
                                                        missedTracks.duplicates!.lines.join("\n")
                                                    )
                                                }
                                            >
                                                Copy duplicate list
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogAction onClick={() => setMissedTracksDialog(false)}>Close</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
