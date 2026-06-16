import { useState } from "react";
import { ChevronDown, ChevronUp, Copy, Check, ExternalLink } from "lucide-react";

const SECTION_ICONS = {
  company_overview: "🏢",
  products_and_services: "📦",
  target_market: "🎯",
  competitive_landscape: "⚔️",
  recent_news_and_developments: "📰",
  financials_and_funding: "💰",
  technology_and_infrastructure: "🔧",
  team_and_culture: "👥",
  strategic_insights: "💡",
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handle = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button onClick={handle} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
    </button>
  );
}

function SectionCard({ section }) {
  const [open, setOpen] = useState(true);
  const icon = SECTION_ICONS[section.key] || "📄";

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 bg-white hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className="font-medium text-gray-800 text-sm">{section.label}</span>
          {section.word_count > 0 && (
            <span className="text-xs text-gray-400 ml-1">{section.word_count} words</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <CopyButton text={section.content} />
          {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>
      {open && (
        <div className="px-5 py-4 bg-white border-t border-gray-100">
          {section.content ? (
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{section.content}</p>
          ) : (
            <p className="text-sm text-gray-400 italic">No content available for this section.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportViewer({ report }) {
  if (!report) return null;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{report.company_name}</h2>
            <p className="text-sm text-gray-500 mt-1">{report.objective}</p>
          </div>
          <div className="text-right">
            <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${report.quality_score >= 70 ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
              Quality: {report.quality_score}/100
            </span>
            <p className="text-xs text-gray-400 mt-1">
              {new Date(report.generated_at).toLocaleString()}
            </p>
          </div>
        </div>

        {report.summary && (
          <p className="mt-3 text-sm text-gray-600 bg-gray-50 rounded-lg p-3 leading-relaxed">
            {report.summary}
          </p>
        )}
      </div>

      {/* Sections */}
      <div className="space-y-2">
        {(report.sections || []).map((section) => (
          <SectionCard key={section.key} section={section} />
        ))}
      </div>

      {/* Sources */}
      {report.sources?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Sources ({report.sources.length})</h4>
          <ul className="space-y-1">
            {report.sources.map((url, i) => (
              <li key={i}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span className="truncate">{url}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
