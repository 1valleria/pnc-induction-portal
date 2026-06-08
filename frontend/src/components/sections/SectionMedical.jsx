import React from "react";
import { Field, TextArea } from "@/components/Field";
import { YesNoToggle } from "@/components/YesNoToggle";
import { MEDICAL_QUESTIONS, HAVS_QUESTIONS } from "@/lib/constants";

const QuestionRow = ({ qKey, label, value, onChange, group }) => (
  <div className="flex flex-col gap-2 py-4 border-b border-[#F5F5F4] last:border-b-0">
    <div className="text-sm sm:text-base text-[#1C1917] leading-snug">{label}</div>
    <YesNoToggle
      name={`${group}-${qKey}`}
      value={value}
      onChange={onChange}
    />
  </div>
);

export const SectionMedical = ({ medical, updateMedical, havs, updateHavs, errors = {} }) => {
  return (
    <div className="space-y-10">
      <section>
        <header className="mb-3">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Medical History
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Please answer honestly. This is confidential.
          </h2>
        </header>
        <div className="rounded-2xl bg-white border border-[#E7E5E4] p-4 sm:p-5">
          {MEDICAL_QUESTIONS.map((q) => (
            <QuestionRow
              key={q.key}
              qKey={q.key}
              label={q.label}
              value={medical[q.key]}
              onChange={(v) => updateMedical({ [q.key]: v })}
              group="med"
            />
          ))}
        </div>
        {errors.medical_all && (
          <p className="text-xs text-[#EF4444] mt-2">{errors.medical_all}</p>
        )}

        <div className="mt-5 space-y-4">
          <Field label="If you answered Yes to any of the above, please provide details">
            <TextArea
              data-testid="medical-yes-details"
              value={medical.if_yes_details || ""}
              onChange={(e) => updateMedical({ if_yes_details: e.target.value })}
              placeholder="Provide brief details for each Yes answer..."
            />
          </Field>
          <Field label="Medication or disability details">
            <TextArea
              data-testid="medical-medication-details"
              value={medical.medication_disability_details || ""}
              onChange={(e) => updateMedical({ medication_disability_details: e.target.value })}
              placeholder="List any prescribed medication and any disability we should be aware of..."
            />
          </Field>
        </div>
      </section>

      <section>
        <header className="mb-3">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            HAVS Questionnaire
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Hand-arm vibration screening
          </h2>
        </header>
        <div className="rounded-2xl bg-white border border-[#E7E5E4] p-4 sm:p-5">
          {HAVS_QUESTIONS.map((q) => (
            <QuestionRow
              key={q.key}
              qKey={q.key}
              label={q.label}
              value={havs[q.key]}
              onChange={(v) => updateHavs({ [q.key]: v })}
              group="havs"
            />
          ))}
        </div>
        {errors.havs_all && (
          <p className="text-xs text-[#EF4444] mt-2">{errors.havs_all}</p>
        )}
      </section>
    </div>
  );
};

export default SectionMedical;
