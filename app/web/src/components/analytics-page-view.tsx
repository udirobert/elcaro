"use client";

import { useEffect } from "react";
import { trackFunnel, type FunnelEventType } from "@/lib/analytics";

/** Fire-and-forget page-view beacon for server-rendered funnel pages. */
export function AnalyticsPageView({ event }: { event: FunnelEventType }) {
  useEffect(() => {
    trackFunnel(event);
  }, [event]);
  return null;
}
