export default function StatusBadge({ status }: { status: string }) {
    let color = "secondary";
    if (status === "done") color = "success";
    if (status === "failed") color = "danger";
    if (status === "running" || status === "importing") color = "primary";
    if (status === "waiting_review") color = "warning";
    if (status === "queued") color = "secondary";

    // Capitalize
    const label = status.charAt(0).toUpperCase() + status.slice(1).replace("_", " ");

    return (
        <span className={`badge bg-${color} text-${color}-fg`}>{label}</span>
    );
}
