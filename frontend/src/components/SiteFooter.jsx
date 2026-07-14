import React from "react";
import { Link } from "react-router-dom";
import { BrandWordmark } from "@/components/BrandMark";

/**
 * Site-wide footer. Corporate identity is rendered from the values below —
 * see /app/memory/PRD.md for the source of truth.
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
            <div>Registered in England and Wales</div>
            <div>
              Unit 1, Headlands House<br />
              1 Kings Court, Kettering<br />
              NN15 6WJ
            </div>
            <div className="pt-1">
              <a href="mailto:info@pncunique.com" className="hover:text-[#1C1917] hover:underline">
                info@pncunique.com
              </a>
            </div>
            <div>
              <a href="tel:+443330905024" className="hover:text-[#1C1917] hover:underline">
                0333 090 5024
              </a>
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
