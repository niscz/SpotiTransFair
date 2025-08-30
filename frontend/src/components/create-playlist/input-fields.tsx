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
import { CheckIcon } from "@/components/ui/check";
import { LuLoader, LuX } from "react-icons/lu";

// --- Types ---
const MARKET_CHOICES = [
    "US", "GB", "DE", "FR", "IT", "ES", "NL", "SE", "PL", "IE",
    "CA", "BR", "AR", "MX", "CL", "CO",
    "AU", "NZ", "JP", "KR", "IN", "ID", "SG", "TH", "MY", "VN", "PH",
    "TR", "AE", "SA", "ZA"
] as const;
type MarketChoice = typeof MARKET_CHOICES[number];

const PRIVACY_CHOICES = ["PRIVATE", "UNLISTED", "PUBLIC"] as const;
type PrivacyChoice = typeof PRIVACY_CHOICES[number];

type YtmFilter = "songs" | "videos" | "uploads";

interface DuplicatesData { count: number; items: string[] }
interface MissedTracksData {
    count: number;
    tracks: string[];
    duplicates?: DuplicatesData;
    _stats?: { found_total?: number; inserted?: number };
}
interface CloneSuccessResponse {
    message: string;
    missed_tracks: MissedTracksData;
    playlist_id?: string;
    playlist_url?: string;
}
interface ErrorResponse {
    error?: { code: string; message: string };
    message?: string;
}
interface RetrySuccessItem {
    videoId: string;
    title?: string;
    artists?: { name: string }[];
}
interface RetrySearchResponse {
    results?: RetrySuccessItem[];
}

interface MissedTrackItem {
    originalQuery: string;
    editedQuery: string;
    status: "pending" | "retrying" | "success" | "failed";
    filter: YtmFilter;
    suggestions: RetrySuccessItem[];
}

export default function InputFields() {
    // --- Component State ---
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
    const [missedTracks, setMissedTracks] = useState<MissedTrackItem[]>([]);
    const [ignoredDuplicates, setIgnoredDuplicates] = useState<DuplicatesData>({ count: 0, items: [] });

    // Validate Headers
    const [headersValid, setHeadersValid] = useState<null | boolean>(null);
    const [headersValidateBusy, setHeadersValidateBusy] = useState(false);
    const [headersValidateMsg, setHeadersValidateMsg] = useState<string>("");

    // Market & Privacy
    const [market, setMarket] = useState<MarketChoice | "CUSTOM">("US");
    const [customMarket, setCustomMarket] = useState("");
    const [autoMarket, setAutoMarket] = useState<string | null>(null);
    const [privacyStatus, setPrivacyStatus] = useState<PrivacyChoice>("PRIVATE");

    // Preview
    const [previewBusy, setPreviewBusy] = useState(false);
    const [preview, setPreview] = useState<{ name: string; track_count: number } | null>(null);
    const [previewError, setPreviewError] = useState<string>("");

    // Update existing
    const [updateExisting, setUpdateExisting] = useState(false);
    const [existingPlaylistUrl, setExistingPlaylistUrl] = useState("");

    // Playlist ID from clone for later adds
    const [createdPlaylistId, setCreatedPlaylistId] = useState<string | null>(null);

    const { playlistUrl, setPlaylistUrl } = usePlaylist();

    // --- Memoized Values ---
    const effectiveMarket = useMemo(() => {
        if (market === "CUSTOM") return (customMarket || "").trim().toUpperCase();
        return market;
    }, [market, customMarket]);

    const customMarketInvalid = market === "CUSTOM" && !/^[A-Z]{2}$/.test(effectiveMarket);

    const validateUrl = (url: string) =>
        /^(?:https?:\/\/)?open\.spotify\.com\/playlist\/.+/.test(url);

    const isCloneDisabled =
        !isValidUrl ||
        !authHeaders ||
        playlistUrl.trim() === "" ||
        !serverOnline ||
        customMarketInvalid ||
        (updateExisting && existingPlaylistUrl.trim() === "");

    const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const url = e.target.value;
        setPlaylistUrl(url);
        setIsValidUrl(validateUrl(url) || url === "");
    };

    // --- Effects ---
    useEffect(() => {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
        const qs = tz ? `?tz=${encodeURIComponent(tz)}` : "";
        (async () => {
            try {
                const res = await fetch(`/api/market/guess${qs}`, { method: "GET" });
                if (!res.ok) throw new Error("guess failed");
                const data: { market: string } = await res.json();
                const cc = (data.market || "").toUpperCase();
                setAutoMarket(cc || null);
                if (cc && (MARKET_CHOICES as readonly string[]).includes(cc)) {
                    setMarket(cc as MarketChoice);
                } else if (cc) {
                    setMarket("CUSTOM");
                    setCustomMarket(cc);
                }
            } catch {
                const loc = (navigator.language || "").split("-")[1];
                const cc = (loc || "").toUpperCase();
                setAutoMarket(/^[A-Z]{2}$/.test(cc) ? cc : null);
                if (cc && MARKET_CHOICES.includes(cc as MarketChoice)) {
                    setMarket(cc as MarketChoice);
                } else if (cc) {
                    setMarket("CUSTOM");
                    setCustomMarket(cc);
                }
            }
        })();
    }, []);

    // --- API Calls ---
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
                        </a>.
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

    async function validateHeaders() {
        setHeadersValidateBusy(true);
        setHeadersValid(null);
        setHeadersValidateMsg("");
        try {
            const res = await fetch(`/api/validate-headers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ auth_headers: authHeaders }),
            });
            const data = await res.json();
            if (res.ok && data?.valid) {
                setHeadersValid(true);
                setHeadersValidateMsg("Headers valid.");
            } else {
                setHeadersValid(false);
                setHeadersValidateMsg(data?.error?.message || data?.message || "Validation failed.");
            }
        } catch (e) {
            setHeadersValid(false);
            setHeadersValidateMsg("Network error during validation.");
        } finally {
            setHeadersValidateBusy(false);
        }
    }

    async function loadPreview() {
        if (!validateUrl(playlistUrl)) return;
        setPreview(null);
        setPreviewError("");
        setPreviewBusy(true);
        try {
            const u = new URLSearchParams({ playlist_link: playlistUrl, market: effectiveMarket || "US" }).toString();
            const res = await fetch(`/api/spotify/preview?${u}`);
            const data = await res.json();
            if (res.ok) {
                setPreview({ name: data.name, track_count: data.track_count });
            } else {
                setPreviewError(data?.error?.message || data?.message || "Preview failed");
            }
        } catch {
            setPreviewError("Network error while previewing playlist");
        } finally {
            setPreviewBusy(false);
        }
    }

    async function clonePlaylist() {
        const body: Record<string, any> = {
            playlist_link: playlistUrl,
            auth_headers: authHeaders,
            market: effectiveMarket || "US",
            privacy_status: privacyStatus,
        };
        if (updateExisting && existingPlaylistUrl.trim()) {
            body["target_playlist_id"] = extractYtmPlaylistId(existingPlaylistUrl.trim());
        }

        try {
            setdialogOpen(true);
            const res = await fetch(`/api/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            if (res.ok) {
                const data = (await res.json()) as CloneSuccessResponse;
                setCreatedPlaylistId(data.playlist_id ?? null);
                const mt = data.missed_tracks;

                if (mt && mt.count > 0) {
                    setMissedTracks(
                        mt.tracks.map((track) => ({
                            originalQuery: track,
                            editedQuery: track,
                            status: "pending",
                            filter: "songs",
                            suggestions: [],
                        }))
                    );
                } else {
                    setMissedTracks([]);
                }

                if (mt && mt.duplicates && mt.duplicates.count > 0) {
                    setIgnoredDuplicates(mt.duplicates);
                } else {
                    setIgnoredDuplicates({ count: 0, items: [] });
                }

                if ((mt?.count ?? 0) > 0 || (mt?.duplicates?.count ?? 0) > 0) {
                    setMissedTracksDialog(true);
                } else {
                    setStarPrompt(true);
                }
            } else {
                const data = (await res.json()) as ErrorResponse;
                setCloneError(true);
                setCloneErrorMessage(data.error?.message || data.message || "Failed to clone playlist");
            }
        } catch {
            setCloneError(true);
            setCloneErrorMessage("Network error while cloning playlist");
        } finally {
            setdialogOpen(false);
        }
    }

    async function retrySearch(index: number) {
        const t = missedTracks[index];
        if (!t || t.status === "retrying" || t.status === "success") return;
        const updated = [...missedTracks];
        updated[index].status = "retrying";
        updated[index].suggestions = [];
        setMissedTracks(updated);

        try {
            const res = await fetch(`/api/ytm/search`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: t.editedQuery,
                    filter: t.filter,
                    auth_headers: authHeaders,
                    top_k: 5,
                }),
            });
            const data = (await res.json()) as RetrySearchResponse;
            const finalTracks = [...updated];
            if (res.ok && Array.isArray(data.results) && data.results.length > 0) {
                finalTracks[index].status = "pending";
                finalTracks[index].suggestions = data.results;
            } else {
                finalTracks[index].status = "failed";
            }
            setMissedTracks(finalTracks);
        } catch {
            const finalTracks = [...updated];
            finalTracks[index].status = "failed";
            setMissedTracks(finalTracks);
        }
    }

    async function addSuggestion(videoId: string, index: number) {
        if (!createdPlaylistId || !videoId) return;
        const updated = [...missedTracks];
        updated[index].status = "retrying";
        setMissedTracks(updated);
        try {
            const res = await fetch(`/api/ytm/add`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    playlist_id: createdPlaylistId,
                    video_id: videoId,
                    auth_headers: authHeaders,
                }),
            });
            if (res.ok) {
                const final = [...missedTracks];
                final[index].status = "success";
                setMissedTracks(final);
            } else {
                const final = [...missedTracks];
                final[index].status = "failed";
                setMissedTracks(final);
            }
        } catch {
            const final = [...missedTracks];
            final[index].status = "failed";
            setMissedTracks(final);
        }
    }

    function extractYtmPlaylistId(urlOrId: string) {
        if (/^PL|^OLAK/.test(urlOrId)) return urlOrId;
        try {
            const u = new URL(urlOrId);
            const id = u.searchParams.get("list");
            return id || urlOrId;
        } catch {
            return urlOrId;
        }
    }

    return (
        <>
            <div className="w-full flex items-start justify-around">
                {/* LEFT: Auth headers */}
                <div className="flex flex-col gap-3 items-center justify-center w-[40vw]">
                    <div className="space-y-1 text-center">
                        <h1 className="text-lg font-semibold">Paste Headers Here</h1>
                    </div>
                    <Textarea
                        placeholder="Paste your raw request headers here"
                        value={authHeaders}
                        onChange={(e) => { setAuthHeaders(e.target.value); setHeadersValid(null); }}
                        id="auth-headers"
                        className="h-[50vh] min-h-[300px]"
                    />
                    <div className="flex gap-2 w-full">
                        <Button className="w-full" variant="secondary" onClick={validateHeaders} disabled={!authHeaders || headersValidateBusy}>
                            {headersValidateBusy ? <span className="inline-flex gap-2 items-center"><LuLoader className="animate-spin" /> Validating…</span> : "Validate headers"}
                        </Button>
                    </div>
                    {headersValid === true && <p className="text-green-500 text-sm mt-1">✓ {headersValidateMsg || "Headers valid."}</p>}
                    {headersValid === false && <p className="text-red-500 text-sm mt-1">✗ {headersValidateMsg || "Invalid headers."}</p>}
                </div>

                {/* RIGHT: Server connect + playlist + options */}
                <div className="flex flex-col gap-8 items-start justify-center w-[40vw]">
                    {/* connect */}
                    <div className="flex flex-col w-full gap-3 items-center justify-center">
                        <div className="space-y-1 w-full">
                            <h1 className="text-lg font-semibold w-full">1. Connect to Server</h1>
                            {serverOnline && <p className="text-green-500 text-sm">✓ Connection Successful</p>}
                        </div>
                        <AlertDialog open={connectionDialogOpen} onOpenChange={setConnectionDialogOpen}>
                            <AlertDialogTrigger asChild>
                                <Button className="w-full" onClick={testConnection}>Connect</Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Requesting connection...</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        Please wait till the server comes online.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>

                    {/* playlist URL & options */}
                    <div className="flex flex-col gap-3 items-start justify-center w-full">
                        <div className="space-y-1">
                            <h1 className="text-lg font-semibold">2. Provide Playlist & Options</h1>
                            <div className="flex items-center gap-2">
                                <FaExclamationCircle />
                                <p className="text-sm text-gray-500">Make sure the playlist is public</p>
                            </div>
                        </div>

                        {/* Spotify URL */}
                        <div className="flex gap-2 w-full">
                            <Input
                                placeholder="Paste your Spotify playlist URL here"
                                value={playlistUrl}
                                onChange={handleUrlChange}
                                id="playlist-url"
                                className={`w-full ${!isValidUrl ? "border-red-500" : ""}`}
                            />
                            <Button variant="outline" onClick={loadPreview} disabled={!isValidUrl || !playlistUrl || previewBusy}>
                                {previewBusy ? "Preview..." : "Preview"}
                            </Button>
                        </div>
                        {!isValidUrl && <p className="text-red-500 text-sm">Please enter a valid Spotify playlist URL</p>}
                        {preview && <p className="text-sm text-zinc-500">Name: <span className="font-medium">{preview.name}</span> • Tracks: {preview.track_count}</p>}
                        {previewError && <p className="text-red-500 text-sm">{previewError}</p>}

                        {/* Options (Market + Privacy) */}
                        <div className="mt-2 w-full grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="flex flex-col">
                                <label htmlFor="market" className="text-sm font-medium mb-1">Market</label>
                                <select
                                    id="market"
                                    value={market}
                                    onChange={(e) => setMarket(e.target.value as MarketChoice | "CUSTOM")}
                                    className="border rounded-md px-3 py-2 bg-background"
                                >
                                    {MARKET_CHOICES.map((m) => <option key={m} value={m}>{m}</option>)}
                                    <option value="CUSTOM">Other…</option>
                                </select>
                                {market === "CUSTOM" && (
                                    <Input
                                        placeholder="e.g., US"
                                        value={customMarket}
                                        onChange={(e) => setCustomMarket(e.target.value)}
                                        className={`mt-2 ${customMarketInvalid ? "border-red-500" : ""}`}
                                    />
                                )}
                                <p className="text-xs text-zinc-500 mt-1 h-4">
                                    {autoMarket ? `Auto-detected (from browser): ${autoMarket}` : "Could not derive market from browser language"}
                                </p>
                            </div>

                            <div className="flex flex-col">
                                <label htmlFor="privacy" className="text-sm font-medium mb-1">Privacy</label>
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
                                <p className="text-xs text-zinc-500 mt-1 h-4">Playlist visibility.</p>
                            </div>
                        </div>

                        {/* Update existing */}
                        <div className="mt-2 w-full border rounded-md p-3">
                            <label className="flex items-center gap-2">
                                <input type="checkbox" checked={updateExisting} onChange={(e) => setUpdateExisting(e.target.checked)} />
                                <span className="text-sm font-medium">Update existing YouTube Music playlist (add new tracks only)</span>
                            </label>
                            {updateExisting && (
                                <Input
                                    className="mt-2"
                                    placeholder="https://music.youtube.com/playlist?list=..."
                                    value={existingPlaylistUrl}
                                    onChange={(e) => setExistingPlaylistUrl(e.target.value)}
                                />
                            )}
                        </div>

                        {/* Clone */}
                        <AlertDialog open={dialogOpen} onOpenChange={setdialogOpen}>
                            <AlertDialogTrigger asChild>
                                <Button disabled={isCloneDisabled} className="w-full mt-4" onClick={clonePlaylist}>Clone Playlist</Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Cloning playlist...</AlertDialogTitle>
                                    <AlertDialogDescription>This may take a few minutes.</AlertDialogDescription>
                                </AlertDialogHeader>
                            </AlertDialogContent>
                        </AlertDialog>

                        {/* Success prompt */}
                        <AlertDialog open={starPrompt} onOpenChange={setStarPrompt}>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>
                                        <div className="flex items-center"><CheckIcon />Your Playlist has been cloned!</div>
                                    </AlertDialogTitle>
                                    <AlertDialogDescription>
                                        <div className="ml-12 mb-2">
                                            <p>Please consider starring the project on{" "}
                                                <a href="https://github.com/niscz/SpotiTransFair" target="_blank" rel="noopener noreferrer" className="hover:underline">GitHub</a>.
                                            </p>
                                            <p>It's free and helps me a lot!</p>
                                        </div>
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <div className="flex items-center justify-between w-full">
                                        <Button asChild>
                                            <a className="w-full flex items-center gap-2" href="https://github.com/niscz/SpotiTransFair" target="_blank" rel="noopener noreferrer">
                                                ⭐ on GitHub <FaGithub className="w-6 h-6" />
                                            </a>
                                        </Button>
                                        <AlertDialogAction>Clone Another Playlist</AlertDialogAction>
                                    </div>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>
                </div>

                {/* Error dialogs */}
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

                {/* Missed tracks dialog (with filter + suggestions) */}
                <AlertDialog open={missedTracksDialog} onOpenChange={setMissedTracksDialog}>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Transfer Report</AlertDialogTitle>
                            <AlertDialogDescription asChild>
                                <div className="mt-2 text-foreground">
                                    {missedTracks.length > 0 && (
                                        <>
                                            <p className="mb-2 font-medium">
                                                {missedTracks.filter(t => t.status !== 'success').length} tracks couldn't be found. Edit the query, choose a filter and retry. You can add a suggestion directly.
                                            </p>
                                            <div className="max-h-[300px] overflow-y-auto space-y-3 pr-2 border-b pb-4 mb-4">
                                                {missedTracks.map((track, index) => (
                                                    <div key={index} className="flex flex-col gap-2 border rounded-md p-2">
                                                        <div className="flex items-center gap-2">
                                                            <select
                                                                className="border rounded-md px-2 py-1 text-sm bg-background"
                                                                value={track.filter}
                                                                onChange={(e) => {
                                                                    const final = [...missedTracks];
                                                                    final[index].filter = e.target.value as YtmFilter;
                                                                    setMissedTracks(final);
                                                                }}
                                                            >
                                                                <option value="songs">Songs</option>
                                                                <option value="videos">Videos</option>
                                                                <option value="uploads">Uploads</option>
                                                            </select>
                                                            <Input
                                                                value={track.editedQuery}
                                                                onChange={(e) => {
                                                                    const newTracks = [...missedTracks];
                                                                    newTracks[index].editedQuery = e.target.value;
                                                                    if (newTracks[index].status === 'failed') newTracks[index].status = 'pending';
                                                                    setMissedTracks(newTracks);
                                                                }}
                                                                className="text-sm flex-grow bg-zinc-100 dark:bg-zinc-800"
                                                                disabled={track.status === 'success'}
                                                            />
                                                            {track.status === 'pending' && <Button size="sm" onClick={() => retrySearch(index)}>Search</Button>}
                                                            {track.status === 'retrying' && <Button size="sm" disabled><LuLoader className="animate-spin" /></Button>}
                                                            {track.status === 'success' && <div className="text-green-500"><CheckIcon /></div>}
                                                            {track.status === 'failed' && <Button size="sm" variant="destructive" onClick={() => retrySearch(index)}><LuX /></Button>}
                                                        </div>
                                                        {track.suggestions.length > 0 && (
                                                            <div className="pl-1">
                                                                <p className="text-xs text-zinc-500 mb-1">Suggestions:</p>
                                                                <ul className="space-y-1">
                                                                    {track.suggestions.map((s, i) => (
                                                                        <li key={i} className="flex items-center justify-between text-sm">
                                                                            <span className="truncate">
                                                                                {(s.title || "Unknown Title")} — {(s.artists || []).map(a => a.name).join(", ")}
                                                                            </span>
                                                                            <Button size="sm" variant="secondary" onClick={() => addSuggestion(s.videoId, index)}>Add</Button>
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}
                                    {ignoredDuplicates.count > 0 && (
                                        <>
                                            <p className="mb-2 font-medium">{ignoredDuplicates.count} duplicate tracks were ignored:</p>
                                            <div className="max-h-[150px] overflow-y-auto">
                                                <ul className="list-disc list-inside text-xs text-zinc-500">
                                                    {ignoredDuplicates.items.map((item, i) => <li key={i}>{item}</li>)}
                                                </ul>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogAction onClick={() => { setMissedTracksDialog(false); setStarPrompt(true); }}>
                                Continue
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            </div>
        </>
    );
}
