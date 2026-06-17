import React, { useState } from "react";

export default function DocumentUpload({
  onUpload,
  onAnalysisReady = () => {},
  uploadedDocs,
  expanded = false,
  uploadProgress = { loaded: 0, total: 0, percent: 0, status: "" },
  ollamaReady = false,
  ollamaChecking = false,
}) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = React.useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFiles(Array.from(files));
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (files) => {
    const validFiles = files.filter((file) => {
      const validTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/rtf",
        "image/jpeg",
        "image/png",
        "image/jpg",
      ];
      const validSize = file.size <= 50 * 1024 * 1024;
      return validTypes.includes(file.type) && validSize;
    });

    if (validFiles.length > 0) {
      try {
        const result = await onUpload(validFiles);
        const processedFiles = result?.summary?.files_processed || [];
        if (processedFiles.length > 0) {
          onAnalysisReady(processedFiles);
        }
      } catch {
        // Upload error is handled by parent page state
      }
    } else {
      alert("Invalid files. Please upload PDF, DOCX, TXT, RTF, or images (max 50MB each)");
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 space-y-4">
      <h2 className="section-title">Upload Legal Documents</h2>
      <p className="section-subtitle">Upload documents for automatic analysis and document-grounded Q and A</p>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
          dragActive ? "border-indigo-500 bg-indigo-50" : "border-gray-300 hover:border-indigo-400"
        }`}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt,.rtf,.jpg,.jpeg,.png"
          onChange={handleChange}
          style={{ display: "none" }}
        />

        <div className="text-4xl mb-3">+</div>
        <p className="font-semibold text-gray-800 mb-1">Drag files here or click to select</p>
        <p className="text-xs text-gray-500">PDF, DOCX, TXT, RTF, or Images (max 50MB each)</p>
      </div>

      {ollamaChecking && (
        <div className="p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-sm text-yellow-800">
          Checking local model status...
        </div>
      )}

      {!ollamaReady && !ollamaChecking && (
        <div className="p-3 bg-orange-50 border border-orange-300 rounded-lg text-sm text-orange-800">
          If One Model unavailable. System will auto-switch to Available Model.
        </div>
      )}

      {ollamaReady && !ollamaChecking && (
        <div className="p-2 bg-green-50 border border-green-300 rounded-lg text-xs text-green-800">
          Ollama is ready.
        </div>
      )}

      {uploadProgress.total > 0 && (
        <div className="space-y-2 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-800">{uploadProgress.status || "Uploading..."}</span>
            <span className="text-sm font-medium text-indigo-600">{Math.round(uploadProgress.percent || 0)}%</span>
          </div>

          <div className="w-full bg-gray-300 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress.percent || 0}%` }}
            />
          </div>

          <p className="text-xs text-gray-600">
            {uploadProgress.loaded && uploadProgress.total
              ? `${(uploadProgress.loaded / 1024 / 1024).toFixed(2)} MB / ${(uploadProgress.total / 1024 / 1024).toFixed(2)} MB`
              : "Preparing analysis..."}
          </p>
        </div>
      )}

      {uploadedDocs.length > 0 && (
        <div className="space-y-2">
          <h4 className="panel-heading">Uploaded Documents ({uploadedDocs.length})</h4>
          <div className="max-h-96 overflow-y-auto space-y-3">
            {uploadedDocs.map((doc) => (
              <div
                key={doc.id}
                className="p-3 bg-gradient-to-r from-green-50 to-blue-50 border border-green-300 rounded-lg shadow-sm"
              >
                <div className="space-y-2">
                  <p className="text-sm font-semibold text-gray-800">{doc.name}</p>
                  <p className="text-xs text-gray-600">
                    {doc.size ? `${doc.size.toFixed(2)} MB` : "Size unknown"} | {doc.chunks || 0} chunks | analyzed
                  </p>

                  {doc.analysis?.summary && (
                    <div className="mt-2 p-2 bg-white rounded border-l-2 border-indigo-400 space-y-2">
                      <p className="text-xs font-semibold text-indigo-700">Case Summary</p>
                      <p className="text-xs text-gray-700 leading-relaxed">{doc.analysis.summary}</p>
                      <p className="text-xs text-gray-700">
                        <span className="font-semibold">Case Type:</span> {doc.analysis.case_type || "Unknown"}
                      </p>
                      <p className="text-xs text-gray-700">
                        <span className="font-semibold">Court:</span> {doc.analysis.court || "Not extracted"}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-blue-50 p-4 rounded-lg text-sm text-blue-900">
        <p className="panel-heading mb-2 border-blue-200 text-blue-900">Tips for best results</p>
        <ul className="space-y-1 text-xs">
          <li>- Upload complete legal documents for accurate analysis</li>
          <li>- PDFs typically extract better than images</li>
          <li>- After analysis, ask document-specific questions in document mode</li>
        </ul>
      </div>
    </div>
  );
}
