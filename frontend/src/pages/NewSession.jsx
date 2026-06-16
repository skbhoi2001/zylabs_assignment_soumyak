import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Zap, Loader } from "lucide-react";
import { createSession, triggerRun } from "../api/client";

const schema = z.object({
  company_name: z.string().min(2, "Company name must be at least 2 characters"),
  website: z.string().url("Please enter a valid URL (include https://)"),
  objective: z.string().min(20, "Research objective must be at least 20 characters"),
});

function Field({ label, error, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export default function NewSession() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const { mutate: create, isPending, error: mutationError } = useMutation({
    mutationFn: async (data) => {
      const session = await createSession(data);
      await triggerRun(session.id);
      return session;
    },
    onSuccess: (session) => {
      qc.invalidateQueries({ queryKey: ["sessions"] });
      navigate(`/sessions/${session.id}`);
    },
  });

  const inputClass = (hasError) =>
    `w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300 transition-colors ${
      hasError ? "border-red-300 bg-red-50" : "border-gray-200 bg-white hover:border-gray-300"
    }`;

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center gap-3">
          <button onClick={() => navigate("/")} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
            <ArrowLeft className="w-4 h-4 text-gray-600" />
          </button>
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-600" />
            <span className="font-bold text-gray-900">New Research Session</span>
          </div>
        </div>
      </nav>

      <main className="max-w-2xl mx-auto px-6 py-10">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <h1 className="text-xl font-bold text-gray-900 mb-1">Research a Company</h1>
          <p className="text-sm text-gray-500 mb-7">
            Our AI will run a 5-node LangGraph workflow to produce a comprehensive research report.
          </p>

          {mutationError && (
            <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {mutationError.response?.data?.detail || mutationError.message}
            </div>
          )}

          <form onSubmit={handleSubmit(create)} className="space-y-5">
            <Field label="Company Name" error={errors.company_name?.message}>
              <input
                {...register("company_name")}
                className={inputClass(!!errors.company_name)}
                placeholder="e.g. Stripe, OpenAI, Notion"
              />
            </Field>

            <Field label="Company Website" error={errors.website?.message}>
              <input
                {...register("website")}
                className={inputClass(!!errors.website)}
                placeholder="https://stripe.com"
                type="url"
              />
            </Field>

            <Field label="Research Objective" error={errors.objective?.message}>
              <textarea
                {...register("objective")}
                className={`${inputClass(!!errors.objective)} resize-none h-28`}
                placeholder="e.g. I'm preparing for a sales call with Stripe. I need to understand their core products, recent news, competitive positioning, and identify potential pain points we could address."
              />
            </Field>

            <button
              type="submit"
              disabled={isPending}
              className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isPending ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Starting research…
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Start Research
                </>
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
