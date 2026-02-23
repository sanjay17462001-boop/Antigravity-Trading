"use client";

import { Bell, Search } from "lucide-react";

interface HeaderProps {
    title: string;
}

export default function Header({ title }: HeaderProps) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
    });

    return (
        <header className="header">
            <h2 className="header-title">{title}</h2>

            <div className="header-actions">
                <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    background: "var(--bg-tertiary)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                    padding: "6px 12px",
                    color: "var(--text-muted)",
                    fontSize: 13,
                }}>
                    <Search style={{ width: 14, height: 14 }} />
                    <span>Search...</span>
                    <span style={{
                        fontSize: 11,
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: "var(--bg-secondary)",
                        color: "var(--text-dim)",
                        marginLeft: 24,
                    }}>
                        Ctrl+K
                    </span>
                </div>

                <button className="btn-icon" style={{ position: "relative" }}>
                    <Bell style={{ width: 16, height: 16 }} />
                    <span style={{
                        position: "absolute",
                        top: 6,
                        right: 6,
                        width: 6,
                        height: 6,
                        background: "var(--red)",
                        borderRadius: "50%",
                    }} />
                </button>

                <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 12,
                    color: "var(--text-muted)",
                }}>
                    {timeStr}
                </div>
            </div>
        </header>
    );
}
