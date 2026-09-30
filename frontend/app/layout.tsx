import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ayan.J — AI Frontend Developer",
  description:
    "Portfolio of Ayan Jamali — AI engineering and frontend development.",
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