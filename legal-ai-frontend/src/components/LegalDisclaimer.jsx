import React from "react";

export default function LegalDisclaimer({ onAccept }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl max-h-96 overflow-y-auto">
        <div className="p-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-4xl">⚖️</span>
            <h2 className="text-2xl font-bold text-gray-900">
              Important Legal Disclaimer
            </h2>
          </div>

          <div className="space-y-4 text-gray-700">
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
              <p className="font-bold text-red-900 mb-2">⚠️ CRITICAL WARNING</p>
              <p className="text-sm text-red-800">
                This AI assistant provides EDUCATIONAL INFORMATION ONLY and is
                NOT a substitute for professional legal advice from a qualified
                lawyer.
              </p>
            </div>

            <div className="space-y-2 text-sm">
              <h3 className="font-bold text-gray-900">You Acknowledge That:</h3>
              <ul className="list-disc pl-5 space-y-1 text-gray-700">
                <li>
                  This tool may contain errors, inaccuracies, or outdated
                  information
                </li>
                <li>
                  Laws vary by jurisdiction and are subject to interpretation
                </li>
                <li>
                  AI-generated responses should never be used as a basis for
                  legal action
                </li>
                <li>
                  You must consult a qualified lawyer for important legal
                  matters
                </li>
                <li>
                  The authors are not liable for any damages arising from the
                  use of this tool
                </li>
                <li>
                  This tool should not be used to commit illegal activities or
                  evade laws
                </li>
                <li>
                  All information provided must be verified through official
                  legal sources
                </li>
              </ul>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
              <p className="text-sm text-blue-900">
                <strong>Recommended Action:</strong> For any significant legal
                matter, immediately consult with a licensed attorney in your
                jurisdiction. This tool is meant to help you understand legal
                concepts, not to replace legal counsel.
              </p>
            </div>
          </div>

          <div className="mt-6 flex gap-4">
            <button
              onClick={onAccept}
              className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 transition-all"
            >
              ✅ I Understand & Accept
            </button>
            <button
              onClick={() => window.location.href = "https://www.google.com"}
              className="flex-1 bg-gray-200 text-gray-800 py-3 rounded-lg font-bold hover:bg-gray-300 transition-all"
            >
              ❌ Leave Site
            </button>
          </div>

          <p className="text-xs text-gray-500 text-center mt-4">
            By clicking "I Understand & Accept", you agree to use this tool
            responsibly and at your own risk.
          </p>
        </div>
      </div>
    </div>
  );
}
