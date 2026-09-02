// Shared interior page header — the visual bridge to the landing hero.
// Same mono eyebrow (text-[10px] uppercase tracking-widest) the landing uses
// ("IPI detection · miner 8848"), so every route opens with the same
// instrument voice. Server component; stays static by default.
export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-enter space-y-3">
      <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
        {eyebrow}
      </p>
      <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-ink">
        {title}
      </h1>
      {children}
    </div>
  );
}
