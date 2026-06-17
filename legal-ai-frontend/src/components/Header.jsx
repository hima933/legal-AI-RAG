import React from "react";

export default function Header() {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-lg">
      <div className="container mx-auto px-2 sm:px-4 py-4 sm:py-6 max-w-6xl">
        <div className="flex items-center justify-between gap-2 sm:gap-4 flex-wrap">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-bold truncate">Legal AI</h1>
              <p className="text-xs sm:text-sm text-blue-100 truncate">
                Intelligent Legal Information Assistant
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-indigo-900 bg-white px-3 sm:px-4 py-2 rounded-full border border-indigo-200 whitespace-nowrap">
            <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
            <span>System Active</span>
          </div>
        </div>
      </div>
    </header>
  );
}
