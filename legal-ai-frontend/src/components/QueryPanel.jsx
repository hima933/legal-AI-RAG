import React from "react";

export default function QueryPanel({
  query,
  setQuery,
  loading,
  onSubmit,
  uploadedDocs = []
}) {
  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h2 className="section-title">
          Ask Legal Question
        </h2>
        <p className="section-subtitle">
          Ask any legal question related to law, Constitution, or Acts.
        </p>
      </div>

      {/* Uploaded Context Indicator */}
      {uploadedDocs.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4">
          <p className="label-heading text-indigo-800 mb-2">
            Using {uploadedDocs.length} document(s) as context
          </p>

          <div className="space-y-1">
            {uploadedDocs.slice(0, 3).map((doc) => (
              <p key={doc.id} className="text-xs text-indigo-800 truncate">
                • {doc.name}
              </p>
            ))}

            {uploadedDocs.length > 3 && (
              <p className="text-xs text-indigo-700 italic">
                + {uploadedDocs.length - 3} more document(s)
              </p>
            )}
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={onSubmit} className="space-y-5">

        {/* Textarea */}
        <div className="space-y-2">
          <label className="label-heading text-slate-700">
            Your Question
          </label>

          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Example: What are the rights of workers under minimum wage law?"
            disabled={loading}
            maxLength={1000}
            className="w-full min-h-[140px] px-4 py-3 rounded-2xl border border-slate-300 bg-white 
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500
              transition-all duration-200 resize-none text-sm text-black placeholder:text-gray-500"
          />

          <div className="flex justify-between text-xs text-slate-500">
            <span>
              {query.length}/1000 characters
            </span>

            {query.length > 850 && (
              <span className="text-amber-600 font-medium">
                Approaching limit
              </span>
            )}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className={`
            w-full py-3 rounded-2xl font-semibold text-sm transition-all duration-200
            ${loading || !query.trim()
              ? "bg-slate-300 text-white cursor-not-allowed"
              : "bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:opacity-90 active:scale-[0.98] shadow-md"
            }
          `}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin inline-block">⏳</span>
              Analyzing Legal Context...
            </span>
          ) : (
            "Generate Answer"
          )}
        </button>
      </form>
    </div>
  );
}
