"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    LineChart,
    FlaskConical,
    Play,
    Zap,
    Database,
    Settings,
    TrendingUp,
    Activity,
    Wifi,
    WifiOff,
} from "lucide-react";

const navSections = [
    {
        title: "Overview",
        items: [
            { label: "Dashboard", href: "/", icon: LayoutDashboard },
            { label: "Market Data", href: "/market", icon: TrendingUp },
        ],
    },
    {
        title: "Strategy",
        items: [
            { label: "Strategies", href: "/strategies", icon: FlaskConical },
            { label: "Paper Trade", href: "/paper-trade", icon: Play },
        ],
    },
    {
        title: "Execution",
        items: [
            { label: "Live Trading", href: "/live", icon: Zap },
            { label: "Positions", href: "/positions", icon: Activity },
        ],
    },
    {
        title: "System",
        items: [
            { label: "Data Explorer", href: "/data", icon: Database },
            { label: "Settings", href: "/settings", icon: Settings },
        ],
    },
];

interface BrokerStatus {
    name: string;
    status: "connected" | "disconnected" | "pending";
}

const brokerStatuses: BrokerStatus[] = [
    { name: "Dhan", status: "connected" },
    { name: "Bigul Connect", status: "pending" },
    { name: "Bigul XTS", status: "connected" },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="logo-icon">AG</div>
                <h1>Antigravity</h1>
            </div>

            <nav className="sidebar-nav">
                {navSections.map((section) => (
                    <div key={section.title} className="nav-section">
                        <div className="nav-section-title">{section.title}</div>
                        {section.items.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`nav-item ${isActive ? "active" : ""}`}
                                >
                                    <Icon />
                                    <span>{item.label}</span>
                                </Link>
                            );
                        })}
                    </div>
                ))}
            </nav>

            <div className="sidebar-status">
                {brokerStatuses.map((broker) => (
                    <div key={broker.name} className="status-indicator" style={{ marginBottom: 6 }}>
                        <span className={`status-dot ${broker.status}`} />
                        <span>{broker.name}</span>
                        {broker.status === "connected" ? (
                            <Wifi style={{ width: 12, height: 12, marginLeft: "auto", color: "var(--green)" }} />
                        ) : broker.status === "pending" ? (
                            <Activity style={{ width: 12, height: 12, marginLeft: "auto", color: "var(--yellow)" }} />
                        ) : (
                            <WifiOff style={{ width: 12, height: 12, marginLeft: "auto", color: "var(--red)" }} />
                        )}
                    </div>
                ))}
            </div>
        </aside>
    );
}
