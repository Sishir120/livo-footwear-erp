import "./globals.css";
import React from "react";
import type { Metadata } from "next";
import { LocaleProvider } from "../context/LocaleContext";

export const metadata: Metadata = {
  title: "LIVO ERP | Production & Stock Ledger",
  description: "Enterprise Resource Planning for Footwear Manufacturing & Distribution — LIVO GROUP OF INDUSTRIES",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" }
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180" }
    ]
  }
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0b1120" />
      </head>
      <body>
        <LocaleProvider>
          {children}
        </LocaleProvider>
      </body>
    </html>
  );
}
