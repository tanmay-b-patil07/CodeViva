
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "CodeViva — Prove You Understand the Code",
    description:
        "A code comprehension and verification platform for students and educators.",
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
