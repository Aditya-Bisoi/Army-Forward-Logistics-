import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const TOKEN_KEY = "ct_token";
axios.defaults.withCredentials = true;
axios.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const saveSession = data => { if (data?.token) localStorage.setItem(TOKEN_KEY, data.token); };
export const clearSession = () => localStorage.removeItem(TOKEN_KEY);
export const apiError = e => typeof e?.response?.data?.detail === "string" ? e.response.data.detail : "Unable to reach control tower";
export const colors = { CRITICAL: "#ff5c57", WARNING: "#ffb547", NORMAL: "#4bd38a", HUB: "#62b4ff", DEPOT: "#f3c969" };
export const fmt = n => (n ?? 0).toLocaleString();
export { axios };
