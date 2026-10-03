import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import Providers from "@/components/Providers";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://kenkenlab.vercel.app";
const description =
  "KenKenLab lee un puzzle KenKen desde una foto o imagen, lo resuelve con programación con restricciones y dibuja la solución sobre tu imagen.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "KenKenLab",
    template: "%s — KenKenLab",
  },
  description,
  keywords: ["KenKen", "solver", "visión computacional", "programación con restricciones", "CP-SAT"],
  openGraph: {
    title: "KenKenLab",
    description,
    url: siteUrl,
    siteName: "KenKenLab",
    locale: "es_PE",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#1f4fd8",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        <Providers>
          <Nav />
          <div className="flex flex-1 flex-col">{children}</div>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
