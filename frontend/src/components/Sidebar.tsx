"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  ShieldAlert,
  TrendingUp,
  ArrowRightLeft,
  FolderOpen,
  Coffee,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/risk", label: "Risk Analysis", icon: ShieldAlert },
  { href: "/market", label: "Market Monitor", icon: TrendingUp },
  { href: "/rebalancing", label: "Rebalancing", icon: ArrowRightLeft },
  { href: "/portfolio", label: "Portfolio", icon: FolderOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-56 bg-neutral-950 border-r border-neutral-800 flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-neutral-800">
        <Coffee className="h-6 w-6 text-accent" />
        <span className="text-base font-semibold tracking-tight text-white">
          Barista AI
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-150",
                active
                  ? "bg-accent/10 text-accent font-medium"
                  : "text-neutral-400 hover:text-white hover:bg-neutral-800/60"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-neutral-800">
        <p className="text-[10px] text-neutral-600 leading-relaxed">
          Multi-Agent Portfolio Risk Management
        </p>
      </div>
    </aside>
  );
}
