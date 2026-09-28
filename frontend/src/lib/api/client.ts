/**
 * Typed API client. Types come from `src/lib/api/generated/schema.ts`, generated from the
 * backend OpenAPI schema (`npm run gen:api`) — never hand-edit generated files.
 * Provider API keys never reach the browser; the browser only talks to our backend.
 */
import createClient from "openapi-fetch";

import type { components, paths } from "./generated/schema";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const api = createClient<paths>({
  baseUrl: API_BASE_URL,
  // Resolve fetch per call (not at import) so tests and instrumentation can replace it.
  fetch: (request) => globalThis.fetch(request),
});

/** Standard error body (PRD 14.6): `{ error: { code, message, details } }`. */
export type ApiError = components["schemas"]["ErrorResponse"];

export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiError | undefined,
  ) {
    super(body?.error.message ?? `Request failed with status ${status}`);
    this.name = "ApiRequestError";
  }

  get code(): string | undefined {
    return this.body?.error.code;
  }
}
