"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type WorkspaceSidebarProps = {
  roles: string[];
};

type NavigationItem = {
  href: string;
  label: string;
};

function navigationForRoles(roles: string[]): NavigationItem[] {
  const has = (...allowed: string[]) => roles.some((role) => allowed.includes(role));
  const items: NavigationItem[] = [{ href: "/", label: "Dashboard" }];

  if (has("institution_applicant", "institution_user")) {
    items.push(
      { href: "/institution/submit", label: "Register FDR" },
      { href: "/institution/my-submissions", label: "My submissions" },
      { href: "/institution/renewals", label: "Renewals" },
      { href: "/releases", label: "Releases" }
    );
  } else {
    if (has("scrutiny_officer")) {
      items.push({ href: "/scrutiny", label: "Scrutiny" });
    } else if (has("compliance_administrator", "admin")) {
      items.push({ href: "/scrutiny", label: "Escalations" });
    }
    if (has("finance_officer", "admin")) {
      items.push(
        { href: "/institution/renewals", label: "Renewals" },
        { href: "/releases", label: "Finance review" }
      );
    } else if (has("approving_authority")) {
      items.push({ href: "/releases", label: "Final approvals" });
    }
  }

  if (
    has(
      "institution_applicant",
      "institution_user",
      "scrutiny_officer",
      "compliance_administrator",
      "finance_officer",
      "approving_authority",
      "auditor",
      "admin"
    )
  ) {
    items.push({ href: "/lifecycle", label: "Lifecycle" });
  }
  items.push({ href: "/notifications", label: "Notifications" });
  if (has("compliance_administrator", "approving_authority", "auditor", "admin")) {
    items.push({ href: "/audit", label: "Audit history" });
  }
  return items;
}

export function WorkspaceSidebar({ roles }: WorkspaceSidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="workspace-sidebar">
      <Link className="sidebar-brand" href="/" aria-label="Deposit360 dashboard">
        <span className="brand-mark brand-mark-small">D</span>
        <span>Deposit360</span>
      </Link>
      <nav className="sidebar-nav" aria-label="Workspace navigation">
        {navigationForRoles(roles).map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={active ? "sidebar-link sidebar-link-active" : "sidebar-link"}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
