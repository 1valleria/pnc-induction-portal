import React from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { SITE_RULES } from "@/data/complianceContent";

const formatTime = (iso) => {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return null;
  }
};

export const SectionSiteRules = ({ siteRulesAck, onAcknowledge, errors }) => {
  const isAcknowledged = Boolean(siteRulesAck);
  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-[#FEF3C7] border border-[#FDE68A] p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-[#92400E] flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="font-heading text-lg sm:text-xl text-[#78350F] tracking-tight">
              Site Rules
            </h2>
            <p className="text-sm text-[#1C1917] mt-1">
              Please read the following site rules carefully. You must press
              <strong> Compliant</strong> at the bottom to confirm before you can continue.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-[#E7E5E4] bg-white shadow-sm p-4 sm:p-6">
        <ul className="space-y-3" data-testid="site-rules-list">
          {SITE_RULES.map((rule, i) => (
            <li key={i} className="flex gap-3 text-sm text-[#1C1917] leading-relaxed">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#FAFAF9] border border-[#E7E5E4] text-[11px] font-semibold text-[#57534E] flex-shrink-0">
                {i + 1}
              </span>
              <span className="flex-1 pt-0.5">{rule}</span>
            </li>
          ))}
        </ul>

        <div className="mt-6 pt-5 border-t border-[#F5F5F4] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="text-sm text-[#57534E]">
            {isAcknowledged
              ? `Site Rules acknowledged · ${formatTime(siteRulesAck)}`
              : "I have read and understood the Site Rules."}
          </div>
          <button
            type="button"
            onClick={onAcknowledge}
            disabled={isAcknowledged}
            data-testid="site-rules-compliant-btn"
            className={`text-sm font-medium px-4 py-2.5 rounded-lg inline-flex items-center justify-center gap-1.5 transition-colors ${
              isAcknowledged
                ? "bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0] cursor-default"
                : "bg-[#166534] text-white hover:bg-[#14532D] shadow-sm"
            }`}
          >
            <CheckCircle2 className="h-4 w-4" />
            {isAcknowledged ? "Compliant" : "Compliant – I have read & understood"}
          </button>
        </div>
      </div>

      {errors?.site_rules && (
        <div className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C] text-sm p-3" data-testid="site-rules-error">
          {errors.site_rules}
        </div>
      )}
    </div>
  );
};
