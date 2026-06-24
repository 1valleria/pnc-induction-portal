import React from "react";
import { Field, TextInput } from "@/components/Field";
import { FileDropzone } from "@/components/FileDropzone";
import { YesNoToggle } from "@/components/YesNoToggle";

const radioCard = (active) =>
  [
    "flex-1 cursor-pointer rounded-xl border p-4 transition-all",
    active
      ? "border-[#166534] bg-[#F0FDF4] ring-2 ring-[#166534]/20"
      : "border-[#E7E5E4] bg-white hover:bg-[#FAFAF9]",
  ].join(" ");

export const SectionPersonal = ({ data, update, files, setFile, errors = {} }) => {
  return (
    <div className="space-y-10">
      {/* Personal */}
      <section className="space-y-5">
        <header>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Personal
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            About you
          </h2>
        </header>

        <Field label="Full Name" required error={errors.full_name}>
          <TextInput
            data-testid="field-full-name"
            value={data.full_name || ""}
            onChange={(e) => update({ full_name: e.target.value })}
            placeholder="As shown on your passport"
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Date of Birth" required error={errors.dob}>
            <TextInput
              data-testid="field-dob"
              type="date"
              value={data.dob || ""}
              onChange={(e) => update({ dob: e.target.value })}
            />
          </Field>
          <Field label="Contact Telephone Number" required error={errors.telephone}>
            <TextInput
              data-testid="field-telephone"
              type="tel"
              inputMode="tel"
              value={data.telephone || ""}
              onChange={(e) => update({ telephone: e.target.value })}
              placeholder="e.g. 07700 900123"
            />
          </Field>
        </div>

        <Field label="Email Address" required error={errors.email}>
          <TextInput
            data-testid="field-email"
            type="email"
            inputMode="email"
            value={data.email || ""}
            onChange={(e) => update({ email: e.target.value })}
            placeholder="you@example.com"
          />
        </Field>

        <Field label="Address Line 1" required error={errors.address1}>
          <TextInput
            data-testid="field-address1"
            value={data.address1 || ""}
            onChange={(e) => update({ address1: e.target.value })}
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Postcode" required error={errors.postcode}>
            <TextInput
              data-testid="field-postcode"
              value={data.postcode || ""}
              onChange={(e) => update({ postcode: e.target.value.toUpperCase() })}
              placeholder="SW1A 1AA"
            />
          </Field>
          <Field label="National Insurance Number" required error={errors.ni_number}>
            <TextInput
              data-testid="field-ni"
              value={data.ni_number || ""}
              onChange={(e) => update({ ni_number: e.target.value.toUpperCase() })}
              placeholder="QQ123456C"
            />
          </Field>
        </div>
      </section>

      {/* Emergency */}
      <section className="space-y-5">
        <header>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Emergency Contact
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Who should we contact if needed?
          </h2>
        </header>

        <Field label="Emergency Contact Full Name" required error={errors.emergency_name}>
          <TextInput
            data-testid="field-emergency-name"
            value={data.emergency_name || ""}
            onChange={(e) => update({ emergency_name: e.target.value })}
          />
        </Field>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Emergency Contact Phone" required error={errors.emergency_phone}>
            <TextInput
              data-testid="field-emergency-phone"
              type="tel"
              value={data.emergency_phone || ""}
              onChange={(e) => update({ emergency_phone: e.target.value })}
            />
          </Field>
          <Field label="Relationship" required error={errors.emergency_relationship}>
            <TextInput
              data-testid="field-emergency-rel"
              value={data.emergency_relationship || ""}
              onChange={(e) => update({ emergency_relationship: e.target.value })}
              placeholder="e.g. Spouse, Parent"
            />
          </Field>
        </div>
      </section>

      {/* Right To Work + Documents */}
      <section className="space-y-5">
        <header>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Right to Work & Identity
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Verification documents
          </h2>
        </header>

        <Field label="Right To Work Share Code" required error={errors.right_to_work_share_code}>
          <TextInput
            data-testid="field-rtw"
            value={data.right_to_work_share_code || ""}
            onChange={(e) => update({ right_to_work_share_code: e.target.value.toUpperCase() })}
            placeholder="ABC 123 DEF"
          />
        </Field>

        <FileDropzone
          label="Upload Passport or National Identity Card"
          required
          value={files.passport}
          onChange={(f) => setFile("passport", f)}
          testId="upload-passport"
        />
        <FileDropzone
          label="Upload Driving Licence"
          required
          value={files.driving_licence}
          onChange={(f) => setFile("driving_licence", f)}
          testId="upload-driving-licence"
        />

        <Field label="DVLA Licence Check Approval" required error={errors.dvla_check}>
          <YesNoToggle
            name="dvla"
            value={data.dvla_check}
            onChange={(v) => update({ dvla_check: v })}
          />
        </Field>
      </section>

      {/* Business */}
      <section className="space-y-5">
        <header>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Business Details
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Your company information
          </h2>
        </header>

        <Field label="Company Name" required error={errors.company_name}>
          <TextInput
            data-testid="field-company-name"
            value={data.company_name || ""}
            onChange={(e) => update({ company_name: e.target.value })}
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Business Bank Account Number" required error={errors.bank_account}>
            <TextInput
              data-testid="field-bank-account"
              value={data.bank_account || ""}
              onChange={(e) => update({ bank_account: e.target.value.replace(/\D/g, "") })}
              inputMode="numeric"
              maxLength={8}
              placeholder="12345678"
            />
          </Field>
          <Field label="Business Sort Code" required error={errors.sort_code}>
            <TextInput
              data-testid="field-sort-code"
              value={data.sort_code || ""}
              onChange={(e) => update({ sort_code: e.target.value })}
              placeholder="12-34-56"
            />
          </Field>
        </div>

        <FileDropzone
          label="Upload Proof of Business Bank Account"
          required
          value={files.bank_proof}
          onChange={(f) => setFile("bank_proof", f)}
          testId="upload-bank-proof"
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Company UTR Number" required error={errors.utr}>
            <TextInput
              data-testid="field-utr"
              value={data.utr || ""}
              onChange={(e) => update({ utr: e.target.value })}
              placeholder="10 digits"
            />
          </Field>
          <Field label="VAT Registration Number" hint="Leave blank if not VAT registered">
            <TextInput
              data-testid="field-vat"
              value={data.vat_number || ""}
              onChange={(e) => update({ vat_number: e.target.value })}
              placeholder="GB123456789"
            />
          </Field>
        </div>
      </section>

      {/* Insurance */}
      <section className="space-y-5">
        <header>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Insurance
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Will you provide your own insurance, or be covered by PNC for £5/week?
          </h2>
        </header>

        <div className="flex flex-col sm:flex-row gap-3">
          <div
            className={radioCard(data.insurance_option === "own")}
            onClick={() => update({ insurance_option: "own" })}
            data-testid="insurance-own"
          >
            <div className="text-sm font-semibold text-[#1C1917]">My own insurance</div>
            <div className="text-xs text-[#57534E] mt-1">
              I will upload a valid certificate.
            </div>
          </div>
          <div
            className={radioCard(data.insurance_option === "pnc")}
            onClick={() => update({ insurance_option: "pnc" })}
            data-testid="insurance-pnc"
          >
            <div className="text-sm font-semibold text-[#1C1917]">PNC cover — £5/week</div>
            <div className="text-xs text-[#57534E] mt-1">
              I wish to be covered by the PNC policy.
            </div>
          </div>
        </div>
        {errors.insurance_option && (
          <p className="text-xs text-[#EF4444]">{errors.insurance_option}</p>
        )}

        {data.insurance_option === "own" && (
          <FileDropzone
            label="Upload Insurance Certificate"
            required
            value={files.insurance_certificate}
            onChange={(f) => setFile("insurance_certificate", f)}
            testId="upload-insurance"
          />
        )}
      </section>

      {/* Invoice service */}
      <section className="space-y-5">
        <header>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Weekly Invoicing Service
          </div>
          <h2 className="font-heading text-lg sm:text-xl text-[#1C1917] tracking-tight">
            Would you like PNC to create your weekly invoices for a £2 weekly charge?
          </h2>
        </header>

        <div className="flex flex-col sm:flex-row gap-3">
          <div
            className={radioCard(data.invoice_service_requested === true)}
            onClick={() => update({ invoice_service_requested: true })}
            data-testid="invoice-yes"
          >
            <div className="text-sm font-semibold text-[#1C1917]">Yes — £2/week</div>
            <div className="text-xs text-[#57534E] mt-1">
              PNC will prepare and send my weekly invoices.
            </div>
          </div>
          <div
            className={radioCard(data.invoice_service_requested === false)}
            onClick={() =>
              update({
                invoice_service_requested: false,
                invoice_email_1: "",
                invoice_email_2: "",
              })
            }
            data-testid="invoice-no"
          >
            <div className="text-sm font-semibold text-[#1C1917]">No</div>
            <div className="text-xs text-[#57534E] mt-1">
              I will produce my own invoices.
            </div>
          </div>
        </div>
        {errors.invoice_service_requested && (
          <p className="text-xs text-[#EF4444]">{errors.invoice_service_requested}</p>
        )}

        {data.invoice_service_requested === true && (
          <div className="space-y-4 rounded-xl border border-[#E7E5E4] bg-[#FAFAF9] p-4 sm:p-5">
            <div className="text-sm font-medium text-[#1C1917]">
              What email address(es) should we send the weekly invoices to?
            </div>
            <Field label="Invoice Email 1" required error={errors.invoice_email_1}>
              <TextInput
                data-testid="invoice-email-1"
                type="email"
                placeholder="invoices@example.com"
                value={data.invoice_email_1 || ""}
                onChange={(e) => update({ invoice_email_1: e.target.value })}
              />
            </Field>
            <Field label="Invoice Email 2 (optional)" error={errors.invoice_email_2}>
              <TextInput
                data-testid="invoice-email-2"
                type="email"
                placeholder="accounts@example.com"
                value={data.invoice_email_2 || ""}
                onChange={(e) => update({ invoice_email_2: e.target.value })}
              />
            </Field>
            <p className="text-xs text-[#57534E]">
              Up to 2 email addresses. We&apos;ll send your weekly invoice to all of them.
            </p>
          </div>
        )}
      </section>
    </div>
  );
};

export default SectionPersonal;
