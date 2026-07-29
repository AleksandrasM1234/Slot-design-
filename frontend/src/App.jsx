import { useEffect, useState } from "react";
import AssetCard from "./AssetCard";

const emptyAsset = {
  name: "",
  category: "symbol",
  description: "",
  enhanced_prompt: "",
  style_keywords: "",
  generation_type: "image",
  model_id: "",
  width: 768,
  height: 768,
  duration_seconds: 4,
  num_outputs: 1,
  jobId: null,
};

export default function App() {
  const [gameName, setGameName] = useState("");
  const [artStyle, setArtStyle] = useState("");
  const [palette, setPalette] = useState("");
  const [assets, setAssets] = useState([{ ...emptyAsset }]);
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
      enhanced_prompt: a.enhanced_prompt || null,
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
        enhanced_prompt: a.enhanced_prompt || "",
        style_keywords: a.style_keywords.join(", "),
        generation_type: a.settings.generation_type,
        model_id: "",
        width: a.settings.width,
        height: a.settings.height,
        duration_seconds: a.settings.duration_seconds ?? 4,
        num_outputs: a.settings.num_outputs,
        jobId: null,
      }))
    );
  };

  const enhancePrompt = async (index) => {
    const asset = assets[index];
    const res = await fetch("http://localhost:8000/prompts/enhance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_prompt: asset.description,
        art_style: artStyle,
        palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
        category: asset.category,
        is_animation: asset.generation_type === "animation",
      }),
    });
    const data = await res.json();
    updateAsset(index, "enhanced_prompt", data.enhanced_prompt);
  };

  const submitAsset = async (index) => {
    const assetForm = assets[index];
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
    updateAsset(index, "jobId", data.job_id);
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
        <button className="border rounded p-2 bg-gray-200" onClick={addAssetRow}>
          + Add asset
        </button>
      </div>

      <div className="grid grid-cols-6 gap-3">
        {assets.map((asset, i) => (
          <AssetCard
            key={i}
            asset={asset}
            index={i}
            updateAsset={updateAsset}
            enhancePrompt={enhancePrompt}
            submitAsset={submitAsset}
            imageModels={imageModels}
            animationModels={animationModels}
          />
        ))}
      </div>
    </div>
  );
}