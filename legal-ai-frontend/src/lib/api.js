import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const parseTimeout = (rawValue, fallbackMs) => {
  const parsed = Number.parseInt(rawValue || "", 10);
  if (parsed === 0) return 0; // Axios: 0 means no timeout
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallbackMs;
};

// General request timeout (queries, auth, metadata)
const API_TIMEOUT = parseTimeout(process.env.NEXT_PUBLIC_API_TIMEOUT, 300000); // 5 minutes
// Upload-specific timeout (embedding + indexing can be much slower)
const UPLOAD_TIMEOUT = parseTimeout(process.env.NEXT_PUBLIC_UPLOAD_TIMEOUT, 900000); // 15 minutes

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    Accept: "application/json",
  },
});

const memoryAuthStore = {
  token: null,
  user: null,
};
const memoryStore = new Map();

const getStorage = () => {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

export const getLocalItem = (key) => {
  const storage = getStorage();
  if (!storage) return memoryStore.get(key) ?? null;
  try {
    return storage.getItem(key);
  } catch {
    return memoryStore.get(key) ?? null;
  }
};

export const setLocalItem = (key, value) => {
  memoryStore.set(key, value);
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(key, value);
  } catch (e) {
    console.warn(`Failed to store ${key}:`, e);
  }
};

export const removeLocalItem = (key) => {
  memoryStore.delete(key);
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.removeItem(key);
  } catch (e) {
    console.warn(`Failed to remove ${key}:`, e);
  }
};

// ---------------------------
// JWT TOKEN MANAGEMENT
// ---------------------------
export const getToken = () => {
  return getLocalItem("legalAI_token") || memoryAuthStore.token;
};

export const setToken = (token) => {
  memoryAuthStore.token = token;
  setLocalItem("legalAI_token", token);
};

export const clearToken = () => {
  memoryAuthStore.token = null;
  memoryAuthStore.user = null;
  removeLocalItem("legalAI_token");
  removeLocalItem("legalAI_user");
};

export const getStoredUser = () => {
  const user = getLocalItem("legalAI_user");
  if (!user) return memoryAuthStore.user;
  try {
    return user ? JSON.parse(user) : memoryAuthStore.user;
  } catch {
    return memoryAuthStore.user;
  }
};

export const setStoredUser = (user) => {
  memoryAuthStore.user = user;
  setLocalItem("legalAI_user", JSON.stringify(user));
};

// ---------------------------
// REQUEST INTERCEPTOR
// ---------------------------
apiClient.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ---------------------------
// RESPONSE INTERCEPTOR
// ---------------------------
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 - Unauthorized
    if (error.response?.status === 401) {
      clearToken();
      // Redirect to login (handled by frontend app.js)
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("unauthorized"));
      }
    }

    const errorMessage =
      error.response?.data?.detail ||
      error.message ||
      "Unknown error";

    console.error("API Error:", errorMessage);
    return Promise.reject(error);
  }
);

// ---------------------------
// AUTHENTICATION ENDPOINTS
// ---------------------------
export const signup = async (email, password, fullName) => {
  try {
    const response = await apiClient.post("/auth/signup", {
      email,
      password,
      full_name: fullName,
    });
    const { access_token, token_type, user } = response.data;
    setToken(access_token);
    setStoredUser(user);
    return { success: true, user, token: access_token };
  } catch (error) {
    const detail = error.response?.data?.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Signup failed"
    );
  }
};

export const login = async (email, password) => {
  try {
    const response = await apiClient.post("/auth/login", {
      email,
      password,
    });
    const { access_token, token_type, user } = response.data;
    setToken(access_token);
    setStoredUser(user);
    return { success: true, user, token: access_token };
  } catch (error) {
    const detail = error.response?.data?.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Login failed"
    );
  }
};

export const getCurrentUser = async () => {
  try {
    const response = await apiClient.get("/auth/me");
    return response.data;
  } catch (error) {
    clearToken();
    throw error;
  }
};

export const logout = async () => {
  try {
    await apiClient.post("/auth/logout");
  } catch (error) {
    console.warn("Logout error:", error);
  } finally {
    clearToken();
  }
};

// ---------------------------
// GLOBAL ERROR HANDLER
// ---------------------------

// ---------------------------
// QUERY LEGAL AI
// ---------------------------
export const askLegalAI = async (payload) => {
  try {
    const response = await apiClient.post("/query", payload);
    return response.data;
  } catch (error) {
    console.error("Failed to query Legal AI:", error);
    throw error;
  }
};

// ---------------------------
// UPLOAD DOCUMENT WITH PROGRESS
// ---------------------------
export const uploadDocument = async (files, onProgress) => {
  const formData = new FormData();

  if (Array.isArray(files)) {
    files.forEach((file) => formData.append("files", file));
  } else {
    formData.append("files", files);
  }

  try {
    const response = await apiClient.post("/upload", formData, {
      timeout: UPLOAD_TIMEOUT,
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        const percent = Math.round(
          (progressEvent.loaded / progressEvent.total) * 100
        );
        if (onProgress) {
          onProgress({
            percent,
            status: `Uploading and analyzing... ${percent}%`,
          });
        }
      },
    });

    return response.data;
  } catch (error) {
    console.error("Upload failed:", error);
    throw error;
  }
};

// ---------------------------
// HEALTH CHECK
// ---------------------------
export const checkHealth = async () => {
  try {
    const response = await apiClient.get("../health");
    return response.data;
  } catch (error) {
    console.error("Health check failed:", error);
    return {
      status: "error",
      message: "Backend not responding",
    };
  }
};

// ---------------------------
// INDEX RECOVERY
// ---------------------------
export const recoverIndex = async () => {
  try {
    const response = await apiClient.post("/index/recover");
    return response.data;
  } catch (error) {
    console.error("Failed to recover index:", error);
    throw error;
  }
};

// ---------------------------
// MODEL MANAGEMENT
// ---------------------------
export const getAvailableModels = async () => {
  try {
    const response = await apiClient.get("/models/ollama");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch available models:", error);
    return {
      status: "error",
      models: [],
      error: error.message,
    };
  }
};

export const selectModel = async (modelName) => {
  try {
    const response = await apiClient.post("/models/select", {
      model: modelName,
    });
    return response.data;
  } catch (error) {
    console.error("Failed to select model:", error);
    throw error;
  }
};

export const getModelRecommendations = async () => {
  try {
    const response = await apiClient.get("/models/recommendations");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch model recommendations:", error);
    return {
      status: "error",
      recommendations: {},
    };
  }
};

// ---------------------------
// FEEDBACK + EVALUATION
// ---------------------------
export const submitFeedback = async ({ query_id, rating, correction = "", tags = [], details = "" }) => {
  try {
    const response = await apiClient.post("/feedback", {
      query_id,
      rating,
      correction,
      tags,
      details,
    });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    throw new Error(typeof detail === "string" ? detail : "Failed to submit feedback");
  }
};

export const getEvaluationSummary = async (days = 30, releaseVersion = "") => {
  try {
    const params = { days };
    if (releaseVersion) params.release_version = releaseVersion;
    const response = await apiClient.get("/eval/summary", { params });
    return response.data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    throw new Error(typeof detail === "string" ? detail : "Failed to fetch evaluation summary");
  }
};

export default apiClient;
