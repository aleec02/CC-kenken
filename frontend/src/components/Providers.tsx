"use client";

import { MotionConfig } from "framer-motion";
import type { ReactNode } from "react";

/** Respeta prefers-reduced-motion en todas las animaciones de Framer Motion. */
export default function Providers({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
