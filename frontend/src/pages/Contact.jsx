import React from "react";
import LegalShell from "@/components/LegalShell";
import { Mail, Building2, MapPin, Phone } from "lucide-react";

export default function Contact() {
  return (
    <LegalShell title="Contact PNC UNIQUE LTD" subtitle="Get in touch">
      <p>
        The fastest way to get help with your induction is to contact PNC
        UNIQUE LTD HR directly. All contact channels below are staffed during
        UK working hours. Please quote your access code (never share your full
        code by public channels — the last four characters are enough).
      </p>

      <div className="not-prose mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <Mail className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">HR email</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]" data-placeholder="hr-email">
            <em className="text-[#78716C]">[HR email to be confirmed]</em>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <Phone className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Telephone</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]" data-placeholder="hr-phone">
            <em className="text-[#78716C]">[HR phone to be confirmed]</em>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <Building2 className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Registered company</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]">
            PNC UNIQUE LTD
            <br />
            <span data-placeholder="company-number" className="text-[#78716C]">
              Company Number: <em>[to be confirmed]</em>
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <MapPin className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Registered office</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]" data-placeholder="registered-address">
            <em className="text-[#78716C]">[registered address to be confirmed]</em>
          </div>
        </div>
      </div>

      <h2 className="mt-8">Security concerns</h2>
      <p>
        If you have received a suspicious email that claims to be from
        PNC UNIQUE LTD, please do <strong>not</strong> click any links.
        Forward the message to <em data-placeholder="security-email">[security contact to be confirmed]</em>
        and delete the original.
      </p>
    </LegalShell>
  );
}
