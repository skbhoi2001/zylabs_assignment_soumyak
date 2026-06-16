import { useEffect, useRef, useState } from "react";
import { CheckCircle, Circle, Loader, AlertCircle } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const NODES = [
  { key: "planner", label: "Planner", description: "Breaking down research objective" },
  { key: "researcher", label: "Researcher", description: "Gathering data via web search" },
  { key: "analyst", label: "Analyst", description: "Synthesising 9 report sections" },
  { key: "quality_check", label: "Quality Check", description: "Scoring completeness" },
  { key: "report_generator", label: "Report Generator", description: "Formatting final report" },
];

const STATUS = { pending: "pending", running: "running", done: "done", error: "error" };

function NodeIcon({ status }) {
  if (status === STATUS.done) return <CheckCircle className="w-6 h-6 text-green-500" />;
  if (status === STATUS.running) return <Loader className="w-6 h-6 text-indigo-500 animate-spin" />;
  if (status === STATUS.error) return <AlertCircle className="w-6 h-6 text-red-500" />;
  return <Circle className="w-6 h-6 text-gray-300" />;
}

export default function WorkflowStepper({ sessionId, onComplete }) {
  const [nodeStatuses, setNodeStatuses] = useState(() =>
    Object.fromEntries(NODES.map((n) => [n.key, STATUS.pending]))
  );
  const [log, setLog] = useState([]);
  const [qualityScore, setQualityScore] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [workflowError, setWorkflowError] = useState(null);
  const esRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`${BASE_URL}/sessions/${sessionId}/run`);
    esRef.current = es;

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "ping") return;

        setLog((prev) => [...prev, data]);

        if (data.type === "node_start") {
          setNodeStatuses((prev) => ({ ...prev, [data.node]: STATUS.running }));
        }
        if (data.type === "node_complete") {
          const err = data.error;
          setNodeStatuses((prev) => ({
            ...prev,
            [data.node]: err ? STATUS.error : STATUS.done,
          }));
          if (data.quality_score != null) setQualityScore(data.quality_score);
          if (data.retry_count != null) setRetryCount(data.retry_count);
        }
        if (data.type === "complete") {
          es.close();
          onComplete?.();
        }
        if (data.type === "error") {
          setWorkflowError(data.message);
          es.close();
          onComplete?.();
        }
      } catch (_) {}
    };

    es.onerror = () => {
      es.close();
    };

    return () => es.close();
  }, [sessionId]);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-base font-semibold text-gray-800 mb-5">Research Workflow</h3>

      <div className="space-y-3">
        {NODES.map((node, idx) => {
          const status = nodeStatuses[node.key];
          return (
            <div key={node.key} className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <NodeIcon status={status} />
                {idx < NODES.length - 1 && (
                  <div className={`w-0.5 h-6 mt-1 ${status === STATUS.done ? "bg-green-300" : "bg-gray-200"}`} />
                )}
              </div>
              <div className="pb-2">
                <p className={`text-sm font-medium ${status === STATUS.running ? "text-indigo-600" : status === STATUS.done ? "text-gray-800" : "text-gray-400"}`}>
                  {node.label}
                </p>
                <p className="text-xs text-gray-400">{node.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      {qualityScore != null && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Quality score</span>
            <span className={`font-semibold ${qualityScore >= 70 ? "text-green-600" : "text-amber-600"}`}>
              {qualityScore}/100
            </span>
          </div>
          {retryCount > 0 && (
            <p className="text-xs text-amber-500 mt-1">Retried {retryCount}× to improve quality</p>
          )}
        </div>
      )}

      {workflowError && (
        <div className="mt-4 p-3 bg-red-50 rounded-lg text-sm text-red-700">
          <strong>Error:</strong> {workflowError}
        </div>
      )}
    </div>
  );
}
