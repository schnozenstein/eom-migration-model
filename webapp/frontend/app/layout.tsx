import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EOM | Migration Research Observatory",
  description: "An empirical observatory for migration dynamics and destination systems."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
