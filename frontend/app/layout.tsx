import "@tabler/core/dist/css/tabler.min.css";
import "./globals.css";
import Link from "next/link";
import { IconHome, IconLink, IconPlaylist } from "@tabler/icons-react";

export const metadata = {
  title: "SpotiTransFair",
  description: "Migrate Spotify Playlists to TIDAL/YTM",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased theme-light">
        <div className="page">
          {/* Sidebar */}
          <aside className="navbar navbar-vertical navbar-expand-lg navbar-dark">
            <div className="container-fluid">
              <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#sidebar-menu" aria-controls="sidebar-menu" aria-expanded="false" aria-label="Toggle navigation">
                <span className="navbar-toggler-icon"></span>
              </button>
              <h1 className="navbar-brand navbar-brand-autodark">
                <Link href="/">
                  SpotiTransFair
                </Link>
              </h1>
              <div className="collapse navbar-collapse" id="sidebar-menu">
                <ul className="navbar-nav pt-lg-3">
                  <li className="nav-item">
                    <Link className="nav-link" href="/">
                      <span className="nav-link-icon d-md-none d-lg-inline-block">
                        <IconHome />
                      </span>
                      <span className="nav-link-title">Dashboard</span>
                    </Link>
                  </li>
                  <li className="nav-item">
                    <Link className="nav-link" href="/connect">
                      <span className="nav-link-icon d-md-none d-lg-inline-block">
                        <IconLink />
                      </span>
                      <span className="nav-link-title">Connect</span>
                    </Link>
                  </li>
                  <li className="nav-item">
                    <Link className="nav-link" href="/playlists">
                      <span className="nav-link-icon d-md-none d-lg-inline-block">
                        <IconPlaylist />
                      </span>
                      <span className="nav-link-title">Playlists</span>
                    </Link>
                  </li>
                </ul>
              </div>
            </div>
          </aside>

          <div className="page-wrapper">
             {children}
          </div>
        </div>
      </body>
    </html>
  );
}
