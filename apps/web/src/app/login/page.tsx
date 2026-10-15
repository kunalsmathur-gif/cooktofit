import type { Metadata } from "next";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-8">
      <div>
        <h1 className="font-display text-2xl font-bold">Sign in</h1>
        <p className="mt-1 text-sm text-muted">
          CookToFit is invite-only. Use the phone number or Google account you were invited with.
        </p>
      </div>
      <form className="flex flex-col gap-3" aria-describedby="auth-status">
        <label htmlFor="phone" className="text-sm font-medium">
          Mobile number
        </label>
        <input
          id="phone"
          name="phone"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="+91 98765 43210"
          disabled
          className="min-h-11 rounded-md border border-border bg-surface px-3 text-base disabled:opacity-60"
        />
        <button
          type="button"
          disabled
          className="min-h-11 rounded-md bg-primary font-medium text-on-primary disabled:opacity-60"
        >
          Send code on WhatsApp
        </button>
        <div className="flex items-center gap-3 text-xs text-muted">
          <span className="h-px flex-1 bg-border" />
          or
          <span className="h-px flex-1 bg-border" />
        </div>
        <button
          type="button"
          disabled
          className="min-h-11 rounded-md border border-border bg-surface font-medium disabled:opacity-60"
        >
          Continue with Google
        </button>
      </form>
      <p id="auth-status" className="text-xs text-muted">
        Sign-in is being built (Phase 1).
      </p>
    </div>
  );
}
