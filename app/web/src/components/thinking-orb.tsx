"use client";

export function ThinkingOrb() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="relative">
        {/* Outer pulse ring */}
        <div className="absolute inset-0 rounded-full bg-blue-500/20 animate-pulse-ring" />
        {/* Inner spinning gradient orb */}
        <div className="relative w-16 h-16 rounded-full bg-gradient-to-tr from-blue-500 via-purple-500 to-cyan-400 animate-spin-slow opacity-80 blur-[1px]" />
        {/* Center glow */}
        <div className="absolute inset-3 rounded-full bg-background/80 backdrop-blur-sm" />
        {/* Label */}
      </div>
      <span className="ml-4 text-muted text-sm font-mono">Scanning...</span>
    </div>
  );
}
