"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

/** Backend reachability. Status is shown with text + icon, never colour alone (WCAG 2.2 AA). */
export function ApiStatus() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error } = await api.GET("/health");
      if (error || !data) throw new Error("health check failed");
      return data;
    },
  });

  let icon = "…";
  let label = "Checking API";
  let state = "pending";
  if (isError) {
    icon = "✕";
    label = "API unreachable";
    state = "down";
  } else if (!isPending && data) {
    icon = "✓";
    label = `API online (v${data.version})`;
    state = "ok";
  }

  return (
    <p className="api-status" data-state={state} role="status">
      <span aria-hidden="true">{icon}</span> {label}
    </p>
  );
}
