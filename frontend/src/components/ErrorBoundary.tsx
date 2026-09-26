"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  screenName: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Error caught in ${this.props.screenName} ErrorBoundary:`, error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "40px 20px", textAlign: "center" }}>
          <div className="glass-card" style={{ maxWidth: "500px", margin: "0 auto", padding: "30px" }}>
            <AlertTriangle size={48} color="#f43f5e" style={{ marginBottom: "16px" }} />
            <h2 style={{ fontSize: "20px", marginBottom: "8px", color: "#f8fafc" }}>
              Something went wrong in {this.props.screenName}
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "20px" }}>
              {this.state.error?.message || "An unexpected rendering error occurred on this screen."}
            </p>
            <button
              className="btn-primary"
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{ margin: "0 auto" }}
            >
              <RefreshCw size={16} /> Reload Screen
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
