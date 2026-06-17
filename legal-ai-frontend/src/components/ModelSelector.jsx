import React, { useEffect, useState } from "react";
import {
  getAvailableModels,
  selectModel,
  getModelRecommendations,
  getEvaluationSummary,
  setLocalItem,
} from "@/lib/api";

export default function ModelSelector({ onModelChange, onLogout }) {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [recommendations, setRecommendations] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [evalSummary, setEvalSummary] = useState(null);
  const [evalError, setEvalError] = useState("");

  useEffect(() => {
    const loadModelsAndRecommendations = async () => {
      setLoading(true);
      setError("");

      try {
        const modelsResult = await getAvailableModels();

        if (modelsResult.status === "success" && modelsResult.models) {
          setModels(modelsResult.models);
          setSelectedModel(modelsResult.current_selection);
          if (modelsResult.current_selection) {
            setLocalItem("selectedOllamaModel", modelsResult.current_selection);
          }
        } else {
          setError("Failed to fetch models from Ollama");
        }

        const recsResult = await getModelRecommendations();
        if (recsResult.status === "success") {
          setRecommendations(recsResult.recommendations);
        }
      } catch (err) {
        console.error("Error loading models:", err);
        setError("Failed to load model information");
      } finally {
        setLoading(false);
      }
    };

    loadModelsAndRecommendations();
  }, []);

  useEffect(() => {
    const loadEvaluationSummary = async () => {
      try {
        const result = await getEvaluationSummary(30, "lq-rag-v2");
        setEvalSummary(result);
        setEvalError("");
      } catch (err) {
        setEvalError(err.message || "Failed to load evaluation summary");
      }
    };
    loadEvaluationSummary();
  }, []);

  const handleModelSelection = async (modelName) => {
    try {
      setLoading(true);
      setError("");

      const result = await selectModel(modelName);

      if (result.status === "success") {
        setSelectedModel(modelName);
        setLocalItem("selectedOllamaModel", modelName);
        if (onModelChange) onModelChange(modelName);
      } else {
        setError(`Failed to select model: ${result.error}`);
      }
    } catch (err) {
      console.error("Error selecting model:", err);
      setError("Failed to select model");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    if (!onLogout) return;
    setLogoutLoading(true);
    try {
      await onLogout();
    } finally {
      setLogoutLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="section-title">Model Settings</h3>
        <button
          onClick={() => setShowRecommendations(!showRecommendations)}
          className="text-sm px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded transition-colors"
        >
          {showRecommendations ? "Hide" : "Show"} Recommendations
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-300 rounded text-sm text-red-800">
          {error}
        </div>
      )}

      {loading && !models.length && (
        <div className="text-center py-4">
          <p className="text-gray-600">Loading available models...</p>
        </div>
      )}

      {models.length > 0 && (
        <div className="space-y-3">
          <label className="label-heading block text-gray-800">
            Available Ollama Models ({models.length})
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {models.map((model) => {
              const modelName =  model.name;
              const modelSize = model.size
                ? `${(model.size / 1024 / 1024 / 1024).toFixed(1)} GB`
                : "Size unknown";
              const isSelected = selectedModel === modelName;

              return (
                <button
                  key={`${model.name}-${Math.random()}`}
                  onClick={() => handleModelSelection(modelName)}
                  disabled={loading}
                  className={`p-3 rounded-lg border-2 transition-all text-left ${
                    isSelected
                      ? "border-indigo-500 bg-indigo-50 shadow-md"
                      : "border-gray-300 hover:border-indigo-400 hover:bg-gray-50"
                  } ${loading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-800">{modelName}</p>
                      <p className="text-xs text-gray-600">{modelSize}</p>
                    </div>
                    {isSelected && <span className="text-xl">OK</span>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {models.length === 0 && !loading && (
        <div className="p-4 bg-yellow-50 border border-yellow-300 rounded">
          <p className="text-sm text-yellow-800 mb-2">
            No Ollama models installed. Please run:
          </p>
          <code className="block bg-yellow-100 p-2 rounded text-xs overflow-x-auto">
            ollama pull mistral
          </code>
        </div>
      )}

      {showRecommendations && Object.keys(recommendations).length > 0 && (
        <div className="space-y-2 p-4 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg border border-purple-200">
          <p className="panel-heading border-purple-200 text-slate-900">Model Recommendations</p>
          <div className="space-y-2 text-sm">
            {Object.entries(recommendations).map(([key, rec]) => (
              <div
                key={key}
                className="p-3 bg-white rounded border border-gray-200 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-start gap-2">
                  <span className="text-lg">
                    {key === "low_resource" ? "Low" : key === "high_quality" ? "HQ" : "Fast"}
                  </span>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">{rec.model}</p>
                    <p className="text-gray-600 text-xs">{rec.description}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      VRAM: {rec.vram_required_gb}GB | Speed: {rec.speed}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-2">
        <p className="panel-heading border-slate-200 text-slate-900">Evaluation Dashboard (Last 30 Days)</p>
        {evalError && <p className="text-xs text-red-700">{evalError}</p>}
        {!evalError && !evalSummary && <p className="text-xs text-slate-600">Loading evaluation metrics...</p>}
        {evalSummary?.releases?.length > 0 && (
          <div className="space-y-2 text-xs text-slate-700">
            {evalSummary.releases.map((rel) => (
              <div key={rel.release_version} className="grid grid-cols-2 md:grid-cols-4 gap-2 p-2 bg-white rounded border border-slate-200">
                <p><strong>Release:</strong> {rel.release_version}</p>
                <p><strong>Queries:</strong> {rel.total_queries}</p>
                <p><strong>Faithful:</strong> {Math.round((rel.avg_faithfulness || 0) * 100)}%</p>
                <p><strong>Hallucination:</strong> {Math.round((rel.avg_hallucination_risk || 0) * 100)}%</p>
                <p><strong>P@K:</strong> {Math.round((rel.avg_precision_at_k || 0) * 100)}%</p>
                <p><strong>R@K:</strong> {Math.round((rel.avg_recall_at_k || 0) * 100)}%</p>
                <p><strong>Citations:</strong> {Math.round((rel.avg_citation_coverage || 0) * 100)}%</p>
                <p><strong>2nd pass:</strong> {Math.round((rel.second_pass_ratio || 0) * 100)}%</p>
              </div>
            ))}
            <div className="flex gap-4">
              <p><strong>👍</strong> {evalSummary.feedback?.up || 0}</p>
              <p><strong>👎</strong> {evalSummary.feedback?.down || 0}</p>
            </div>
          </div>
        )}
      </div>

      <div className="bg-blue-50 p-4 rounded-lg text-sm text-blue-900 border border-blue-200">
        <p className="panel-heading mb-2 border-blue-200 text-blue-900">Hardware Guide</p>
        <ul className="space-y-1 text-xs">
          <li><strong>4GB RAM/VRAM</strong> - Use orca-mini</li>
          <li><strong>8GB RAM/VRAM</strong> - Use mistral or neural-chat</li>
          <li><strong>GPU Available</strong> - Use larger models</li>
        </ul>
      </div>

      <div className="pt-2 border-t border-slate-200">
        <button
          onClick={handleLogout}
          disabled={logoutLoading}
          className="w-full py-2.5 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {logoutLoading ? "Logging out..." : "Logout"}
        </button>
      </div>
    </div>
  );
}
