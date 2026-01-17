"use client";
import useSWR from "swr";
import { useState } from "react";
import ProviderCard from "@/components/ProviderCard";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function ConnectPage() {
  const { data: connections, mutate } = useSWR("http://localhost:8001/user/connections", fetcher);
  const [ytmHeaders, setYtmHeaders] = useState("");
  const [ytmLoading, setYtmLoading] = useState(false);
  const [ytmError, setYtmError] = useState("");

  const handleOAuth = async (provider: string) => {
    const res = await fetch(`http://localhost:8001/auth/${provider}/login`);
    const data = await res.json();
    if (data.url) {
        window.location.href = data.url;
    }
  };

  const handleYTMSubmit = async () => {
    setYtmLoading(true);
    setYtmError("");
    try {
        const res = await fetch("http://localhost:8001/auth/ytm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ headers: ytmHeaders })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed");
        }
        setYtmHeaders("");
        mutate();
    } catch (e: any) {
        setYtmError(e.message);
    } finally {
        setYtmLoading(false);
    }
  };

  if (!connections) return <div className="p-3">Loading...</div>;

  return (
    <div className="container-xl">
      <div className="page-header d-print-none">
        <h2 className="page-title">Connect Providers</h2>
      </div>
      <div className="page-body">
        <div className="row row-cards">
            {/* Spotify */}
            <div className="col-md-4">
                <ProviderCard title="Spotify" connected={connections.spotify}>
                    {!connections.spotify && (
                        <button className="btn btn-success w-100" onClick={() => handleOAuth("spotify")}>
                            Connect Spotify
                        </button>
                    )}
                    {connections.spotify && (
                        <div className="text-muted">Authentication valid.</div>
                    )}
                </ProviderCard>
            </div>

            {/* TIDAL */}
            <div className="col-md-4">
                <ProviderCard title="TIDAL" connected={connections.tidal}>
                    {!connections.tidal && (
                        <button className="btn btn-dark w-100" onClick={() => handleOAuth("tidal")}>
                            Connect TIDAL
                        </button>
                    )}
                     {connections.tidal && (
                        <div className="text-muted">Authentication valid.</div>
                    )}
                </ProviderCard>
            </div>

             {/* YTM */}
             <div className="col-md-4">
                <ProviderCard title="YouTube Music" connected={connections.ytm}>
                    {connections.ytm ? (
                         <div className="text-muted">Headers valid. You can update them below if needed.</div>
                    ) : (
                        <div className="text-muted mb-2">Please paste your raw headers (Cookie, etc.) from the browser.</div>
                    )}

                    <textarea
                        className="form-control mb-2"
                        rows={5}
                        placeholder="Paste headers here..."
                        value={ytmHeaders}
                        onChange={(e) => setYtmHeaders(e.target.value)}
                    ></textarea>

                    {ytmError && <div className="text-danger mb-2">{ytmError}</div>}

                    <button className="btn btn-primary w-100" onClick={handleYTMSubmit} disabled={ytmLoading}>
                        {ytmLoading ? "Verifying..." : "Save Headers"}
                    </button>
                </ProviderCard>
            </div>
        </div>
      </div>
    </div>
  );
}
