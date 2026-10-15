import Link from "next/link";
import { NAV } from "./nav";
import { OffAttribution } from "./off-attribution";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <aside className="hidden w-60 shrink-0 flex-col gap-6 border-r border-border bg-surface p-5 md:flex">
        <Link href="/" aria-label="CookToFit home">
          <picture>
            <source srcSet="/lockup-dark.svg" media="(prefers-color-scheme: dark)" />
            <img src="/lockup-light.svg" alt="CookToFit" className="h-8 w-auto" />
          </picture>
        </Link>
        <nav aria-label="Primary" className="flex flex-col gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-text hover:bg-surface2"
            >
              <span aria-hidden className="w-5 text-center text-muted">
                {item.icon}
              </span>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] md:hidden">
        <Link href="/" aria-label="CookToFit home">
          <picture>
            <source srcSet="/lockup-dark.svg" media="(prefers-color-scheme: dark)" />
            <img src="/lockup-light.svg" alt="CookToFit" className="h-7 w-auto" />
          </picture>
        </Link>
        <Link href="/login" className="min-h-11 content-center text-sm font-medium text-primary">
          Sign in
        </Link>
      </header>

      <div className="flex min-w-0 flex-1 flex-col">
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 pb-24 md:px-8 md:pb-8">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-5xl px-4 pb-24 text-xs text-muted md:px-8 md:pb-6">
          <OffAttribution />
        </footer>
      </div>

      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-10 grid grid-cols-5 border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-text"
          >
            <span aria-hidden className="text-base text-muted">
              {item.icon}
            </span>
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
