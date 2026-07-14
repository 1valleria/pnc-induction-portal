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
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">General enquiries</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]">
            <a href="mailto:info@pncunique.com" className="hover:underline">info@pncunique.com</a>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <Mail className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Admin &amp; HR</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]">
            <a href="mailto:admin@pncunique.com" className="hover:underline">admin@pncunique.com</a>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <Phone className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Telephone</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]">
            <a href="tel:+443330905024" className="hover:underline">0333 090 5024</a>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5">
          <div className="flex items-center gap-2 text-[#166534]">
            <Building2 className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Registered company</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917]">
            PNC UNIQUE LTD<br />
            <span className="text-[#57534E]">Registered in England and Wales</span>
          </div>
        </div>
        <div className="rounded-xl border border-[#E7E5E4] bg-white p-5 sm:col-span-2">
          <div className="flex items-center gap-2 text-[#166534]">
            <MapPin className="h-4 w-4" />
            <div className="text-[11px] uppercase tracking-[0.18em] font-semibold">Registered office</div>
          </div>
          <div className="mt-2 text-sm text-[#1C1917] leading-relaxed">
            <address className="not-italic">
              Headlands House<br />
              1 Kings Court<br />
              Kettering Parkway<br />
              Kettering<br />
              Northamptonshire<br />
              NN15 6WJ
            </address>
          </div>
        </div>
      </div>

      <h2 className="mt-8">Security concerns</h2>
      <p>
        If you have received a suspicious email that claims to be from
        PNC UNIQUE LTD, please do <strong>not</strong> click any links.
        Forward the message to{" "}
        <a href="mailto:admin@pncunique.com">admin@pncunique.com</a>
        {" "}and delete the original.
      </p>
    </LegalShell>
  );
}
