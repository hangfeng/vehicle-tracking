import { create } from "zustand";
import type { User } from "../types";
import { api } from "../api/client";

interface AuthState {
  user: User | null;
  token: string | null;
  login: (phone: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("access_token"),

  login: async (phone, password) => {
    const resp = await api.post("/auth/login", { phone, password });
    const token = resp.data.access_token;
    localStorage.setItem("access_token", token);
    set({ token });
    const me = await api.get("/auth/me");
    set({ user: me.data });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ user: null, token: null });
  },

  fetchMe: async () => {
    try {
      const resp = await api.get("/auth/me");
      set({ user: resp.data });
    } catch {
      set({ user: null, token: null });
    }
  },
}));
