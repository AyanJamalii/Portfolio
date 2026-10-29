import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";
import SmoothScrolling from "@/components/SmoothScrolling";
import CustomCursor from "../components/CustomCursor";

const geist = Geist({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  title: "Ayan J. — AI Frontend Developer",
  description: "Portfolio of Ayan Jamali — AI engineering and frontend development.",
  openGraph: {
    title: "Ayan J. — AI Frontend Developer",
    description: "Portfolio of Ayan Jamali — AI engineering and frontend development.",
    url: "https://meetayan.vercel.app",
    siteName: "Ayan Portfolio",
    images: [
      {
        url: "https://meetayan.vercel.app/icon.png", // Agar aapki image public folder mein ya root par hai
        width: 1200,
        height: 630,
        alt: "Ayan J. Portfolio Preview",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Ayan J. — AI Frontend Developer",
    description: "Portfolio of Ayan Jamali — AI engineering and frontend development.",
    images: ["https://meetayan.vercel.app/icon.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body>
        <SmoothScrolling>
          {/* <CustomCursor /> */}
          {children}
        </SmoothScrolling>
      </body>
    </html>
  );
}