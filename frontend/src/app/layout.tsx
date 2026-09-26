import "./globals.css";
import React from "react";

export const metadata = {
  title: "LIVO GROUP OF INDUSTRIES - Footwear ERP",
  description: "Enterprise Resource Planning for Footwear Manufacturing & Distribution",
  manifest: "/manifest.json"
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
        <meta name="theme-color" content="#0f172a" />
      </head>
      <body>{children}</body>
    </html>
  );
}
