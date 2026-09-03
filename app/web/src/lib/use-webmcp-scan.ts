"use client";

import { useEffect, useRef, useState } from "react";
import { getModelContext, type WebMcpDebugCall } from "./webmcp";
import {
  registerScanTools,
  type ScanToolHandlers,
} from "./webmcp-register";

const REGISTERED_TOOLS = [
  "scan_content",
  "load_specimen",
  "list_specimens",
  "explain_verdict",
  "contrast_intent",
];

export function useWebMcpScan(handlers: ScanToolHandlers): boolean {
  const handlersRef = useRef(handlers);
  const [live, setLive] = useState(false);

  useEffect(() => {
    handlersRef.current = handlers;
  });

  useEffect(() => {
    const ctx = getModelContext();
    if (!ctx) return;

    const debug = (window.__ELCARO_WEBMCP_DEBUG__ ??= {
      live: false,
      registered: false,
      tools: [],
      log: [],
    });

    function logCall(call: WebMcpDebugCall) {
      debug.log.unshift(call);
      if (debug.log.length > 50) debug.log.pop();
      window.dispatchEvent(
        new CustomEvent("elcaro:webmcp:log", { detail: call })
      );
    }

    async function timed<T>(
      name: string,
      input: Record<string, unknown>,
      fn: () => Promise<T>
    ): Promise<T> {
      const start = Date.now();
      try {
        const out = await fn();
        logCall({
          name,
          input,
          output: out,
          duration: Date.now() - start,
          ts: Date.now(),
        });
        return out;
      } catch (err) {
        const error = err instanceof Error ? err.message : String(err);
        logCall({
          name,
          input,
          output: null,
          duration: Date.now() - start,
          ts: Date.now(),
          error,
        });
        throw err;
      }
    }

    const proxy: ScanToolHandlers = {
      scan: (content, contentType) =>
        timed("scan_content", { content, content_type: contentType }, () =>
          handlersRef.current.scan(content, contentType)
        ),
      loadSpecimen: (id) => {
        const out = handlersRef.current.loadSpecimen(id);
        logCall({
          name: "load_specimen",
          input: { id },
          output: out,
          duration: 0,
          ts: Date.now(),
        });
        return out;
      },
      lastVerdict: () => {
        const out = handlersRef.current.lastVerdict();
        logCall({
          name: "lastVerdict",
          input: {},
          output: out,
          duration: 0,
          ts: Date.now(),
        });
        return out;
      },
      contrastIntent: (intendedAction) => {
        const out = handlersRef.current.contrastIntent(intendedAction);
        logCall({
          name: "contrast_intent",
          input: { intended_action: intendedAction },
          output: out,
          duration: 0,
          ts: Date.now(),
        });
        return out;
      },
    };

    const ac = new AbortController();
    let cancelled = false;

    registerScanTools(ctx, proxy, ac.signal)
      .then(() => {
        if (cancelled) return;
        debug.live = true;
        debug.registered = true;
        debug.tools = REGISTERED_TOOLS;
        setLive(true);
      })
      .catch((err) => {
        console.warn("WebMCP: registerTool failed", err);
      });

    return () => {
      cancelled = true;
      ac.abort();
      debug.live = false;
      setLive(false);
    };
  }, []);

  return live;
}
