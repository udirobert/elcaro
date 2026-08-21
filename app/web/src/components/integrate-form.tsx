"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

type FormState = "idle" | "submitting" | "success" | "error";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function IntegrateForm() {
  const [email, setEmail] = useState("");
  const [formState, setFormState] = useState<FormState>("idle");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim() || formState === "submitting") return;

    setFormState("submitting");

    try {
      // Netlify form submission: POST form-encoded data to the page URL.
      // The form is registered by the static HTML mirror in /public/netlify-forms.html.
      const body = new URLSearchParams({
        "form-name": "elcaro-waitlist",
        "bot-field": "",
        email,
      });

      const res = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });

      if (res.ok) {
        setFormState("success");
        setEmail("");
      } else {
        setFormState("error");
      }
    } catch {
      setFormState("error");
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-surface px-8 py-10 space-y-6">
      {/* Heading */}
      <div className="space-y-2">
        <h2 className="text-xl font-bold text-ink tracking-tight">
          Stay ahead of attackers
        </h2>
        <p className="text-sm text-ink-muted leading-relaxed max-w-sm">
          New injection techniques emerge weekly. We track them, build detectors
          for them, and send a short brief when something worth knowing appears.
          No noise — only patterns your agent is likely to encounter.
        </p>
      </div>

      {/* What you get */}
      <ul className="space-y-2">
        {[
          "New injection technique breakdowns — with real examples",
          "Pattern releases as we add them to the detection engine",
          "Practical hardening tips for specific agent use cases",
        ].map((item, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm text-ink-muted">
            <span className="text-violet mt-0.5 shrink-0">→</span>
            {item}
          </li>
        ))}
      </ul>

      {/* Form */}
      <AnimatePresence mode="wait">
        {formState === "success" ? (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: EASE_OUT }}
            className="flex items-center gap-3 py-3"
          >
            <span className="text-safe text-lg">✓</span>
            <div>
              <p className="text-sm font-semibold text-ink">You&apos;re in.</p>
              <p className="text-xs text-ink-muted">
                First brief lands when the next significant pattern drops.
              </p>
            </div>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            onSubmit={handleSubmit}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
            className="space-y-3"
          >
            {/* Honeypot field — hidden from humans, traps bots */}
            <input type="hidden" name="form-name" value="elcaro-waitlist" />
            <div hidden aria-hidden="true">
              <input name="bot-field" tabIndex={-1} autoComplete="off" />
            </div>
            <div className="flex gap-2">
              <input
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@youragent.com"
                required
                disabled={formState === "submitting"}
                className="flex-1 px-4 py-2.5 rounded-xl bg-canvas border border-border text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-violet/50 focus:ring-1 focus:ring-violet/20 transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={formState === "submitting" || !email.trim()}
                className="px-5 py-2.5 rounded-xl bg-ink text-canvas text-sm font-semibold hover:scale-[1.02] active:scale-[0.98] transition-transform disabled:opacity-30 disabled:cursor-not-allowed disabled:scale-100 whitespace-nowrap"
              >
                {formState === "submitting" ? (
                  <span className="flex items-center gap-2">
                    <motion.span
                      className="w-3 h-3 rounded-full border-2 border-canvas/40 border-t-canvas"
                      animate={{ rotate: 360 }}
                      transition={{
                        duration: 0.6,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    />
                    Sending
                  </span>
                ) : (
                  "Get updates"
                )}
              </button>
            </div>

            {formState === "error" && (
              <motion.p
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-dangerous"
              >
                Something went wrong — try again or email{" "}
                <a
                  href="mailto:hello@elcaro.trustfall.xyz"
                  className="underline underline-offset-2"
                >
                  hello@elcaro.trustfall.xyz
                </a>
              </motion.p>
            )}

            <p className="text-[11px] text-ink-faint">
              No spam. Unsubscribe any time.
            </p>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}
