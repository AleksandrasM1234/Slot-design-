import { useEffect, useState } from "react";

export default function AssetWindow({ jobId }) {
  const [status, setStatus] = useState("queued");
  const [resultPaths, setResultPaths] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/assets/${jobId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setResultPaths(data.result_paths || []);
      setError(data.error);
    };
    return () => ws.close();
  }, [jobId]);

  return (
    <div className="border rounded-lg p-4 shadow bg-white">
      <div className="text-xs text-gray-400">{jobId.slice(0, 8)}</div>
      <div className="font-semibold capitalize">{status}</div>
      {error && <div className="text-red-500 text-sm mt-1">{error}</div>}
      <div className="grid grid-cols-2 gap-2 mt-2">
        {resultPaths.map((path) => (
          <img
            key={path}
            src={`http://localhost:8000/${path}`}
            alt={jobId}
            className="rounded w-full"
          />
        ))}
      </div>
    </div>
  );
}