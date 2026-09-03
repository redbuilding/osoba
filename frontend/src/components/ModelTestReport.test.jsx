import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ModelTestReport from "./ModelTestReport";

const sampleResults = [
  {
    model: "openai/gpt-5.6-sol",
    provider: "openai",
    status: "ok",
    latency_ms: 812,
    text: "Hello! I'm ready to help.",
    error: null,
  },
  {
    model: "anthropic/claude-sonnet-5",
    provider: "anthropic",
    status: "error",
    latency_ms: 1500,
    text: null,
    error: "AuthenticationError: invalid api key",
  },
  {
    model: "openrouter/z-ai/glm-5.3",
    provider: "openrouter",
    status: "timeout",
    latency_ms: 30000,
    text: null,
    error: "Timed out after 30s",
  },
];

const summary = { total: 3, ok: 1, failed: 2, avg_latency_ms: 812, providers: ["openai", "anthropic", "openrouter"] };

describe("ModelTestReport", () => {
  it("renders the header and summary counts", () => {
    render(<ModelTestReport results={sampleResults} summary={summary} />);
    expect(screen.getByText("Model Diagnostics")).toBeInTheDocument();
    expect(screen.getByText("3 models")).toBeInTheDocument();
    expect(screen.getByText("1 ok")).toBeInTheDocument();
    expect(screen.getByText("2 failed")).toBeInTheDocument();
    expect(screen.getByText(/avg 812 ms/)).toBeInTheDocument();
  });

  it("renders every model name", () => {
    render(<ModelTestReport results={sampleResults} summary={summary} />);
    expect(screen.getByText("openai/gpt-5.6-sol")).toBeInTheDocument();
    expect(screen.getByText("anthropic/claude-sonnet-5")).toBeInTheDocument();
    expect(screen.getByText("openrouter/z-ai/glm-5.3")).toBeInTheDocument();
  });

  it("shows the reply snippet for a working model", () => {
    render(<ModelTestReport results={sampleResults} summary={summary} />);
    expect(screen.getByText("Hello! I'm ready to help.")).toBeInTheDocument();
  });

  it("shows the error message for a failed model", () => {
    render(<ModelTestReport results={sampleResults} summary={summary} />);
    expect(screen.getByText("AuthenticationError: invalid api key")).toBeInTheDocument();
    expect(screen.getByText("Timed out after 30s")).toBeInTheDocument();
  });

  it("shows a loading state while testing", () => {
    render(<ModelTestReport results={[]} summary={{}} loading />);
    expect(screen.getByText(/Testing models/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no results", () => {
    render(<ModelTestReport results={[]} summary={{}} />);
    expect(screen.getByText(/No models to test/)).toBeInTheDocument();
  });
});
