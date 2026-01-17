import { IconCheck, IconX } from "@tabler/icons-react";
import React from "react";

interface ProviderCardProps {
    title: string;
    connected: boolean;
    children?: React.ReactNode;
}

export default function ProviderCard({ title, connected, children }: ProviderCardProps) {
    return (
        <div className="card">
            <div className="card-header">
                <h3 className="card-title">{title}</h3>
                <div className="card-actions">
                    {connected ? (
                        <span className="text-success d-flex align-items-center gap-1"><IconCheck size={16} /> Connected</span>
                    ) : (
                        <span className="text-muted d-flex align-items-center gap-1"><IconX size={16} /> Not Connected</span>
                    )}
                </div>
            </div>
            <div className="card-body">
                {children}
            </div>
        </div>
    );
}
