"use client";

import { useEffect, useRef, useState } from "react";
import { getModelContext } from "./webmcp";
import {
  registerScanTools,
  type ScanToolHandlers,
} from "./webmcp-register";

export function useWebMcpScan(handlers: ScanToolHandlers): boolean {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;
  const [live, setLive] = useState(false);

  useEffect(() => {
    const ctx = getModelContext();
    if (!ctx) return;

    const proxy: ScanToolHandlers = {
      scan: (content, contentType) =>
        handlersRef.current.scan(content, contentType),
      loadSpecimen: (id) => handlersRef.current.loadSpecimen(id),
      lastVerdict: () => handlersRef.current.lastVerdict(),
    };

    const ac = new AbortController();
    let cancelled = false;

    registerScanTools(ctx, proxy, ac.signal)
      .then(() => {
        if (!cancelled) setLive(true);
      })
      .catch((err) => {
        console.warn("WebMCP: registerTool failed", err);
      });

    return () => {
      cancelled = true;
      ac.abort();
      setLive(false);
    };
  }, []);

  return live;
}
