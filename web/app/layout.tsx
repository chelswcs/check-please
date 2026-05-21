import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "check-please receipt preview",
  description: "Shareable AI token receipts with a checkout voice.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
