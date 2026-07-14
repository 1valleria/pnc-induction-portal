import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import SiteFooter from "@/components/SiteFooter";
import BrandMark from "@/components/BrandMark";

/**
 * Shared layout for the static legal / about / contact pages. Renders a
 * consistent header (brand + back link), a max-width prose container, and
 * the site footer with placeholders. Purely presentational — no data.
 */
export default function LegalShell({ title, subtitle, children }) {
  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAF9]">
      <header className="bg-white border-b border-[#E7E5E4]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-3">
          <BrandMark size="sm" />
          <div className="leading-tight">
            <div className="font-heading text-base text-[#1C1917] tracking-tight">
              PNC UNIQUE LTD
            </div>
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
              Contractor Induction Portal
            </div>
          </div>
          <Link
            to="/"
            className="ml-auto inline-flex items-center gap-1 text-sm text-[#57534E] hover:text-[#1C1917]"
          >
            <ArrowLeft className="h-4 w-4" /> Back to portal
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            {subtitle || "Corporate"}
          </div>
          <h1 className="font-heading text-3xl sm:text-4xl tracking-tight text-[#1C1917] mt-1">
            {title}
          </h1>
          <div className="prose prose-neutral max-w-none mt-6 text-[15px] leading-relaxed text-[#1C1917]">
            {children}
          </div>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
