"use client";
import { useEffect, useRef } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";

export default function CallbackPage() {
    const params = useParams();
    const provider = params.provider;
    const searchParams = useSearchParams();
    const code = searchParams.get("code");
    const router = useRouter();
    const processed = useRef(false);

    useEffect(() => {
        if (!code || !provider || processed.current) return;
        processed.current = true;

        async function exchange() {
            try {
                const res = await fetch(`http://localhost:8001/auth/${provider}/callback`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: code })
                });
                if (res.ok) {
                    router.push("/connect");
                } else {
                    const err = await res.json();
                    alert("Auth failed: " + JSON.stringify(err));
                    router.push("/connect");
                }
            } catch (e) {
                alert("Auth error: " + e);
                router.push("/connect");
            }
        }
        exchange();
    }, [code, provider, router]);

    return (
        <div className="container-tight py-4 text-center">
            <h1>Authenticating {provider}...</h1>
            <div className="progress progress-sm">
                <div className="progress-bar progress-bar-indeterminate"></div>
            </div>
        </div>
    );
}
