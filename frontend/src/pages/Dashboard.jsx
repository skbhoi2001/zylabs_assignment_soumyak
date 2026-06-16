import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Plus, Zap } from "lucide-react";
import { listSessions } from "../api/client";
import SessionCard from "../components/SessionCard";

function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gray-100" />
        <div className="space-y-2">
          <div className="w-32 h-3 bg-gray-100 rounded" />
          <div className="w-24 h-2 bg-gray-100 rounded" />
        </div>
      </div>
      <div className="mt-3 w-full h-2 bg-gray-100 rounded" />
      <div className="mt-1 w-3/4 h-2 bg-gray-100 rounded" />
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: sessions, isLoading, isError } = useQuery({
    queryKey: ["sessions"],
    queryFn: listSessions,
    refetchInterval: 10000,
    refetchOnWindowFocus: true,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-600" />
            <span className="font-bold text-gray-900">ZyLabs Research Copilot</span>
          </div>
          <button
            onClick={() => navigate("/sessions/new")}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Research
          </button>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Research Sessions</h1>
          <p className="text-sm text-gray-500 mt-1">AI-powered company research reports</p>
        </div>

        {isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 mb-4">
            Failed to load sessions. Is the backend running?
          </div>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : sessions?.length === 0 ? (
          <div className="text-center py-20">
            <Zap className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">No research sessions yet</p>
            <p className="text-sm text-gray-400 mt-1">Create your first session to get started</p>
            <button
              onClick={() => navigate("/sessions/new")}
              className="mt-4 px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition-colors"
            >
              Start Researching
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {sessions?.map((s) => <SessionCard key={s.id} session={s} />)}
          </div>
        )}
      </main>
    </div>
  );
}
