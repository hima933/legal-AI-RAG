import React from "react";

export default function HistoryPanel({ history, onLoadEntry, onClear }) {
  if (history.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-12 text-center">
        <h3 className="section-title justify-center before:hidden">No Query History</h3>
        <p className="section-subtitle mb-6">Your legal queries will appear here for easy access.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="section-title">Query History</h2>
        <button
          onClick={onClear}
          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 font-semibold text-sm"
        >
          Clear History
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {history.map((entry) => (
          <div
            key={entry.id}
            className="bg-white rounded-lg shadow p-4 hover:shadow-lg transition-all cursor-pointer"
            onClick={() => onLoadEntry(entry)}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <p className="font-semibold text-gray-900 line-clamp-2 mb-2">{entry.question}</p>
                <p className="text-sm text-gray-700 line-clamp-2 mb-3">{entry.answer}</p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-blue-700 font-semibold">
                    Confidence: {Math.round(entry.confidence * 100)}%
                  </span>
                  <span className="text-gray-500">
                    {new Date(entry.timestamp).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
