import React, { useState } from "react";

const panelClass = "bg-white border border-slate-200 rounded-2xl shadow-sm";

const ConfidenceIndicator = ({ confidence = 0 }) => {
  const percentage = Math.round((confidence || 0) * 100);
  let label = "Low";
  if (confidence >= 0.8) label = "High";
  else if (confidence >= 0.6) label = "Medium";

  return (
    <div className="space-y-1">
      <div className="progress-bar">
        <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
      </div>
      <div className="text-xs font-semibold text-slate-700">
        {label} confidence - {percentage}%
      </div>
    </div>
  );
};

const AnalysisFields = ({ analysis }) => {
  const legalIssues = Array.isArray(analysis?.legal_issues) ? analysis.legal_issues : [];
  const keyArguments = Array.isArray(analysis?.key_arguments) ? analysis.key_arguments : [];
  const parties = Array.isArray(analysis?.parties) ? analysis.parties : [];

  return (
    <div className={`${panelClass} p-6 space-y-5`}>
      <h4 className="panel-heading text-indigo-700">Structured Legal Analysis</h4>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <p className="label-heading">Case Type</p>
          <p className="text-sm font-medium text-slate-900 mt-1">{analysis?.case_type || "Not available"}</p>
        </div>
        <div>
          <p className="label-heading">Risk Level</p>
          <span className="inline-block mt-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            {analysis?.risk_level || "Unknown"}
          </span>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <p className="label-heading">Court</p>
          <p className="text-sm font-medium text-slate-900 mt-1">{analysis?.court || "Not extracted"}</p>
        </div>
        <div>
          <p className="label-heading">Parties</p>
          {parties.length ? (
            <p className="text-sm text-slate-800 mt-1">{parties.join(" vs ")}</p>
          ) : (
            <p className="text-sm text-slate-500 mt-1">Not available</p>
          )}
        </div>
      </div>

      <div>
        <p className="label-heading mb-2">Legal Issues</p>
        {legalIssues.length ? (
          <ul className="list-disc pl-5 text-sm text-slate-800 space-y-1">
            {legalIssues.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Not available</p>
        )}
      </div>

      <div>
        <p className="label-heading mb-2">Key Arguments</p>
        {keyArguments.length ? (
          <ul className="list-disc pl-5 text-sm text-slate-800 space-y-1">
            {keyArguments.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Not available</p>
        )}
      </div>

      <div>
        <p className="label-heading mb-2">Recommended Action</p>
        <p className="text-sm text-slate-800">{analysis?.recommended_action || "Not available"}</p>
      </div>
    </div>
  );
};

const TransparencyPanel = ({ metadata }) => {
  if (!metadata || typeof metadata !== "object") return null;

  const evalMetrics = metadata.evaluation || {};
  const chunks = Array.isArray(metadata.top_context_chunks) ? metadata.top_context_chunks : [];
  const sections = Array.isArray(metadata.matched_legal_sections) ? metadata.matched_legal_sections : [];
  const feedback = metadata.recursive_feedback || {};

  return (
    <div className={`${panelClass} p-5 space-y-3`}>
      <h4 className="panel-heading text-slate-900">Why this answer</h4>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-slate-700">
        <p><strong>Mode:</strong> {metadata.retrieval_mode || "n/a"}</p>
        <p><strong>Strategy:</strong> {metadata.retrieval_strategy || "n/a"}</p>
        <p><strong>Language:</strong> {metadata.query_language || "en"}</p>
        <p><strong>2nd pass:</strong> {metadata.second_pass_used ? "Yes" : "No"}</p>
        <p><strong>Faithful:</strong> {Math.round((evalMetrics.faithfulness_score || 0) * 100)}%</p>
        <p><strong>P@K:</strong> {Math.round((evalMetrics.precision_at_k || 0) * 100)}%</p>
        <p><strong>R@K:</strong> {Math.round((evalMetrics.recall_at_k || 0) * 100)}%</p>
        <p><strong>Citations:</strong> {Math.round((evalMetrics.citation_coverage || 0) * 100)}%</p>
      </div>

      {metadata.rewritten_query && (
        <p className="text-xs text-slate-700">
          <strong>Rewritten query:</strong> {metadata.rewritten_query}
        </p>
      )}

      {feedback.reason && (
        <p className="text-xs text-slate-700">
          <strong>Critique:</strong> {feedback.reason}
        </p>
      )}

      {sections.length > 0 && (
        <div>
          <p className="label-heading mb-1">Matched Legal Sections</p>
          <div className="flex flex-wrap gap-2">
            {sections.slice(0, 8).map((item, idx) => (
              <span key={`${item}-${idx}`} className="px-2 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs">
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {chunks.length > 0 && (
        <div className="space-y-2">
          <p className="label-heading">Top Context Chunks</p>
          {chunks.slice(0, 3).map((chunk, idx) => (
            <div key={idx} className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
              <p className="font-semibold text-slate-800">
                {chunk.source || `Legal reference ${idx + 1}`}
                {chunk.page ? ` (page ${chunk.page})` : ""}
              </p>
              <p>{chunk.preview || "No preview available."}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const FeedbackPanel = ({ queryId, onSubmitFeedback, feedbackStatus }) => {
  const [rating, setRating] = useState("");
  const [correction, setCorrection] = useState("");
  const [details, setDetails] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!queryId || !onSubmitFeedback) return null;

  const submit = async (nextRating) => {
    setSaving(true);
    setError("");
    try {
      const payload = {
        queryId,
        rating: nextRating || rating,
        correction: correction.trim(),
        details: details.trim(),
      };
      await onSubmitFeedback(payload);
      setRating(payload.rating);
      if (payload.rating === "up") {
        setCorrection("");
        setDetails("");
      }
    } catch (err) {
      setError(err.message || "Failed to submit feedback");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`${panelClass} p-5 space-y-3`}>
      <h4 className="panel-heading text-slate-900">Was this answer helpful?</h4>
      <div className="flex gap-2">
        <button
          onClick={() => submit("up")}
          disabled={saving}
          className={`px-3 py-2 rounded-lg text-sm font-semibold border ${rating === "up" ? "bg-green-100 border-green-300 text-green-700" : "bg-white border-slate-300 text-slate-700"}`}
        >
          Thumb Up
        </button>
        <button
          onClick={() => setRating("down")}
          disabled={saving}
          className={`px-3 py-2 rounded-lg text-sm font-semibold border ${rating === "down" ? "bg-amber-100 border-amber-300 text-amber-700" : "bg-white border-slate-300 text-slate-700"}`}
        >
          Thumb Down
        </button>
      </div>

      {rating === "down" && (
        <div className="space-y-2">
          <textarea
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            placeholder="What should be corrected?"
            maxLength={1000}
            className="w-full min-h-[90px] px-3 py-2 rounded-lg border border-slate-300 text-sm text-black"
          />
          <textarea
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            placeholder="Optional details (missing section, wrong interpretation, etc.)"
            maxLength={1000}
            className="w-full min-h-[70px] px-3 py-2 rounded-lg border border-slate-300 text-sm text-black"
          />
          <button
            onClick={() => submit("down")}
            disabled={saving}
            className="px-3 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold disabled:opacity-50"
          >
            {saving ? "Saving..." : "Submit Correction"}
          </button>
        </div>
      )}

      {feedbackStatus && <p className="text-xs text-green-700">{feedbackStatus}</p>}
      {error && <p className="text-xs text-red-700">{error}</p>}
    </div>
  );
};

const AutoGeneratedSummaryPanel = ({ response, filesProcessed = [] }) => {
  const items = Array.isArray(filesProcessed) ? filesProcessed : [];
  const fallbackItem =
    items.length > 0
      ? null
      : [
          {
            name: "Uploaded document",
            analysis: null,
            raw_analysis: {},
          },
        ];
  const displayItems = items.length > 0 ? items : fallbackItem;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="section-title">Case Analysis</h3>
        <p className="section-subtitle">Generated from uploaded legal document</p>
      </div>

      {displayItems.map((file, idx) => {
        const analysis = file?.analysis || null;
        const raw = file?.raw_analysis || {};
        const summaryText =
          raw.summary ||
          analysis?.summary ||
          analysis?.recommended_action ||
          response?.answer ||
          "Document analyzed, but structured extraction was limited.";

        return (
          <div key={`${file?.name || "uploaded"}-${idx}`} className="space-y-4">
            <div className={`${panelClass} p-6`}>
              <p className="label-heading mb-2">Document</p>
              <p className="text-sm font-semibold text-slate-900 mb-3">{file?.name || "Uploaded document"}</p>
              <p className="text-sm text-black leading-relaxed">{summaryText}</p>
            </div>

            {analysis ? (
              <AnalysisFields analysis={analysis} />
            ) : (
              <p className="text-sm text-slate-500">Structured legal insights unavailable for this document.</p>
            )}
          </div>
        );
      })}

      <TransparencyPanel metadata={response?.metadata} />
      <ConfidenceIndicator confidence={response.confidence} />
    </div>
  );
};

export default function ResponsePanel({ response, query, onSubmitFeedback, feedbackStatus }) {
  if (!response) return null;

  const filesProcessed = Array.isArray(response?.summary?.files_processed)
    ? response.summary.files_processed
    : [];
  const structuredAnalysis = filesProcessed[0]?.analysis;
  const displayQuery =
    response?.asked_question ||
    query ||
    response?.metadata?.translated_query ||
    "Question";

  const formatCitation = (citation = {}, idx = 0) => {
    const rawSource = String(citation?.source || "").trim();
    const source =
      rawSource && !["unknown", "none", "null"].includes(rawSource.toLowerCase())
        ? rawSource
        : `Legal reference ${idx + 1}`;

    const parsedPage = Number.parseInt(citation?.page, 10);
    const pageLabel = Number.isFinite(parsedPage) && parsedPage > 0 ? ` (page ${parsedPage})` : "";
    return `${source}${pageLabel}`;
  };

  if (response.autoGenerated === true) {
    return <AutoGeneratedSummaryPanel response={response} filesProcessed={filesProcessed} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="section-title">Legal Response</h3>
        <p className="section-subtitle">AI-generated legal information with contextual analysis.</p>
      </div>

      <div className={`${panelClass} p-5`}>
        <p className="label-heading mb-1">Question</p>
        <p className="text-sm text-slate-900">{displayQuery}</p>
      </div>

      <ConfidenceIndicator confidence={response.confidence} />

      {response.has_warning && response.warning && (
        <div className="alert-warning">
          <strong>Warning:</strong> {response.warning}
        </div>
      )}

      <div className={`${panelClass} p-6`}>
        <h4 className="panel-heading mb-3">Answer</h4>
        <p className="text-black leading-relaxed whitespace-pre-line">{response.answer}</p>
      </div>

      {structuredAnalysis && <AnalysisFields analysis={structuredAnalysis} />}

      <TransparencyPanel metadata={response?.metadata} />

      {Array.isArray(response.citations) && response.citations.length > 0 && (
        <div className={`${panelClass} p-5`}>
          <h4 className="panel-heading mb-3">Citations</h4>
          <ul className="text-sm text-slate-800 space-y-1">
            {response.citations.slice(0, 8).map((c, idx) => (
              <li key={idx}>{formatCitation(c, idx)}</li>
            ))}
          </ul>
        </div>
      )}

      {response.disclaimer && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-900">
          {response.disclaimer}
        </div>
      )}

      <FeedbackPanel
        queryId={response.query_id}
        onSubmitFeedback={onSubmitFeedback}
        feedbackStatus={feedbackStatus}
      />

      <div className="flex gap-3 pt-1">
        <button
          onClick={() => {
            navigator.clipboard.writeText(response.answer || "");
            alert("Answer copied to clipboard");
          }}
          className="btn-primary"
        >
          Copy Answer
        </button>

        <button
          onClick={() => {
            const element = document.createElement("a");
            const file = new Blob([response.answer || ""], { type: "text/plain" });
            element.href = URL.createObjectURL(file);
            element.download = `legal-answer-${Date.now()}.txt`;
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
          }}
          className="px-4 py-2 rounded-xl border border-slate-300 hover:bg-slate-100 text-sm font-semibold"
        >
          Download
        </button>
      </div>
    </div>
  );
}
