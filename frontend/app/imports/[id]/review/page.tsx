"use client";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { IconCheck, IconX, IconArrowLeft } from "@tabler/icons-react";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function ReviewPage() {
  const params = useParams();
  const id = params.id;
  const router = useRouter();
  const { data: items, error } = useSWR(`http://localhost:8001/imports/${id}/review`, fetcher);

  const [decisions, setDecisions] = useState<Record<number, string>>({});

  if (!items) return <div className="p-3">Loading...</div>;
  if (items.length === 0) return <div className="p-3">No items to review. <Link href={`/imports/${id}`}>Back to details</Link></div>;

  const handleDecision = (itemId: number, decision: string) => {
    setDecisions(prev => ({ ...prev, [itemId]: decision }));
  };

  const submit = async () => {
    const payload = {
        decisions: Object.entries(decisions).map(([itemId, decision]) => ({
            item_id: parseInt(itemId),
            decision
        }))
    };

    await fetch(`http://localhost:8001/imports/${id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    router.push(`/imports/${id}`);
  };

  return (
    <div className="container-xl">
        <div className="page-header">
            <div className="row align-items-center">
                <div className="col">
                     <div className="page-pretitle">
                        <Link href={`/imports/${id}`}><IconArrowLeft size={16}/> Back to Job</Link>
                     </div>
                    <h2 className="page-title">Review Matches</h2>
                </div>
                <div className="col-auto">
                    <button className="btn btn-primary" onClick={submit} disabled={Object.keys(decisions).length === 0}>
                        Submit {Object.keys(decisions).length} Decisions
                    </button>
                </div>
            </div>
        </div>

        <div className="page-body">
            <div className="row row-cards">
                {items.map((item: any) => {
                    const decision = decisions[item.id];
                    const cardClass = decision === "confirm" ? "border-success" : decision === "reject" ? "border-danger" : "";

                    return (
                        <div className="col-12" key={item.id}>
                            <div className={`card ${cardClass}`}>
                                <div className="card-body">
                                    <div className="row align-items-center">
                                        <div className="col-md-5">
                                            <div className="text-muted small">Spotify (Source)</div>
                                            <div className="fw-bold">{item.original_track_data.name}</div>
                                            <div>{item.original_track_data.artists.join(", ")}</div>
                                            <div className="text-secondary small">
                                                {(item.original_track_data.duration_ms / 1000).toFixed(0)}s
                                            </div>
                                        </div>

                                        <div className="col-md-2 text-center py-2">
                                            <div className="text-muted small">Score</div>
                                            <div className="h2 mb-0">{(item.match_data?._score * 100).toFixed(0)}%</div>
                                        </div>

                                        <div className="col-md-5">
                                             <div className="text-muted small">Suggested Match</div>
                                             {item.match_data ? (
                                                <>
                                                    <div className="fw-bold">{item.match_data.title}</div>
                                                    <div>{item.match_data.artists.join(", ")}</div>
                                                    <div className="text-secondary small">
                                                        {item.match_data.duration}s
                                                    </div>
                                                </>
                                             ) : (
                                                 <div className="text-danger">No suggestion</div>
                                             )}
                                        </div>
                                    </div>
                                </div>
                                <div className="card-footer">
                                    <div className="d-flex justify-content-end gap-2">
                                        <button
                                            className={`btn ${decision === "reject" ? "btn-danger" : "btn-outline-danger"}`}
                                            onClick={() => handleDecision(item.id, "reject")}
                                        >
                                            <IconX size={16} className="me-1"/> Reject
                                        </button>
                                        <button
                                            className={`btn ${decision === "confirm" ? "btn-success" : "btn-outline-success"}`}
                                             onClick={() => handleDecision(item.id, "confirm")}
                                        >
                                            <IconCheck size={16} className="me-1"/> Confirm
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    </div>
  );
}
