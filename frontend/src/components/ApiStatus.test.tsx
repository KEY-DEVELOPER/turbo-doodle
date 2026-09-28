import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiStatus } from "./ApiStatus";

function renderWithClient() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ApiStatus />
    </QueryClientProvider>,
  );
}

describe("ApiStatus", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows online state with text, not colour alone", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ status: "ok", version: "0.1.0" })),
    );
    renderWithClient();
    expect(await screen.findByText(/API online \(v0\.1\.0\)/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "ok");
  });

  it("shows unreachable state when the API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          { error: { code: "INTERNAL_ERROR", message: "Internal server error", details: {} } },
          { status: 500 },
        ),
      ),
    );
    renderWithClient();
    expect(await screen.findByText("API unreachable")).toBeInTheDocument();
  });
});
