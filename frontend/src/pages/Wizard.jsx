import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, CheckCircle2, Save } from "lucide-react";
import { uploadFile, uploadDataUrl, buildStorageFolderPath } from "@/lib/upload";
import { loadProgress, saveProgress, clearProgress } from "@/lib/autosave";
import { ProgressHeader } from "@/components/ProgressHeader";
import { SectionPersonal } from "@/components/sections/SectionPersonal";
import { SectionMedical } from "@/components/sections/SectionMedical";
import { SectionHealthSafety } from "@/components/sections/SectionHealthSafety";
import { SectionSiteRules } from "@/components/sections/SectionSiteRules";
import { SectionSignature } from "@/components/sections/SectionSignature";
import { MEDICAL_QUESTIONS, HAVS_QUESTIONS } from "@/lib/constants";
import { HEALTH_SAFETY_KEYS } from "@/data/complianceContent";
import { WIZARD } from "@/constants/testIds";
import { toast } from "sonner";

const EMPTY_STATE = {
  // section 1
  full_name: "",
  dob: "",
  telephone: "",
  email: "",
  address1: "",
  postcode: "",
  ni_number: "",
  emergency_name: "",
  emergency_phone: "",
  emergency_relationship: "",
  right_to_work_share_code: "",
  dvla_check: null,
  company_name: "",
  bank_account: "",
  sort_code: "",
  utr: "",
  vat_number: "",
  insurance_option: null,
  // section 3
  digital_signature_name: "",
  signature_image_data_url: null,
};

const EMPTY_MEDICAL = {
  if_yes_details: "",
  medication_disability_details: "",
};
const EMPTY_HAVS = {};
const EMPTY_HS_ACK = {}; // {section_key: ISO timestamp}
const TOTAL_STEPS = 5;
const LAST_STEP = TOTAL_STEPS - 1;

export default function Wizard() {
  const navigate = useNavigate();

  const session = useMemo(() => {
    try {
      return JSON.parse(sessionStorage.getItem("pnc_session_v1") || "null");
    } catch {
      return null;
    }
  }, []);

  // Hydrate state from localStorage synchronously to avoid set-state in effect
  const initial = useMemo(() => {
    const saved = loadProgress() || {};
    return {
      step: typeof saved.step === "number" ? saved.step : 0,
      data: {
        ...EMPTY_STATE,
        ...(saved.data || {}),
        email: saved.data?.email || session?.invitedEmail || "",
      },
      medical: { ...EMPTY_MEDICAL, ...(saved.medical || {}) },
      havs: { ...EMPTY_HAVS, ...(saved.havs || {}) },
      hsAck: { ...EMPTY_HS_ACK, ...(saved.hsAck || {}) },
      siteRulesAck: saved.siteRulesAck || null,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [step, setStep] = useState(initial.step);
  const [data, setData] = useState(initial.data);
  const [medical, setMedical] = useState(initial.medical);
  const [havs, setHavs] = useState(initial.havs);
  const [hsAck, setHsAck] = useState(initial.hsAck);
  const [siteRulesAck, setSiteRulesAck] = useState(initial.siteRulesAck);
  const [files, setFiles] = useState({});
  const [errors, setErrors] = useState({});
  const [savedAt, setSavedAt] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const interactedRef = useRef(false);

  useEffect(() => {
    if (!session) {
      navigate("/", { replace: true });
    }
  }, [session, navigate]);

  // Auto-save on changes (only after the user has actually interacted)
  useEffect(() => {
    if (!interactedRef.current) return;
    const t = setTimeout(() => {
      saveProgress({ data, medical, havs, hsAck, siteRulesAck, step });
      setSavedAt(Date.now());
    }, 400);
    return () => clearTimeout(t);
  }, [data, medical, havs, hsAck, siteRulesAck, step]);

  const update = (patch) => {
    interactedRef.current = true;
    setData((d) => ({ ...d, ...patch }));
  };
  const updateMedical = (patch) => {
    interactedRef.current = true;
    setMedical((m) => ({ ...m, ...patch }));
  };
  const updateHavs = (patch) => {
    interactedRef.current = true;
    setHavs((h) => ({ ...h, ...patch }));
  };
  const acknowledgeHealthSafety = (sectionKey) => {
    interactedRef.current = true;
    setHsAck((prev) => (prev[sectionKey] ? prev : { ...prev, [sectionKey]: new Date().toISOString() }));
  };
  const acknowledgeSiteRules = () => {
    interactedRef.current = true;
    setSiteRulesAck((cur) => cur || new Date().toISOString());
  };
  const setFile = (key, f) => {
    interactedRef.current = true;
    setFiles((prev) => ({ ...prev, [key]: f }));
  };

  const validateStep = (s) => {
    const e = {};
    if (s === 0) {
      [
        "full_name",
        "dob",
        "telephone",
        "email",
        "address1",
        "postcode",
        "ni_number",
        "emergency_name",
        "emergency_phone",
        "emergency_relationship",
        "right_to_work_share_code",
        "company_name",
        "bank_account",
        "sort_code",
        "utr",
      ].forEach((k) => {
        if (!data[k] || !String(data[k]).trim()) e[k] = "Required";
      });
      if (!data.dvla_check) e.dvla_check = "Please select Yes or No";
      if (!data.insurance_option) e.insurance_option = "Please choose an option";
      if (data.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email))
        e.email = "Enter a valid email";
      if (!files.passport) e.passport = "Required";
      if (!files.driving_licence) e.driving_licence = "Required";
      if (!files.bank_proof) e.bank_proof = "Required";
      if (data.insurance_option === "own" && !files.insurance_certificate)
        e.insurance_certificate = "Required";
      // Invoice service question
      if (data.invoice_service_requested === undefined || data.invoice_service_requested === null) {
        e.invoice_service_requested = "Please choose Yes or No";
      } else if (data.invoice_service_requested === true) {
        const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const e1 = (data.invoice_email_1 || "").trim().toLowerCase();
        const e2 = (data.invoice_email_2 || "").trim().toLowerCase();
        if (!e1) {
          e.invoice_email_1 = "At least one invoice email is required";
        } else if (!emailRe.test(e1)) {
          e.invoice_email_1 = "Enter a valid email";
        }
        if (e2 && !emailRe.test(e2)) {
          e.invoice_email_2 = "Enter a valid email";
        }
        if (e1 && e2 && e1 === e2) {
          e.invoice_email_2 = "This email is the same as Email 1";
        }
      }
    }
    if (s === 1) {
      const missingMed = MEDICAL_QUESTIONS.find((q) => !medical[q.key]);
      if (missingMed) e.medical_all = "Please answer every medical question.";
      const missingHavs = HAVS_QUESTIONS.find((q) => !havs[q.key]);
      if (missingHavs) e.havs_all = "Please answer every HAVS question.";
    }
    if (s === 2) {
      const missing = HEALTH_SAFETY_KEYS.filter((k) => !hsAck[k]).length;
      if (missing > 0) {
        e.health_safety_all = `Please mark all ${HEALTH_SAFETY_KEYS.length} Tool Box Talks as Compliant before continuing (${missing} remaining).`;
      }
    }
    if (s === 3) {
      if (!siteRulesAck) {
        e.site_rules = "Please press Compliant on the Site Rules section before continuing.";
      }
    }
    if (s === 4) {
      if (!data.digital_signature_name || data.digital_signature_name.trim().length < 2)
        e.digital_signature_name = "Please type your full legal name";
      if (!data.signature_image_data_url)
        e.signature_image_data_url = "Please draw your signature above";
    }
    return e;
  };

  const handleNext = () => {
    const e = validateStep(step);
    setErrors(e);
    if (Object.keys(e).length === 0) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      setStep((s) => Math.min(LAST_STEP, s + 1));
    } else {
      if (e.passport || e.driving_licence || e.bank_proof || e.insurance_certificate) {
        toast.error("Please upload all required documents.");
      } else if (e.health_safety_all) {
        toast.error("Please mark every Tool Box Talk as Compliant.");
      } else if (e.site_rules) {
        toast.error("Please press Compliant on the Site Rules.");
      } else {
        toast.error("Please complete the highlighted fields.");
      }
    }
  };

  const handlePrev = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    setStep((s) => Math.max(0, s - 1));
  };

  const handleSubmit = async () => {
    // Final guard — every previous step's validation must still pass.
    const errs = {};
    Object.assign(errs, validateStep(2), validateStep(3), validateStep(4));
    setErrors(errs);
    if (Object.keys(errs).length > 0) {
      if (errs.health_safety_all || errs.site_rules) {
        toast.error("Please confirm Health & Safety and Site Rules before submitting.");
      } else {
        toast.error("Please complete the signature section.");
      }
      return;
    }
    setSubmitError(null);
    setSubmitting(true);
    const apiBase = process.env.REACT_APP_BACKEND_URL || "";

    try {
      const submittedAt = new Date().toISOString();

      // 1. Upload all files directly to Firebase Storage (browser → Storage only).
      // The Storage folder path needs an id; we use the access_code_id so it's
      // unique per inductee even before the backend assigns an employee_id.
      // The backend will resolve / persist this same path on employee_documents.
      const storageFolderPath = buildStorageFolderPath(data.full_name, session.accessCodeId);
      const uploads = {};
      if (files.passport)
        uploads.passport = await uploadFile(storageFolderPath, "passport", files.passport);
      if (files.driving_licence)
        uploads.driving_licence = await uploadFile(storageFolderPath, "driving_licence", files.driving_licence);
      if (files.bank_proof)
        uploads.bank_proof = await uploadFile(storageFolderPath, "bank_proof", files.bank_proof);
      if (files.insurance_certificate)
        uploads.insurance_certificate = await uploadFile(storageFolderPath, "insurance", files.insurance_certificate);

      // 2. Upload signature
      const signatureRes = await uploadDataUrl(
        storageFolderPath,
        "signature",
        data.signature_image_data_url,
        `signature_${session.accessCodeId}.png`
      );
      uploads.signature = signatureRes;

      // 3. Submit everything via the consolidated backend endpoint.
      // Backend writes employees / medical_history / havs_questionnaires /
      // employee_documents / employee_summary, marks the access code used,
      // and generates the PDF — all via the Firebase Admin SDK.
      const submitUrl = `${apiBase}/api/induction/submit`;
      const resp = await fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          access_code_id: session.accessCodeId,
          access_code: session.accessCode,
          invited_email: session.invitedEmail,
          full_name: data.full_name,
          dob: data.dob,
          telephone: data.telephone,
          email: data.email,
          address1: data.address1,
          postcode: data.postcode,
          ni_number: data.ni_number,
          emergency_name: data.emergency_name,
          emergency_phone: data.emergency_phone,
          emergency_relationship: data.emergency_relationship,
          right_to_work_share_code: data.right_to_work_share_code,
          dvla_check: data.dvla_check,
          company_name: data.company_name,
          bank_account: data.bank_account,
          sort_code: data.sort_code,
          utr: data.utr,
          vat_number: data.vat_number || null,
          insurance_option: data.insurance_option,
          invoice_service_requested: Boolean(data.invoice_service_requested),
          invoice_email_1: data.invoice_service_requested
            ? (data.invoice_email_1 || "").trim().toLowerCase() || null
            : null,
          invoice_email_2: data.invoice_service_requested
            ? (data.invoice_email_2 || "").trim().toLowerCase() || null
            : null,
          digital_signature_name: data.digital_signature_name,
          medical: {
            ...MEDICAL_QUESTIONS.reduce((acc, q) => ({ ...acc, [q.key]: medical[q.key] }), {}),
            if_yes_details: medical.if_yes_details || "",
            medication_disability_details: medical.medication_disability_details || "",
          },
          havs: HAVS_QUESTIONS.reduce((acc, q) => ({ ...acc, [q.key]: havs[q.key] }), {}),
          health_safety_sections: hsAck,
          health_safety_acknowledged: HEALTH_SAFETY_KEYS.every((k) => Boolean(hsAck[k])),
          health_safety_completed_at:
            HEALTH_SAFETY_KEYS.every((k) => Boolean(hsAck[k]))
              ? Object.values(hsAck).sort().slice(-1)[0]
              : null,
          site_rules_acknowledged: Boolean(siteRulesAck),
          site_rules_completed_at: siteRulesAck || null,
          files: uploads,
          storage_folder_path: storageFolderPath,
          submitted_at: submittedAt,
        }),
      });

      if (!resp.ok) {
        let detail = `HTTP ${resp.status}`;
        try {
          const body = await resp.json();
          if (body && body.detail) detail = body.detail;
        } catch (bodyParseErr) {
          console.debug("[Wizard] response body not JSON", bodyParseErr);
        }
        throw new Error(detail);
      }

      const body = await resp.json();

      clearProgress();
      sessionStorage.removeItem("pnc_session_v1");
      navigate(`/success?id=${body.employee_id}`, { replace: true });
    } catch (err) {
      const msg = err && err.message ? err.message : "Unknown error";
      setSubmitError(
        `Something went wrong submitting your induction: ${msg}. Your progress is still saved — please try again, or contact PNC UNIQUE LTD HR if the problem continues.`
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF9] pb-32">
      <ProgressHeader step={step} savedAt={savedAt} />

      <div className="max-w-2xl mx-auto px-4 sm:px-6 pt-6">
        {savedAt && (
          <div
            data-testid="wizard-saved-badge-mobile"
            className="sm:hidden mb-4 inline-flex items-center gap-1.5 text-xs text-[#166534] bg-[#F0FDF4] border border-[#BBF7D0] rounded-full px-3 py-1.5"
          >
            <Save className="h-3.5 w-3.5" /> Progress saved
          </div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
          >
            {step === 0 && (
              <SectionPersonal
                data={data}
                update={update}
                files={files}
                setFile={setFile}
                errors={errors}
              />
            )}
            {step === 1 && (
              <SectionMedical
                medical={medical}
                updateMedical={updateMedical}
                havs={havs}
                updateHavs={updateHavs}
                errors={errors}
              />
            )}
            {step === 2 && (
              <SectionHealthSafety
                hsAck={hsAck}
                onAcknowledge={acknowledgeHealthSafety}
                errors={errors}
              />
            )}
            {step === 3 && (
              <SectionSiteRules
                siteRulesAck={siteRulesAck}
                onAcknowledge={acknowledgeSiteRules}
                errors={errors}
              />
            )}
            {step === 4 && (
              <SectionSignature data={data} update={update} errors={errors} />
            )}
          </motion.div>
        </AnimatePresence>

        {submitError && (
          <div className="mt-5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C] text-sm p-3">
            {submitError}
          </div>
        )}
      </div>

      {/* Sticky footer with nav */}
      <div className="fixed bottom-0 inset-x-0 bg-white/95 backdrop-blur-xl border-t border-[#E7E5E4] z-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-3">
          {step > 0 ? (
            <button
              type="button"
              onClick={handlePrev}
              disabled={submitting}
              data-testid={WIZARD.prevBtn}
              className="h-12 sm:h-14 px-4 sm:px-5 rounded-xl border border-[#E7E5E4] bg-white text-[#1C1917] font-medium inline-flex items-center gap-1.5 hover:bg-[#FAFAF9] transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </button>
          ) : (
            <div className="flex-1" />
          )}
          {step < LAST_STEP ? (
            <button
              type="button"
              onClick={handleNext}
              data-testid={WIZARD.nextBtn}
              className="flex-1 h-12 sm:h-14 rounded-xl bg-[#166534] hover:bg-[#14532D] text-white font-medium inline-flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              Continue
              <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              data-testid={WIZARD.submitBtn}
              className="flex-1 h-12 sm:h-14 rounded-xl bg-[#166534] hover:bg-[#14532D] disabled:opacity-60 text-white font-medium inline-flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              {submitting ? (
                "Submitting..."
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" /> Submit Induction
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
