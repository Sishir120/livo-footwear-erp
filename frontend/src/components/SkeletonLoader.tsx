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
          <div style={{ height: "24px", width: "220px", background: "#E2E8F0", borderRadius: "4px", marginBottom: "8px" }} />
          <div style={{ height: "14px", width: "320px", background: "#F1F5F9", borderRadius: "4px" }} />
        </div>
        <div style={{ height: "36px", width: "120px", background: "#E2E8F0", borderRadius: "4px" }} />
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
                  background: "#FFFFFF",
                  border: "1px solid #CBD5E1",
                  borderRadius: "4px",
                  padding: "16px"
                }}
              >
                <div style={{ height: "12px", width: "60%", background: "#F1F5F9", borderRadius: "4px", marginBottom: "12px" }} />
                <div style={{ height: "24px", width: "40%", background: "#E2E8F0", borderRadius: "4px" }} />
              </div>
            ))}
          </div>

          {/* Chart area skeleton */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            <div
              style={{
                height: "280px",
                background: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                padding: "20px"
              }}
            >
              <div style={{ height: "16px", width: "150px", background: "#E2E8F0", borderRadius: "4px", marginBottom: "20px" }} />
              <div style={{ height: "200px", background: "#F8FAFC", borderRadius: "4px", display: "flex", alignItems: "flex-end", gap: "12px", padding: "12px", border: "1px solid #F1F5F9" }}>
                {[40, 65, 85, 30, 95, 60, 75].map((h, idx) => (
                  <div key={idx} style={{ flex: 1, height: `${h}%`, background: "#CBD5E1", borderRadius: "2px" }} />
                ))}
              </div>
            </div>
            <div
              style={{
                height: "280px",
                background: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                padding: "20px"
              }}
            >
              <div style={{ height: "16px", width: "180px", background: "#E2E8F0", borderRadius: "4px", marginBottom: "20px" }} />
              <div style={{ height: "200px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: "140px", height: "140px", borderRadius: "50%", border: "16px solid #E2E8F0" }} />
              </div>
            </div>
          </div>
        </>
      )}

      {/* Table rows skeleton */}
      <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "16px" }}>
        <div style={{ height: "36px", background: "#F1F5F9", borderRadius: "4px", marginBottom: "12px" }} />
        {[1, 2, 3, 4, 5].map((r) => (
          <div key={r} style={{ height: "28px", background: "#F8FAFC", borderRadius: "4px", marginBottom: "8px", borderBottom: "1px solid #F1F5F9" }} />
        ))}
      </div>
    </div>
  );
}
