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
  },
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true,
    },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="light" style={{ backgroundColor: "#F8FAFC", colorScheme: "light" }}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <meta name="color-scheme" content="light" />
        <meta name="theme-color" content="#F8FAFC" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body className="min-h-screen bg-[#F8FAFC] text-[#0F172A] antialiased" style={{ backgroundColor: "#F8FAFC" }}>
        <LocaleProvider>
          {children}
        </LocaleProvider>
      </body>
    </html>
  );
}
