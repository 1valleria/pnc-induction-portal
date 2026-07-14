import React from "react";

/**
 * Corporate mark used across the portal.
 *
 * Two variants:
 *   • <BrandMark />     — rounded green badge with the white PNC logo inside
 *                        (favicon-style, sized by the `size` prop).
 *   • <BrandWordmark /> — the full PNC UNIQUE LTD logotype in its natural
 *                        wide aspect ratio, sized by the `width` prop.
 *
 * Both source their pixels from local static assets — no external image
 * hosts, so a strict CSP with `img-src 'self'` continues to hold.
 */
export default function BrandMark({ size = "md", className = "", ariaLabel = "PNC UNIQUE LTD" }) {
  const dims =
    size === "lg" ? "w-14 h-14" : size === "sm" ? "w-8 h-8" : "w-10 h-10";
  return (
    <img
      src="/apple-touch-icon.png"
      alt={ariaLabel}
      width={size === "lg" ? 56 : size === "sm" ? 32 : 40}
      height={size === "lg" ? 56 : size === "sm" ? 32 : 40}
      className={`inline-block rounded-2xl object-contain ${dims} ${className}`}
      draggable="false"
    />
  );
}

export function BrandWordmark({ width = 220, className = "", variant = "dark", ariaLabel = "PNC UNIQUE LTD" }) {
  // `variant` selects the file variant — the black master or a colour-swapped
  // copy that we generated at build time from the same vector source.
  const src =
    variant === "white"
      ? "/pnc-logo-white.svg"
      : variant === "green"
      ? "/pnc-logo-green.svg"
      : "/pnc-logo.svg";
  return (
    <img
      src={src}
      alt={ariaLabel}
      width={width}
      className={`inline-block ${className}`}
      style={{ height: "auto" }}
      draggable="false"
    />
  );
}
