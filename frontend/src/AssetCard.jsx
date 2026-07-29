import { useEffect, useState } from "react";

const CATEGORIES = [
  "wild", "scatter", "logo", "low_tier", "high_tier",
  "background", "background_character", "ui_element", "frame_animation",
];

const uploadReferenceImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("http://localhost:8000/uploads/reference-image", {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  return data.path;
};

const importAsset = async (name, category, generationType, file) => {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("category", category);
  formData.append("generation_type", generationType);
  formData.append("file", file);

  const res = await fetch("http://localhost:8000/assets/import", {
    method: "POST",
    body: formData,
  });
  return res.json();
};

export default function AssetCard({
  asset, index, updateAsset, enhancePrompt, submitAsset,
  imageModels, animationModels,
}) {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState(null);
  const [resultPaths, setResultPaths] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!asset.jobId) return;
    const ws = new WebSocket(`ws://localhost:8000/ws/assets/${asset.jobId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setResultPaths(data.result_paths || []);
      setError(data.error);
    };
    return () => ws.close();
  }, [asset.jobId]);

  const modelOptions = asset.generation_type === "animation" ? animationModels : imageModels;

  if (!expanded) {
    return (
      <div
        className="border rounded-lg p-3 bg-white shadow cursor-pointer hover:shadow-md transition"
        onClick={() => setExpanded(true)}
      >
        <div className="text-xs text-gray-400 uppercase">{asset.category || "—"}</div>
        <div className="font-semibold truncate">{asset.name || "Untitled asset"}</div>
        {status && <div className="text-xs mt-1 capitalize text-blue-600">{status}</div>}
        {resultPaths[0] && (
          <img
            src={`http://localhost:8000/${resultPaths[0]}`}
            alt={asset.name}
            className="mt-2 rounded w-full h-20 object-cover"
          />
        )}
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={() => setExpanded(false)}
    >
      <div
        className="bg-white rounded-lg p-6 w-[70vw] h-[70vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">{asset.name || "Untitled asset"}</h3>
          <button className="text-gray-500" onClick={() => setExpanded(false)}>✕ Close</button>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-2">
          <input className="border rounded p-2" placeholder="Name"
            value={asset.name} onChange={(e) => updateAsset(index, "name", e.target.value)} />
          <select className="border rounded p-2" value={asset.category}
            onChange={(e) => updateAsset(index, "category", e.target.value)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select className="border rounded p-2" value={asset.generation_type}
            onChange={(e) => {
              updateAsset(index, "generation_type", e.target.value);
              updateAsset(index, "model_id", "");
            }}>
            <option value="image">image</option>
            <option value="animation">animation</option>
          </select>
          <input className="border rounded p-2" type="number" min="1" max="8"
            placeholder="Number of generations" value={asset.num_outputs}
            onChange={(e) => updateAsset(index, "num_outputs", e.target.value)} />
        </div>

        <textarea className="border rounded p-2 w-full mb-2" rows={2}
          placeholder="Base description (your own words)"
          value={asset.description}
          onChange={(e) => updateAsset(index, "description", e.target.value)} />

        <div className="flex gap-2 items-start mb-2">
          <textarea className="border rounded p-2 w-full" rows={2}
            placeholder="AI-enhanced prompt (editable — this is what actually gets sent)"
            value={asset.enhanced_prompt}
            onChange={(e) => updateAsset(index, "enhanced_prompt", e.target.value)} />
          <button className="border rounded p-2 bg-gray-200 whitespace-nowrap"
            onClick={() => enhancePrompt(index)}>
            Enhance ✨
          </button>
        </div>
            <div className="mb-2">
                <label className="text-sm text-gray-600 block mb-1">
                    Reference image {asset.generation_type === "animation" ? "(first frame)" : "(style guide)"}
                </label>
                <div className="flex gap-2 items-center">
                 <input
                    type="file"
                    accept="image/*"
                    className="text-sm"
                    onChange={async (e) => {
                        const file = e.target.files[0];
                        if (!file) return;
                        const path = await uploadReferenceImage(file);
                        updateAsset(index, "reference_image_path", path);
                        }}
                />
                {asset.reference_image_path && (
                    <img
                        src={`http://localhost:8000/${asset.reference_image_path}`}
                        alt="reference"
                       className="w-12 h-12 object-cover rounded border"
                    />
                )}
            </div>
        </div>
        <div className="grid grid-cols-4 gap-2 mb-2">
          <select className="border rounded p-2" value={asset.model_id}
            onChange={(e) => updateAsset(index, "model_id", e.target.value)}>
            <option value="">— Select model —</option>
            {modelOptions.map((m) => (
              <option key={m.model_id} value={m.model_id}>{m.name}</option>
            ))}
          </select>
          <input className="border rounded p-2" type="number" placeholder="Width"
            value={asset.width} onChange={(e) => updateAsset(index, "width", e.target.value)} />
          <input className="border rounded p-2" type="number" placeholder="Height"
            value={asset.height} onChange={(e) => updateAsset(index, "height", e.target.value)} />
          {asset.generation_type === "animation" && (
            <input className="border rounded p-2" type="number" step="0.5"
              placeholder="Duration (sec)" value={asset.duration_seconds}
              onChange={(e) => updateAsset(index, "duration_seconds", e.target.value)} />
          )}
        </div>

        <button className="border rounded p-2 bg-blue-500 text-white w-full mb-4"
          onClick={() => submitAsset(index)}>
          Generate
        </button>

        <div className="border-t pt-3 mb-4">
            <label className="text-sm text-gray-600 block mb-1">
             Or import an already-made asset (skips generation)
            </label>
            <input
                type="file"
                accept={asset.generation_type === "animation" ? "video/*,image/gif" : "image/*"}
                className="text-sm"
                onChange={async (e) => {
                    const file = e.target.files[0];
                     if (!file) return;
                     const result = await importAsset(
                         asset.name || "imported_asset",
                         asset.category,
                         asset.generation_type,
                         file
                        );
                        setStatus("done");
                        setResultPaths(result.result_paths);
                        updateAsset(index, "jobId", result.job_id);
                }}
            />
        </div>

        {status && (
          <div className="mb-2">
            <div className="text-sm font-semibold capitalize">{status}</div>
            {error && <div className="text-red-500 text-sm">{error}</div>}
          </div>
        )}

        <div className="grid grid-cols-3 gap-2">
          {resultPaths.map((path) => (
            <img key={path} src={`http://localhost:8000/${path}`}
              alt={asset.name} className="rounded w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}