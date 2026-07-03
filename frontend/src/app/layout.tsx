import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgentCommit — AI Open Source Mentor",
  description:
    "Your AI mentor for open source contributions. From finding the perfect issue to getting your pull request merged, AgentCommit guides you every step of the way.",
  keywords: [
    "open source",
    "AI mentor",
    "GitHub",
    "contributions",
    "good first issue",
    "Google ADK",
    "Gemini",
  ],
  authors: [{ name: "AgentCommit" }],
  openGraph: {
    title: "AgentCommit — AI Open Source Mentor",
    description:
      "Your AI mentor for open source contributions. Powered by Google ADK & Gemini 2.5 Pro.",
    type: "website",
    locale: "en_US",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
