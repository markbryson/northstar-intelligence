import { BarChart3, Globe2, LayoutDashboard, Menu, Package, RotateCcw, ShoppingBag, Users, X } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useState } from "react";
import { FilterBar } from "../filters/FilterBar";

const navigation = [
  { label: "Overview", to: "/", icon: LayoutDashboard },
  { label: "Sales analytics", to: "/sales", icon: BarChart3 },
  { label: "Product analytics", to: "/products", icon: Package },
  { label: "Customer analytics", to: "/customers", icon: Users },
  { label: "Geography", to: "/geography", icon: Globe2 },
  { label: "Returns", to: "/returns", icon: RotateCcw },
];

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const current = navigation.find((item) => item.to === location.pathname) ?? navigation[0];
  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "mobile-nav-open" : ""}`}>
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><ShoppingBag size={18} /></span><span className="brand-text">northstar<span>intelligence</span></span><button className="mobile-close icon-button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button></div>
        <div className="workspace-switcher"><span className="workspace-dot" /> <span className="workspace-copy">Retail workspace<small>Online Retail II</small></span><span className="workspace-chevron">⌄</span></div>
        <p className="nav-label">Workspace</p>
        <nav className="main-nav" aria-label="Main navigation">{navigation.map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`} onClick={() => setMobileOpen(false)}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
        <div className="sidebar-bottom"><div className="data-status"><span className="status-pulse" /><div><strong>Data connected</strong><small>SQLite · 1.03m rows</small></div></div><p className="sidebar-note">Historical archive<br /><span>2009 — 2011</span></p></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><button className="mobile-menu icon-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div><p className="breadcrumb">Workspace <span>/</span> {current.label}</p><h1>{current.label}</h1></div><div className="topbar-actions"><span className="archive-badge"><span className="status-pulse" /> Historical dataset</span><button className="avatar" aria-label="Workspace profile">NS</button><button className="collapse-toggle icon-button" onClick={() => setCollapsed(!collapsed)} aria-label="Collapse sidebar"><Menu size={19} /></button></div></header>
        <div className="content-wrap"><FilterBar /><Outlet /></div>
      </main>
    </div>
  );
}
