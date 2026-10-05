"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

type FormState = "idle" | "submitting" | "success" | "error";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

interface LeadFormProps {
  /** Netlify registered form name — must match a mirror in /public/netlify-forms.html */
  formName: string;
  heading: string;
  body: string;
  ctaLabel: string;
  /** Optional free-text field beyond email (e.g. corpus description for audits) */
  extraField?: { name: string; label: string; placeholder: string };
}

/** Netlify-backed lead capture — same mechanics as integrate-form.tsx:
 * POSTs form-urlencoded data to "/" against a statically-registered form. */
export function LeadForm({ formName, heading, body, ctaLabel, extraField }: LeadFormProps) {
  const [email, setEmail] = useState("");
  const [extra, setExtra] = useState("");
  const [formState, setFormState] = useState<FormState>("idle");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim() || formState === "submitting") return;
    setFormState("submitting");

    try {
      const params: Record<string, string> = {
        "form-name": formName,
        "bot-field": "",
        email,
      };
      if (extraField) params[extraField.name] = extra;
      const res = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams(params).toString(),
      });
      setFormState(res.ok ? "success" : "error");
      if (res.ok) {
        setEmail("");
        setExtra("");
      }
    } catch {
      setFormState("error");
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-surface px-8 py-10 space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-bold text-ink tracking-tight">{heading}</h2>
        <p className="text-sm text-ink-muted leading-relaxed max-w-lg">{body}</p>
      </div>

      <AnimatePresence mode="wait">
        {formState === "success" ? (
          <motion.p
            key="ok"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
            className="text-sm text-safe font-medium"
          >
            Got it — we&apos;ll be in touch.
          </motion.p>
        ) : (
          <motion.form
            key="form"
            onSubmit={handleSubmit}
            className="space-y-3"
            exit={{ opacity: 0 }}
          >
            <input type="hidden" name="form-name" value={formName} />
            <input type="hidden" name="bot-field" value="" />
            {extraField && (
              <div className="space-y-1.5">
                <label
                  htmlFor={`${formName}-${extraField.name}`}
                  className="block text-xs font-medium text-ink-muted"
                >
                  {extraField.label}
                </label>
                <textarea
                  id={`${formName}-${extraField.name}`}
                  value={extra}
                  onChange={(e) => setExtra(e.target.value)}
                  placeholder={extraField.placeholder}
                  rows={3}
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-violet/30"
                />
              </div>
            )}
            <div className="flex gap-3">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="flex-1 rounded-lg border border-border bg-canvas px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-violet/30"
              />
              <button
                type="submit"
                disabled={formState === "submitting"}
                className="rounded-lg bg-ink text-canvas px-5 py-2 text-sm font-semibold hover:bg-ink/90 transition-colors disabled:opacity-50"
              >
                {formState === "submitting" ? "Sending…" : ctaLabel}
              </button>
            </div>
            {formState === "error" && (
              <p className="text-xs text-dangerous">
                Something went wrong — try again or email us directly.
              </p>
            )}
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}
