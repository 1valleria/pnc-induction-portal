import React, { useState } from "react";
import { ChevronDown, CheckCircle2, ShieldCheck } from "lucide-react";
import { HEALTH_SAFETY_SECTIONS } from "@/data/complianceContent";

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

const AccordionCard = ({ section, index, acknowledgedAt, onAcknowledge }) => {
  const [open, setOpen] = useState(false);
  const isAcknowledged = Boolean(acknowledgedAt);
  return (
    <div
      className={`rounded-2xl border bg-white shadow-sm transition-colors ${
        isAcknowledged ? "border-[#BBF7D0]" : "border-[#E7E5E4]"
      }`}
      data-testid={`hs-card-${section.key}`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full px-4 sm:px-5 py-3.5 flex items-center gap-3 text-left"
        data-testid={`hs-card-toggle-${section.key}`}
        aria-expanded={open}
      >
        <span
          className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-[11px] font-semibold flex-shrink-0 ${
            isAcknowledged ? "bg-[#166534] text-white" : "bg-[#FAFAF9] text-[#57534E] border border-[#E7E5E4]"
          }`}
        >
          {isAcknowledged ? <CheckCircle2 className="w-4 h-4" /> : index + 1}
        </span>
        <span className="flex-1 min-w-0">
          <div className="text-sm sm:text-base font-medium text-[#1C1917] leading-snug">
            {section.title}
          </div>
          {isAcknowledged && (
            <div className="text-[11px] text-[#166534] mt-0.5">
              Compliant · {formatTime(acknowledgedAt)}
            </div>
          )}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-[#57534E] flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-4 sm:px-5 pb-4 border-t border-[#F5F5F4]">
          <div className="text-sm text-[#1C1917] leading-relaxed space-y-3 pt-3 max-h-72 overflow-y-auto pr-1">
            {section.body.map((para, i) => (
              <p key={`${section.key}-para-${i}`} className={para.startsWith("•") ? "pl-1" : ""}>{para}</p>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between gap-3 pt-3 border-t border-[#F5F5F4]">
            <div className="text-xs text-[#57534E]">
              {isAcknowledged ? "You have confirmed this section." : "Please read the section above, then mark it as compliant."}
            </div>
            <button
              type="button"
              onClick={() => onAcknowledge(section.key)}
              disabled={isAcknowledged}
              data-testid={`hs-card-compliant-${section.key}`}
              className={`text-xs sm:text-sm font-medium px-3 py-2 rounded-lg inline-flex items-center gap-1.5 transition-colors ${
                isAcknowledged
                  ? "bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0] cursor-default"
                  : "bg-[#166534] text-white hover:bg-[#14532D] shadow-sm"
              }`}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              {isAcknowledged ? "Compliant" : "Mark as Compliant"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export const SectionHealthSafety = ({ hsAck, onAcknowledge, errors }) => {
  const acknowledgedCount = HEALTH_SAFETY_SECTIONS.filter((s) => hsAck[s.key]).length;
  const total = HEALTH_SAFETY_SECTIONS.length;
  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-[#F0FDF4] border border-[#BBF7D0] p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 text-[#166534] flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="font-heading text-lg sm:text-xl text-[#14532D] tracking-tight">
              Tool Box Talks – Health & Safety
            </h2>
            <p className="text-sm text-[#1C1917] mt-1">
              Read each section below and press <strong>Mark as Compliant</strong> to confirm
              you have understood the information. You must acknowledge all {total} sections
              before you can continue.
            </p>
            <div className="mt-3 text-xs font-medium text-[#166534]" data-testid="hs-progress">
              {acknowledgedCount} of {total} sections acknowledged
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {HEALTH_SAFETY_SECTIONS.map((section, i) => (
          <AccordionCard
            key={section.key}
            section={section}
            index={i}
            acknowledgedAt={hsAck[section.key]}
            onAcknowledge={onAcknowledge}
          />
        ))}
      </div>

      {errors?.health_safety_all && (
        <div className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C] text-sm p-3" data-testid="hs-error">
          {errors.health_safety_all}
        </div>
      )}
    </div>
  );
};
