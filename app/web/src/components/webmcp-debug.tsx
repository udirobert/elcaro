"use client";

import { useEffect, useState } from "react";
import type {
  TestingModelContextToolInfo,
  WebMcpDebugState,
} from "@/lib/webmcp";

function readDebug(): WebMcpDebugState | undefined {
  return typeof window !== "undefined"
    ? window.__ELCARO_WEBMCP_DEBUG__
    : undefined;
}

async function fetchTestingTools(): Promise<TestingModelContextToolInfo[]> {
  if (typeof navigator === "undefined") return [];
  const testing = navigator.modelContextTesting;
  if (!testing || typeof testing.getTools !== "function") return [];
  try {
    return await testing.getTools();
  } catch {
    return [];
  }
}

export function WebMcpDebug({ live }: { live: boolean }) {
  const [open, setOpen] = useState(false);
  const [debug, setDebug] = useState<WebMcpDebugState | undefined>(readDebug);
  const [tools, setTools] = useState<TestingModelContextToolInfo[]>([]);

  useEffect(() => {
    let mounted = true;
    function refresh() {
      if (!mounted) return;
      setDebug(readDebug());
    }
    const onLog = () => refresh();
    window.addEventListener("elcaro:webmcp:log", onLog);
    const interval = setInterval(refresh, 1000);
    refresh();
    return () => {
      mounted = false;
      window.removeEventListener("elcaro:webmcp:log", onLog);
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    fetchTestingTools().then((t) => {
      if (mounted) setTools(t);
    });
    return () => {
      mounted = false;
    };
  }, [live]);

  const active = live || tools.length > 0;
  if (!active) return null;

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              live ? "bg-safe" : "bg-ink-faint"
            }`}
            aria-hidden="true"
          />
          <span className="text-sm font-medium text-ink">
            WebMCP {live ? "live" : "detector ready"}
          </span>
          <span className="text-xs text-ink-faint font-mono">
            {tools.length > 0 ? `${tools.length} tools exposed` : ""}
          </span>
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-xs text-violet font-medium hover:text-violet/80 transition-colors"
          type="button"
        >
          {open ? "Hide debug" : "Debug"}
        </button>
      </div>

      {open && (
        <div className="mt-4 space-y-4 text-sm">
          <div>
            <h4 className="text-ink-muted font-medium mb-1">Exposed tools</h4>
            <ul className="list-disc pl-4 space-y-0.5 text-ink-faint">
              {tools.length > 0
                ? tools.map((t) => <li key={t.name}>{t.name}</li>)
                : debug?.tools.map((t) => <li key={t}>{t}</li>)}
            </ul>
          </div>

          <div>
            <h4 className="text-ink-muted font-medium mb-1">Recent calls</h4>
            {debug && debug.log.length > 0 ? (
              <ul className="space-y-2 max-h-48 overflow-auto pr-2">
                {debug.log.slice(0, 20).map((call, i) => (
                  <li
                    key={i}
                    className="font-mono text-[11px] text-ink-faint border-l-2 border-violet pl-2"
                  >
                    <span className="text-ink">{call.name}</span>
                    {call.error ? (
                      <span className="text-dangerous"> — {call.error}</span>
                    ) : (
                      <span> — {call.duration}ms</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-ink-faint text-xs">No calls logged yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
