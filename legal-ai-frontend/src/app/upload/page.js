"use client";
import React, { useState } from "react";
import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function UploadLegalDoc() {

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const router = useRouter();

  // ---------------- HANDLE FILE SELECT ----------------
  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    if (!selected.name.endsWith(".pdf")) {
      setMessage("Only PDF files allowed.");
      return;
    }

    setFile(selected);
    setMessage("");
  };

  // ---------------- UPLOAD ----------------
  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select a PDF first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      setProgress(0);
      setMessage("");

      const response = await axios.post(
        "http://localhost:8000/upload",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (progressEvent) => {
            const percent = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setProgress(percent);
          }
        }
      );

      // success message
      setMessage(
        `Document indexed successfully (${response.data.chunks_added} chunks). Redirecting to search...`
      );

      setFile(null);

      // redirect to main search page
      setTimeout(() => {
        router.push("/");
      }, 1500);

    } catch (err) {
      console.error(err);
      setMessage("Upload failed. Check backend logs.");
    } finally {
      setUploading(false);
    }
  };

  // ---------------- UI ----------------
  return (
    <div className="min-h-screen bg-gray-950 text-white p-10">

      {/* Back button */}
      <Link href="/">
        <button className="mb-6 border border-gray-700 px-4 py-2 rounded-lg hover:bg-gray-800">
          ← Back to Research
        </button>
      </Link>

      <h1 className="text-3xl font-semibold mb-2">Upload Legal Document</h1>
      <p className="text-gray-400 mb-8">
        Upload contracts, judgments, or legal PDFs to make them searchable.
      </p>

      {/* Upload Card */}
      <div className="bg-gray-900 rounded-2xl shadow-xl p-8 w-[560px]">

        {/* Drag & Drop Area */}
        <label className="border-2 border-dashed border-gray-700 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 transition">
          <p className="text-sm text-gray-400 mb-2">
            Drag & drop a PDF or click to select
          </p>

          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          {file && (
            <p className="mt-3 text-sm text-blue-400">
              Selected: {file.name}
            </p>
          )}
        </label>

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-6 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-6 py-3 rounded-xl w-full"
        >
          {uploading ? "Uploading & Indexing..." : "Upload & Index Document"}
        </button>

        {/* Progress bar */}
        {uploading && (
          <div className="mt-4">
            <div className="h-2 bg-gray-800 rounded">
              <div
                className="h-2 bg-blue-600 rounded"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">{progress}%</p>
          </div>
        )}

        {/* Status message */}
        {message && (
          <p className="mt-6 text-sm text-gray-300">{message}</p>
        )}
      </div>
    </div>
  );
}