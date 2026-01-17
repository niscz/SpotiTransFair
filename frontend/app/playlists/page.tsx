"use client";
import useSWR from "swr";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { IconBrandTidal, IconBrandYoutube } from "@tabler/icons-react";

const fetcher = (url: string) => fetch(url).then((res) => {
    if (!res.ok) throw new Error("Failed");
    return res.json();
});

export default function PlaylistsPage() {
  const { data: playlists, error } = useSWR("http://localhost:8001/playlists", fetcher);
  const [selected, setSelected] = useState<string[]>([]);
  const router = useRouter();

  const toggleSelect = (id: string) => {
    if (selected.includes(id)) setSelected(selected.filter(s => s !== id));
    else setSelected([...selected, id]);
  };

  const handleImport = async (target: string) => {
    if (selected.length === 0) return;

    // Create jobs
    for (const pid of selected) {
        await fetch("http://localhost:8001/imports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ playlist_id: pid, target_provider: target })
        });
    }

    router.push("/");
  };

  if (error) return <div className="p-3 text-danger">Error loading playlists. Please ensure you are connected to Spotify in the Connect page.</div>;
  if (!playlists) return <div className="p-3">Loading playlists...</div>;

  return (
    <div className="container-xl">
      <div className="page-header d-print-none">
        <div className="row g-2 align-items-center">
            <div className="col">
                <h2 className="page-title">Select Playlists</h2>
            </div>
             <div className="col-auto ms-auto d-print-none d-flex gap-2">
                <button className="btn btn-dark" disabled={selected.length===0} onClick={() => handleImport("tidal")}>
                    <IconBrandTidal size={18} className="me-2"/> Import to TIDAL
                </button>
                <button className="btn btn-danger" disabled={selected.length===0} onClick={() => handleImport("ytm")}>
                    <IconBrandYoutube size={18} className="me-2"/> Import to YTM
                </button>
             </div>
        </div>
      </div>

      <div className="page-body">
         <div className="card">
            <div className="table-responsive">
                <table className="table table-vcenter card-table">
                    <thead>
                        <tr>
                            <th className="w-1"><input type="checkbox" className="form-check-input"
                                onChange={(e) => {
                                    if (e.target.checked) setSelected(playlists.map((p: any) => p.id));
                                    else setSelected([]);
                                }}
                                checked={selected.length === playlists.length && playlists.length > 0}
                            /></th>
                            <th>Name</th>
                            <th>Tracks</th>
                            <th>ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {playlists.map((p: any) => (
                            <tr key={p.id}>
                                <td>
                                    <input type="checkbox" className="form-check-input"
                                        checked={selected.includes(p.id)}
                                        onChange={() => toggleSelect(p.id)}
                                    />
                                </td>
                                <td>
                                    {p.image && <img src={p.image} alt="" className="avatar me-2" />}
                                    {p.name}
                                </td>
                                <td>{p.tracks}</td>
                                <td className="text-muted">{p.id}</td>
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
