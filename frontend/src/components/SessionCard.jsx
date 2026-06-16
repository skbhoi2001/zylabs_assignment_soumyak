import { useNavigate } from "react-router-dom";
import { Clock, CheckCircle, AlertCircle, Loader, Building2 } from "lucide-react";

const STATUS_CONFIG = {
  pending: { icon: Clock, label: "Pending", color: "text-gray-400 bg-gray-100" },
  running: { icon: Loader, label: "Running", color: "text-indigo-600 bg-indigo-50", spin: true },
  complete: { icon: CheckCircle, label: "Complete", color: "text-green-600 bg-green-50" },
  error: { icon: AlertCircle, label: "Error", color: "text-red-600 bg-red-50" },
};

export default function SessionCard({ session }) {
  const navigate = useNavigate();
  const cfg = STATUS_CONFIG[session.status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;

  return (
    <div
      onClick={() => navigate(`/sessions/${session.id}`)}
      className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-indigo-200 cursor-pointer transition-all group"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
            <Building2 className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">{session.company_name}</h3>
            <a
              href={session.website}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-indigo-500 hover:underline"
            >
              {session.website}
            </a>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${cfg.color}`}>
          <Icon className={`w-3 h-3 ${cfg.spin ? "animate-spin" : ""}`} />
          {cfg.label}
        </span>
      </div>

      <p className="mt-3 text-xs text-gray-500 line-clamp-2">{session.objective}</p>

      <div className="mt-3 text-xs text-gray-400">
        {new Date(session.created_at).toLocaleString()}
      </div>
    </div>
  );
}
