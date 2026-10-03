import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Resolver",
  description: "Sube una foto o un PDF de un KenKen y recibe la solución dibujada sobre tu imagen.",
};

export default function SolverLayout({ children }: { children: ReactNode }) {
  return children;
}
