"use client";

import React from "react";

interface SkeletonProps {
  title?: string;
  type?: "dashboard" | "table" | "form";
}

export function SkeletonLoader({ title = "Loading Module...", type = "dashboard" }: SkeletonProps) {
  return (
    <div style={{ padding: "8px 0", animation: "pulse 1.5s ease-in-out infinite" }}>
      {/* Header bar skeleton */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <div style={{ height: "24px", width: "220px", background: "#1e293b", borderRadius: "4px", marginBottom: "8px" }} />
          <div style={{ height: "14px", width: "320px", background: "#0f172a", borderRadius: "4px" }} />
        </div>
        <div style={{ height: "36px", width: "120px", background: "#1e293b", borderRadius: "6px" }} />
      </div>

      {type === "dashboard" && (
        <>
          {/* Stat cards skeleton */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                style={{
                  height: "90px",
                  background: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: "8px",
                  padding: "16px"
                }}
              >
                <div style={{ height: "12px", width: "60%", background: "#1e293b", borderRadius: "4px", marginBottom: "12px" }} />
                <div style={{ height: "24px", width: "40%", background: "#334155", borderRadius: "4px" }} />
              </div>
            ))}
          </div>

          {/* Chart area skeleton */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div
              style={{
                height: "280px",
                background: "#0f172a",
                border: "1px solid #1e293b",
                borderRadius: "8px",
                padding: "20px"
              }}
            >
              <div style={{ height: "16px", width: "150px", background: "#1e293b", borderRadius: "4px", marginBottom: "20px" }} />
              <div style={{ height: "200px", background: "rgba(30, 41, 59, 0.4)", borderRadius: "6px", display: "flex", alignItems: "flex-end", gap: "12px", padding: "12px" }}>
                {[40, 65, 85, 30, 95, 60, 75].map((h, idx) => (
                  <div key={idx} style={{ flex: 1, height: `${h}%`, background: "#1e293b", borderRadius: "4px" }} />
                ))}
              </div>
            </div>
            <div
              style={{
                height: "280px",
                background: "#0f172a",
                border: "1px solid #1e293b",
                borderRadius: "8px",
                padding: "20px"
              }}
            >
              <div style={{ height: "16px", width: "180px", background: "#1e293b", borderRadius: "4px", marginBottom: "20px" }} />
              <div style={{ height: "200px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: "140px", height: "140px", borderRadius: "50%", border: "16px solid #1e293b" }} />
              </div>
            </div>
          </div>
        </>
      )}

      {/* Table rows skeleton */}
      <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "16px" }}>
        <div style={{ height: "36px", background: "#1e293b", borderRadius: "4px", marginBottom: "12px" }} />
        {[1, 2, 3, 4, 5].map((r) => (
          <div key={r} style={{ height: "28px", background: "rgba(30, 41, 59, 0.3)", borderRadius: "4px", marginBottom: "8px" }} />
        ))}
      </div>
    </div>
  );
}
