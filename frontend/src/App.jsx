import { useEffect, useState } from "react";
import AssetWindow from "./AssetWindow";

const emptyAsset = {
  name: "",
  category: "symbol",
  description: "",
  style_keywords: "",
  generation_type: "image",
  model_id: "",
  width: 768,
  height: 768,
  duration_seconds: 4,
  num_outputs: 1,
};

const CATEGORIES = [
  "wild", "scatter", "logo", "low_tier", "high_tier",
  "background", "background_character", "ui_element", "frame_animation",
];

export default function App() {
  const [gameName, setGameName] = useState("");
  const [artStyle, setArtStyle] = useState("");
  const [palette, setPalette] = useState("");
  const [assets, setAssets] = useState([{ ...emptyAsset }]);
  const [assetIds, setAssetIds] = useState([]);
  const [savedThemeNames, setSavedThemeNames] = useState([]);
  const [selectedThemeName, setSelectedThemeName] = useState("");
  const [imageModels, setImageModels] = useState([]);
  const [animationModels, setAnimationModels] = useState([]);

  useEffect(() => {
    refreshThemeList();
    refreshModelList();
  }, []);

  const refreshModelList = async () => {
    const res = await fetch("http://localhost:8000/models");
    const data = await res.json();
    setImageModels(data.image);
    setAnimationModels(data.animation);
  };

  const updateAsset = (index, field, value) => {
    setAssets((prev) =>
      prev.map((a, i) => (i === index ? { ...a, [field]: value } : a))
    );
  };

  const addAssetRow = () => setAssets((prev) => [...prev, { ...emptyAsset }]);

  const buildThemePayload = () => ({
    name: gameName,
    art_style: artStyle,
    palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
    assets: assets.map((a) => ({
      name: a.name,
      category: a.category,
      description: a.description,
      style_keywords: a.style_keywords.split(",").map((k) => k.trim()).filter(Boolean),
      settings: {
        generation_type: a.generation_type,
        width: Number(a.width),
        height: Number(a.height),
        duration_seconds: a.generation_type === "animation" ? Number(a.duration_seconds) : null,
        num_outputs: Number(a.num_outputs),
      },
    })),
  });

  const refreshThemeList = async () => {
    const res = await fetch("http://localhost:8000/themes");
    setSavedThemeNames(await res.json());
  };

  const saveTheme = async () => {
    const theme = buildThemePayload();
    await fetch("http://localhost:8000/themes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    });
    await refreshThemeList();
  };

  const loadTheme = async (name) => {
    const res = await fetch(`http://localhost:8000/themes/${name}`);
    const theme = await res.json();
    setGameName(theme.name);
    setArtStyle(theme.art_style);
    setPalette(theme.palette.join(", "));
    setAssets(
      theme.assets.map((a) => ({
        name: a.name,
        category: a.category,
        description: a.description,
        style_keywords: a.style_keywords.join(", "),
        generation_type: a.settings.generation_type,
        model_id: "",
        width: a.settings.width,
        height: a.settings.height,
        duration_seconds: a.settings.duration_seconds ?? 4,
        num_outputs: a.settings.num_outputs,
      }))
    );
  };

  const submitAsset = async (assetForm) => {
    const theme = buildThemePayload();

    const res = await fetch("http://localhost:8000/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        theme,
        asset_name: assetForm.name,
        model_id: assetForm.model_id,
      }),
    });
    const data = await res.json();
    setAssetIds((prev) => [...prev, data.job_id]);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Slot Asset Generator</h1>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <input className="border rounded p-2" placeholder="Game name"
          value={gameName} onChange={(e) => setGameName(e.target.value)} />
        <input className="border rounded p-2" placeholder="Art style"
          value={artStyle} onChange={(e) => setArtStyle(e.target.value)} />
        <input className="border rounded p-2 col-span-2" placeholder="Palette, comma separated"
          value={palette} onChange={(e) => setPalette(e.target.value)} />
      </div>

      <div className="flex gap-2 items-center mb-4">
        <select
          className="border rounded p-2 flex-1"
          value={selectedThemeName}
          onChange={(e) => {
            setSelectedThemeName(e.target.value);
            if (e.target.value) loadTheme(e.target.value);
          }}
        >
          <option value="">— Load a saved theme —</option>
          {savedThemeNames.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <button className="border rounded p-2 bg-gray-200" onClick={saveTheme}>
          Save current theme
        </button>
      </div>

      <h2 className="font-semibold mb-2">Assets</h2>
      {assets.map((a, i) => {
        const modelOptions = a.generation_type === "animation" ? animationModels : imageModels;
        return (
          <div key={i} className="border rounded p-3 mb-3 bg-gray-50">
            <div className="grid grid-cols-4 gap-2 mb-2">
              <input className="border rounded p-2" placeholder="Name"
                value={a.name} onChange={(e) => updateAsset(i, "name", e.target.value)} />
              <select className="border rounded p-2" value={a.category}
                onChange={(e) => updateAsset(i, "category", e.target.value)}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="border rounded p-2" value={a.generation_type}
                onChange={(e) => {
                  updateAsset(i, "generation_type", e.target.value);
                  updateAsset(i, "model_id", "");
                }}>
                <option value="image">image</option>
                <option value="animation">animation</option>
              </select>
              <input className="border rounded p-2" type="number" min="1" max="8"
                placeholder="Number of generations" value={a.num_outputs}
                onChange={(e) => updateAsset(i, "num_outputs", e.target.value)} />
            </div>

            <input className="border rounded p-2 w-full mb-2" placeholder="Description"
              value={a.description} onChange={(e) => updateAsset(i, "description", e.target.value)} />

            <div className="grid grid-cols-4 gap-2">
              <select className="border rounded p-2" value={a.model_id}
                onChange={(e) => updateAsset(i, "model_id", e.target.value)}>
                <option value="">— Select model —</option>
                {modelOptions.map((m) => (
                  <option key={m.model_id} value={m.model_id}>{m.name}</option>
                ))}
              </select>
              <input className="border rounded p-2" type="number" placeholder="Width"
                value={a.width} onChange={(e) => updateAsset(i, "width", e.target.value)} />
              <input className="border rounded p-2" type="number" placeholder="Height"
                value={a.height} onChange={(e) => updateAsset(i, "height", e.target.value)} />
              {a.generation_type === "animation" ? (
                <input className="border rounded p-2" type="number" step="0.5"
                  placeholder="Duration (sec)" value={a.duration_seconds}
                  onChange={(e) => updateAsset(i, "duration_seconds", e.target.value)} />
              ) : (
                <button className="border rounded p-2 bg-blue-500 text-white"
                  onClick={() => submitAsset(a)}>
                  Generate
                </button>
              )}
            </div>
            {a.generation_type === "animation" && (
              <button className="border rounded p-2 bg-blue-500 text-white w-full mt-2"
                onClick={() => submitAsset(a)}>
                Generate
              </button>
            )}
          </div>
        );
      })}
      <button className="text-sm text-blue-600 mb-6" onClick={addAssetRow}>
        + Add another asset
      </button>

      <h2 className="font-semibold mb-2">Generated assets</h2>
      <div className="grid grid-cols-3 gap-4">
        {assetIds.map((id) => (
          <AssetWindow key={id} jobId={id} />
        ))}
      </div>
    </div>
  );
}