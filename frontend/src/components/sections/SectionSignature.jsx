import React from "react";
import { Field, TextInput } from "@/components/Field";
import { SignaturePad } from "@/components/SignaturePad";
import { DECLARATION_TEXT } from "@/lib/constants";

export const SectionSignature = ({ data, update, errors = {} }) => {
  return (
    <div className="space-y-8">
      <section>
        <header className="mb-3">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Declaration
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Please read carefully before signing
          </h2>
        </header>
        <div className="rounded-2xl bg-white border border-[#E7E5E4] p-4 sm:p-5 text-sm text-[#1C1917] leading-relaxed whitespace-pre-wrap">
          {DECLARATION_TEXT}
        </div>
      </section>

      <section className="space-y-4">
        <Field label="Digital Signature — Full Legal Name" required error={errors.digital_signature_name}>
          <TextInput
            data-testid="signature-name"
            value={data.digital_signature_name || ""}
            onChange={(e) => update({ digital_signature_name: e.target.value })}
            placeholder="Type your full legal name"
          />
        </Field>

        <Field label="Drawn Signature" required error={errors.signature_image_data_url}>
          <SignaturePad
            value={data.signature_image_data_url}
            onChange={(v) => update({ signature_image_data_url: v })}
          />
        </Field>

        <div className="rounded-xl bg-[#FAFAF9] border border-[#E7E5E4] p-3 text-xs text-[#57534E]">
          By tapping <span className="font-semibold text-[#1C1917]">Submit Induction</span> you
          confirm the information above is accurate. Your submission date and time will be
          recorded automatically.
        </div>
      </section>
    </div>
  );
};

export default SectionSignature;
