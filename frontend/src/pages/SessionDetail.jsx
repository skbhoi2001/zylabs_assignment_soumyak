import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Zap, RefreshCw } from "lucide-react";
import { getSession } from "../api/client";
import WorkflowStepper from "../components/WorkflowStepper";
import ReportViewer from "../components/ReportViewer";
import ChatPanel from "../components/ChatPanel";

function Skeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="h-5 w-48 bg-gray-100 rounded mb-3" />
        <div className="h-3 w-64 bg-gray-100 rounded" />
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-6 h-40" />
    </div>
  );
}

export default function SessionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workflowDone, setWorkflowDone] = useState(false);

  const { data: session, isLoading, refetch } = useQuery({
    queryKey: ["session", id],
    queryFn: () => getSession(id),
    refetchInterval: workflowDone ? false : 3000,
    refetchOnWindowFocus: true,
  });

  const isRunning = session?.status === "running" || session?.status === "pending";
  const isComplete = session?.status === "complete";
  const hasReport = !!session?.final_report;

  const handleWorkflowComplete = () => {
    setWorkflowDone(true);
    setTimeout(() => refetch(), 1000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("/")} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
              <ArrowLeft className="w-4 h-4 text-gray-600" />
            </button>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-indigo-600" />
              <span className="font-bold text-gray-900">
                {session?.company_name || "Loading…"}
              </span>
            </div>
          </div>
          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {isLoading ? (
          <Skeleton />
        ) : !session ? (
          <div className="text-center py-20 text-gray-400">Session not found</div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column: stepper + chat */}
            <div className="space-y-6">
              <WorkflowStepper
                sessionId={id}
                onComplete={handleWorkflowComplete}
              />
              <ChatPanel sessionId={id} reportReady={isComplete && hasReport} />
            </div>

            {/* Right column: report */}
            <div className="lg:col-span-2">
              {hasReport ? (
                <ReportViewer report={session.final_report} />
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
                  {isRunning ? (
                    <>
                      <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4" />
                      <p className="text-gray-600 font-medium">Research in progress…</p>
                      <p className="text-sm text-gray-400 mt-1">
                        The AI workflow is generating your report. This takes 1–3 minutes.
                      </p>
                    </>
                  ) : session.status === "error" ? (
                    <>
                      <p className="text-red-600 font-medium">Workflow failed</p>
                      <p className="text-sm text-gray-400 mt-1">Check the stepper for error details.</p>
                    </>
                  ) : (
                    <>
                      <p className="text-gray-500 font-medium">No report yet</p>
                      <p className="text-sm text-gray-400 mt-1">Trigger a run to generate the report.</p>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
