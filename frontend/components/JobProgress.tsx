export default function JobProgress({ stats }: { stats: any }) {
    if (!stats) return null;
    const { total, matched, uncertain, failed } = stats;
    // Avoid division by zero
    if (total === 0) return (
        <div className="progress progress-xl">
             <div className="progress-bar" style={{ width: "0%" }}></div>
        </div>
    );

    const pMatched = (matched / total) * 100;
    const pUncertain = (uncertain / total) * 100;
    const pFailed = (failed / total) * 100;

    return (
        <div className="progress progress-xl">
            <div className="progress-bar bg-success" style={{ width: `${pMatched}%` }} role="progressbar" aria-label="Matched" title={`Matched: ${matched}`} />
            <div className="progress-bar bg-warning" style={{ width: `${pUncertain}%` }} role="progressbar" aria-label="Uncertain" title={`Uncertain: ${uncertain}`} />
            <div className="progress-bar bg-danger" style={{ width: `${pFailed}%` }} role="progressbar" aria-label="Failed" title={`Failed: ${failed}`} />
        </div>
    );
}
