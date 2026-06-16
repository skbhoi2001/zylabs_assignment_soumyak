import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Sessions
export const createSession = (data) => api.post("/sessions", data).then((r) => r.data);
export const listSessions = () => api.get("/sessions").then((r) => r.data);
export const getSession = (id) => api.get(`/sessions/${id}`).then((r) => r.data);

// Workflow
export const triggerRun = (sessionId) =>
  api.post(`/sessions/${sessionId}/run`).then((r) => r.data);

// Chat
export const sendChat = (sessionId, content) =>
  api.post(`/sessions/${sessionId}/chat`, { content }).then((r) => r.data);
export const getChatHistory = (sessionId) =>
  api.get(`/sessions/${sessionId}/chat`).then((r) => r.data);

// Health
export const getHealth = () => api.get("/health").then((r) => r.data);
