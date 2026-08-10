import { useEffect, useState } from "react";

const CATEGORIES = [
  "wild", "scatter", "logo", "low_tier", "high_tier", "symbol",
  "hold_and_win", "background", "background_character", "ui_element",
  "animation", "frame_animation",
];

const STAGES = ["queued", "generating", "postprocessing", "done"];

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

function ProgressBar({ status }) {
  if (status === "failed") {
    return <div className="text-red-500 text-xs font-semibold">Failed</div>;
  }
  const currentIndex = STAGES.indexOf(status);
  const percent = currentIndex >= 0 ? ((currentIndex + 1) / STAGES.length) * 100 : 0;

  return (
    <div className="mt-2">
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${
            status === "done" ? "bg-green-500" : "bg-blue-500 animate-pulse"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="text-xs text-gray-500 mt-1 capitalize">{status}</div>
    </div>
  );
}

function ResolutionControl({ asset, index, updateAsset, selectedModel }) {
  if (!selectedModel) {
    return (
      <div className="col-span-2 text-sm text-gray-400 flex items-center">
        Select a model to set resolution
      </div>
    );
  }

  if (selectedModel.resolution_mode === "enumerated") {
    const options = selectedModel.valid_resolutions;
    const currentValue = `${asset.width}x${asset.height}`;

    return (
      <select
        className="border rounded p-2 col-span-2"
        value={currentValue}
        onChange={(e) => {
          const [w, h] = e.target.value.split("x").map(Number);
          updateAsset(index, "width", w);
          updateAsset(index, "height", h);
        }}
      >
        <option value="">— Select resolution —</option>
        {options.map((r) => (
          <option key={`${r.width}x${r.height}`} value={`${r.width}x${r.height}`}>
            {r.ratio} — {r.width} × {r.height}
          </option>
        ))}
      </select>
    );
  }

  return (
    <>
      <input
        className="border rounded p-2"
        type="number"
        placeholder="Width"
        min={selectedModel.min_width}
        max={selectedModel.max_width}
        step={selectedModel.step}
        value={asset.width}
        onChange={(e) => updateAsset(index, "width", e.target.value)}
      />
      <input
        className="border rounded p-2"
        type="number"
        placeholder="Height"
        min={selectedModel.min_height}
        max={selectedModel.max_height}
        step={selectedModel.step}
        value={asset.height}
        onChange={(e) => updateAsset(index, "height", e.target.value)}
      />
    </>
  );
}

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

    const fetchCurrentStatus = async () => {
      const res = await fetch(`http://localhost:8000/assets/${asset.jobId}`);
      if (!res.ok) return;
      const data = await res.json();
      setStatus(data.status);
      setResultPaths(data.result_paths || []);
      setError(data.error);
    };
    fetchCurrentStatus();

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
  const selectedModel = modelOptions.find((m) => m.model_id === asset.model_id) || null;

  if (!expanded) {
    return (
      <div
        className="border rounded-lg p-3 bg-white shadow cursor-pointer hover:shadow-md transition"
        onClick={() => setExpanded(true)}
      >
        <div className="text-xs text-gray-400 uppercase">{asset.category || "—"}</div>
        <div className="font-semibold truncate">{asset.name || "Untitled asset"}</div>
        {status && status !== "done" && <ProgressBar status={status} />}
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
            onChange={(e) => {
              updateAsset(index, "model_id", e.target.value);
              const model = modelOptions.find((m) => m.model_id === e.target.value);
              if (model) {
                if (model.resolution_mode === "enumerated" && model.valid_resolutions.length > 0) {
                  updateAsset(index, "width", model.valid_resolutions[0].width);
                  updateAsset(index, "height", model.valid_resolutions[0].height);
                }
                if (model.min_duration != null) {
                  updateAsset(index, "duration_seconds", model.min_duration);
                }
              }
            }}>
            <option value="">— Select model —</option>
            {modelOptions.map((m) => (
              <option key={m.model_id} value={m.model_id}>{m.name}</option>
            ))}
          </select>

          <ResolutionControl
            asset={asset}
            index={index}
            updateAsset={updateAsset}
            selectedModel={selectedModel}
          />

          {asset.generation_type === "animation" && (
            <input
              className="border rounded p-2"
              type="number"
              step="0.5"
              placeholder="Duration (sec)"
              min={selectedModel?.min_duration ?? undefined}
              max={selectedModel?.max_duration ?? undefined}
              value={asset.duration_seconds}
              onChange={(e) => updateAsset(index, "duration_seconds", e.target.value)}
            />
          )}
        </div>

        {selectedModel?.min_duration != null && (
          <div className="text-xs text-gray-400 mb-2">
            Duration must be between {selectedModel.min_duration}s and {selectedModel.max_duration}s
          </div>
        )}

        <button className="border rounded p-2 bg-blue-500 text-white w-full mb-2"
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
            <ProgressBar status={status} />
            {error && <div className="text-red-500 text-sm mt-1">{error}</div>}
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