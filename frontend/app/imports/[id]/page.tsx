"use client";
import useSWR from "swr";
import { useParams } from "next/navigation";
import StatusBadge from "@/components/StatusBadge";
import JobProgress from "@/components/JobProgress";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function ImportDetailsPage() {
  const params = useParams();
  const id = params.id; // Next.js App Router params
  const { data, error, mutate } = useSWR(`http://localhost:8001/imports/${id}`, fetcher, { refreshInterval: 2000 });

  if (!data) return <div className="p-3">Loading...</div>;
  if (error) return <div className="p-3 text-danger">Error loading job details</div>;

  const { job, stats } = data;

  const handleFinalize = async () => {
      if(!confirm("Are you sure you want to finalize? Any uncertain matches not reviewed will be skipped.")) return;
      await fetch(`http://localhost:8001/imports/${id}/finalize`, { method: "POST" });
      mutate();
  };

  return (
    <div className="container-xl">
       <div className="page-header">
           <div className="row align-items-center">
               <div className="col">
                   <div className="page-pretitle">Import Job</div>
                   <h2 className="page-title">{job.source_playlist_name || job.source_playlist_id}</h2>
               </div>
               <div className="col-auto">
                   <StatusBadge status={job.status} />
               </div>
           </div>
       </div>

       <div className="page-body">
            <div className="card mb-3">
                <div className="card-body">
                    <h3 className="card-title">Progress</h3>
                    <JobProgress stats={stats} />
                    <div className="mt-3 row text-center">
                        <div className="col">
                            <div className="text-muted">Total</div>
                            <div className="h2">{stats.total}</div>
                        </div>
                        <div className="col">
                            <div className="text-muted">Matched</div>
                            <div className="h2 text-success">{stats.matched}</div>
                        </div>
                         <div className="col">
                            <div className="text-muted">Uncertain</div>
                            <div className="h2 text-warning">{stats.uncertain}</div>
                        </div>
                         <div className="col">
                            <div className="text-muted">Failed</div>
                            <div className="h2 text-danger">{stats.failed}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="d-flex gap-2">
                {job.status === "waiting_review" && (
                    <>
                        <Link href={`/imports/${id}/review`} className="btn btn-warning">
                            Review Matches ({stats.uncertain})
                        </Link>
                        <button className="btn btn-success" onClick={handleFinalize}>
                            Finalize Import
                        </button>
                    </>
                )}

                {job.target_playlist_id && (
                    <a href={job.target_provider === "tidal" ? `https://listen.tidal.com/playlist/${job.target_playlist_id}` : `https://music.youtube.com/playlist?list=${job.target_playlist_id}`} target="_blank" className="btn btn-primary">
                        Open in {job.target_provider.toUpperCase()}
                    </a>
                )}
            </div>

            {job.error_message && (
                <div className="alert alert-danger mt-3">
                    {job.error_message}
                </div>
            )}
       </div>
    </div>
  );
}
