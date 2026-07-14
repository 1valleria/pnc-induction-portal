import React from "react";
import { Link } from "react-router-dom";
import { BrandWordmark } from "@/components/BrandMark";

/**
 * Site-wide footer. All corporate identity fields are rendered as clearly
 * marked placeholders so the operator can populate them before go-live.
 * The `data-placeholder` attribute lets us grep for pending items.
 */
export default function SiteFooter() {
  return (
    <footer
      role="contentinfo"
      className="border-t border-[#E7E5E4] bg-white/70 backdrop-blur mt-10"
      data-testid="site-footer"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 sm:grid-cols-3 gap-6 text-[13px] text-[#57534E]">
        <div>
          <BrandWordmark width={170} className="mb-2" />
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Contractor Induction Portal
          </div>
          <div className="mt-3 space-y-1 leading-relaxed">
            <div>
              Registered in England and Wales
            </div>
            <div data-placeholder="company-number">
              Company Number: <span className="italic text-[#78716C]">[to be confirmed]</span>
            </div>
            <div data-placeholder="registered-address">
              Registered Office: <span className="italic text-[#78716C]">[to be confirmed]</span>
            </div>
            <div data-placeholder="corporate-email">
              Corporate contact: <span className="italic text-[#78716C]">[to be confirmed]</span>
            </div>
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            About
          </div>
          <ul className="mt-3 space-y-1.5">
            <li><Link to="/about" className="hover:text-[#1C1917] hover:underline">About PNC UNIQUE LTD</Link></li>
            <li><Link to="/contact" className="hover:text-[#1C1917] hover:underline">Contact HR</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Legal
          </div>
          <ul className="mt-3 space-y-1.5">
            <li><Link to="/legal/privacy" className="hover:text-[#1C1917] hover:underline">Privacy Notice</Link></li>
            <li><Link to="/legal/terms" className="hover:text-[#1C1917] hover:underline">Terms &amp; Conditions</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-[#E7E5E4] bg-[#FAFAF9] py-3 text-center text-[11px] text-[#78716C]">
        &copy; {new Date().getFullYear()} PNC UNIQUE LTD. All rights reserved.
      </div>
    </footer>
  );
}
