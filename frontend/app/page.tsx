"use client";
import useSWR from "swr";
import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { IconPlus } from "@tabler/icons-react";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Dashboard() {
  const { data: jobs, error, isLoading } = useSWR("http://localhost:8001/imports", fetcher, { refreshInterval: 5000 });

  if (error) return <div className="p-3 text-danger">Failed to load jobs</div>;
  if (isLoading) return <div className="p-3">Loading...</div>;

  return (
    <div className="container-xl">
      <div className="page-header d-print-none">
        <div className="row g-2 align-items-center">
          <div className="col">
            <h2 className="page-title">Dashboard</h2>
          </div>
          <div className="col-auto ms-auto d-print-none">
            <Link href="/playlists" className="btn btn-primary d-none d-sm-inline-block">
              <IconPlus size={18} /> New Import
            </Link>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="card">
          <div className="table-responsive">
            <table className="table table-vcenter card-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Target</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th className="w-1"></th>
                </tr>
              </thead>
              <tbody>
                {jobs.length === 0 && (
                    <tr><td colSpan={5} className="text-center p-3">No imports yet.</td></tr>
                )}
                {jobs.map((job: any) => (
                  <tr key={job.id}>
                    <td>{job.source_playlist_name || job.source_playlist_id}</td>
                    <td>{job.target_provider}</td>
                    <td className="text-secondary">{new Date(job.created_at).toLocaleString()}</td>
                    <td><StatusBadge status={job.status} /></td>
                    <td>
                      <Link href={`/imports/${job.id}`}>Details</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
