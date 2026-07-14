import React from "react";
import { ShieldCheck } from "lucide-react";

/**
 * Brand mark used across the portal. A rounded shield in the corporate
 * green with a matching stroke — rendered inline so the CSP does not
 * need to allow external image sources.
 */
export default function BrandMark({ size = "md", className = "" }) {
  const dims =
    size === "lg" ? "w-14 h-14" : size === "sm" ? "w-8 h-8" : "w-10 h-10";
  const icon =
    size === "lg" ? "w-7 h-7" : size === "sm" ? "w-4 h-4" : "w-5 h-5";
  return (
    <div
      className={`inline-flex items-center justify-center rounded-2xl bg-[#166534] text-white ${dims} ${className}`}
      aria-hidden="true"
    >
      <ShieldCheck className={icon} strokeWidth={2} />
    </div>
  );
}
