/**
 * Типизированный API-клиент LearnFlow.
 *
 * Типы генерируются из OpenAPI бэкенда (openapi-typescript) —
 * см. scripts/export_openapi.py и `npm run contract:types`.
 * При расхождении контракта править нужно бэкенд, затем регенерировать типы.
 */
import createClient from "openapi-fetch";
import type { paths, components } from "./types";

export type schemas = components["schemas"];

// Удобные алиасы для использования в UI
export type TokenResponse = schemas["TokenResponse"];
export type UserResponse = schemas["UserResponse"];
export type TopicCreate = schemas["TopicCreate"];
export type TopicUpdate = schemas["TopicUpdate"];
export type TopicResponse = schemas["TopicResponse"];
export type CardCreate = schemas["CardCreate"];
export type CardUpdate = schemas["CardUpdate"];
export type CardResponse = schemas["CardResponse"];
export type DraftActionResponse = schemas["DraftActionResponse"];
export type Exercise = schemas["Exercise"];
export type ExerciseAttempt = schemas["ExerciseAttempt"];
export type AttemptResult = schemas["AttemptResult"];
export type LearningStateResponse = schemas["LearningStateResponse"];
export type ReviewResponse = schemas["ReviewResponse"];
export type ReviewCompleteRequest = schemas["ReviewCompleteRequest"];
export type ReviewCompleteResponse = schemas["ReviewCompleteResponse"];
export type ErrorResponse = schemas["ErrorResponse"];

export type CardType = schemas["CardType"];
export type CardStatus = schemas["CardStatus"];
export type CardSource = schemas["CardSource"];

const TOKEN_KEY = "learnflow_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = createClient<paths>({
  baseUrl,
  headers: { "Content-Type": "application/json" },
});

// JWT из localStorage на каждый запрос
api.use({
  onRequest({ request }) {
    const token = getToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});

/** Ошибка API с машиночитаемым кодом из ErrorResponse. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/** Унифицированная обёртка: бросает ApiError при любом !2xx. */
export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promise;
  if (error !== undefined || !response.ok) {
    const err = error as ErrorResponse | undefined;
    throw new ApiError(
      response.status,
      err?.code ?? "unknown_error",
      err?.detail ?? `HTTP ${response.status}`,
    );
  }
  return data as T;
}
