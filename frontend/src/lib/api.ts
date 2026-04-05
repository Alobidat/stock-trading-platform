/**
 * API client — thin axios wrapper with base URL and error handling.
 */

import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Response interceptor — normalize errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

// ─── API Functions ─────────────────────────────────────────

export const api = {
  // Health
  health: () => apiClient.get("/health/").then((r) => r.data),

  // Portfolio
  getAccount: () => apiClient.get("/portfolio/account").then((r) => r.data),
  getPositions: () => apiClient.get("/portfolio/positions").then((r) => r.data),

  // Signals
  getSignals: (symbol?: string, limit = 50) =>
    apiClient
      .get("/signals/", { params: { symbol, limit } })
      .then((r) => r.data),
  getSignal: (id: string) => apiClient.get(`/signals/${id}`).then((r) => r.data),

  // Agents
  getAgentLogs: (params?: { symbol?: string; agent_name?: string; limit?: number }) =>
    apiClient.get("/agents/logs", { params }).then((r) => r.data),
  triggerAnalysis: (symbol: string, executeTrade = false) =>
    apiClient
      .post("/agents/analyze", { symbol, execute_trade: executeTrade })
      .then((r) => r.data),
  getLlmInfo: () => apiClient.get("/agents/llm-info").then((r) => r.data),
};
