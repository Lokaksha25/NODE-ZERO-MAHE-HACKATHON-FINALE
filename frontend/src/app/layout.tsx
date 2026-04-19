import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reachbl — Connectivity-Aware Routing",
  description:
    "Routes that understand your signal. Predict connectivity dead zones, defer notifications intelligently, and stay connected on the road.",
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
