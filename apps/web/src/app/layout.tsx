import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deposit360",
  description: "Manage fixed deposits, documents, and compliance cases."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}