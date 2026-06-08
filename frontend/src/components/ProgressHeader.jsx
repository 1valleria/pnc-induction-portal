import React from "react";
import { WIZARD } from "@/constants/testIds";
import { Save } from "lucide-react";

const STEP_TITLES = [
  "Personal Information",
  "Medical History & HAVS",
  "Digital Signature & Submit",
];

export const ProgressHeader = ({ step, savedAt }) => {
  const total = 3;
  const pct = ((step + 1) / total) * 100;
  return (
    <div className="sticky top-0 z-50 bg-white/85 backdrop-blur-xl border-b border-[#E7E5E4]">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 pt-4 pb-3">
        <div className="flex items-center justify-between mb-2">
          <div>
            <div
              className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#57534E]"
              data-testid={WIZARD.progressLabel}
            >
              Section {step + 1} of {total}
            </div>
            <h1 className="font-heading text-xl sm:text-2xl text-[#1C1917] tracking-tight">
              {STEP_TITLES[step]}
            </h1>
          </div>
          {savedAt && (
            <div
              className="hidden sm:flex items-center gap-1.5 text-xs text-[#166534] bg-[#F0FDF4] border border-[#BBF7D0] rounded-full px-3 py-1.5"
              data-testid={WIZARD.savedBadge}
            >
              <Save className="h-3.5 w-3.5" strokeWidth={2.2} />
              Progress saved
            </div>
          )}
        </div>
        <div className="h-1 w-full bg-[#E7E5E4] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#166534] transition-all duration-500 ease-out rounded-full"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default ProgressHeader;
