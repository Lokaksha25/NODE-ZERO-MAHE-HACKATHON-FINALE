import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Node Zero - Connectivity-Aware Routing",
  description: "Offline demo for operator-specific route ranking and geo-deferred notifications",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
