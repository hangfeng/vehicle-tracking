import { create } from "zustand";
import axios from "axios";
import type { User, UserRole } from "../types";
import { api } from "../api/client";

type TokenClaims = {
  sub?: string;
  role?: UserRole;
};

function decodeTokenClaims(token: string | null): TokenClaims {
  if (!token) return {};
  try {
    const [, payload] = token.split(".");
    if (!payload) return {};
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "="));
    return JSON.parse(decoded) as TokenClaims;
  } catch {
    return {};
  }
}

const initialToken = localStorage.getItem("access_token");
const initialClaims = decodeTokenClaims(initialToken);

interface AuthState {
  user: User | null;
  token: string | null;
  tokenRole: UserRole | null;
  tokenSubject: string | null;
  authError: string | null;
  isHydrating: boolean;
  login: (phone: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: initialToken,
  tokenRole: initialClaims.role ?? null,
  tokenSubject: initialClaims.sub ?? null,
  authError: null,
  isHydrating: Boolean(initialToken),

  login: async (phone, password) => {
    const resp = await api.post("/auth/login", { phone, password });
    const token = resp.data.access_token;
    const claims = decodeTokenClaims(token);
    localStorage.setItem("access_token", token);
    set({
      token,
      tokenRole: claims.role ?? null,
      tokenSubject: claims.sub ?? null,
      authError: null,
      isHydrating: true,
    });
    const me = await api.get("/auth/me");
    set({ user: me.data, authError: null, isHydrating: false });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({
      user: null,
      token: null,
      tokenRole: null,
      tokenSubject: null,
      authError: null,
      isHydrating: false,
    });
  },

  fetchMe: async () => {
    set({ isHydrating: true, authError: null });
    try {
      const resp = await api.get("/auth/me");
      set({ user: resp.data, authError: null, isHydrating: false });
    } catch (error: unknown) {
      const detail = axios.isAxiosError(error)
        ? `${error.response?.status ?? "network"} ${String(error.response?.data?.detail ?? error.message)}`
        : "unknown error";
      try {
        const usersResp = await api.get<User[]>("/users");
        const currentUser = usersResp.data.find((item) => item.id === get().tokenSubject);
        if (currentUser) {
          set({
            user: currentUser,
            authError: `已通过用户列表恢复当前用户，/auth/me 失败: ${detail}`,
            isHydrating: false,
          });
          return;
        }
      } catch {
        // keep original auth error below
      }
      set({
        user: null,
        authError: `未能从服务器恢复完整用户信息: ${detail}`,
        isHydrating: false,
      });
    }
  },
}));
