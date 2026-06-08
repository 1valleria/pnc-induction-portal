import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, CheckCircle2, Save } from "lucide-react";
import {
  collection,
  doc,
  addDoc,
  setDoc,
  updateDoc,
  serverTimestamp,
} from "firebase/firestore";
import { db } from "@/lib/firebase";
import { uploadFile, uploadDataUrl, buildStorageFolderPath } from "@/lib/upload";
import { loadProgress, saveProgress, clearProgress } from "@/lib/autosave";
import { ProgressHeader } from "@/components/ProgressHeader";
import { SectionPersonal } from "@/components/sections/SectionPersonal";
import { SectionMedical } from "@/components/sections/SectionMedical";
import { SectionSignature } from "@/components/sections/SectionSignature";
import { MEDICAL_QUESTIONS, HAVS_QUESTIONS } from "@/lib/constants";
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
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [step, setStep] = useState(initial.step);
  const [data, setData] = useState(initial.data);
  const [medical, setMedical] = useState(initial.medical);
  const [havs, setHavs] = useState(initial.havs);
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
      saveProgress({ data, medical, havs, step });
      setSavedAt(Date.now());
    }, 400);
    return () => clearTimeout(t);
  }, [data, medical, havs, step]);

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
    }
    if (s === 1) {
      const missingMed = MEDICAL_QUESTIONS.find((q) => !medical[q.key]);
      if (missingMed) e.medical_all = "Please answer every medical question.";
      const missingHavs = HAVS_QUESTIONS.find((q) => !havs[q.key]);
      if (missingHavs) e.havs_all = "Please answer every HAVS question.";
    }
    if (s === 2) {
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
      setStep((s) => Math.min(2, s + 1));
    } else {
      // surface first missing file as toast
      if (e.passport || e.driving_licence || e.bank_proof || e.insurance_certificate) {
        toast.error("Please upload all required documents.");
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
    const e = validateStep(2);
    setErrors(e);
    if (Object.keys(e).length > 0) {
      toast.error("Please complete the signature section.");
      return;
    }
    setSubmitError(null);
    setSubmitting(true);
    try {
      const submittedAt = new Date().toISOString();
      // 1. Create employees doc
      const employeesCol = collection(db, "employees");
      const employeeRef = await addDoc(employeesCol, {
        full_name: data.full_name,
        dob: data.dob,
        telephone: data.telephone,
        email: data.email,
        invited_email: session.invitedEmail,
        address1: data.address1,
        postcode: data.postcode,
        ni_number: data.ni_number,
        emergency_contact: {
          name: data.emergency_name,
          phone: data.emergency_phone,
          relationship: data.emergency_relationship,
        },
        right_to_work_share_code: data.right_to_work_share_code,
        dvla_check: data.dvla_check,
        business: {
          company_name: data.company_name,
          bank_account: data.bank_account,
          sort_code: data.sort_code,
          utr: data.utr,
          vat_number: data.vat_number || null,
        },
        insurance_option: data.insurance_option,
        digital_signature_name: data.digital_signature_name,
        access_code: session.accessCode,
        access_code_id: session.accessCodeId,
        submitted_at: submittedAt,
        submitted_at_server: serverTimestamp(),
        status: "submitted",
      });
      const employeeId = employeeRef.id;

      // Build the human-friendly Storage folder path (only used for new submissions).
      const storageFolderPath = buildStorageFolderPath(data.full_name, employeeId);

      // 2. medical_history
      await addDoc(collection(db, "medical_history"), {
        employee_id: employeeId,
        ...MEDICAL_QUESTIONS.reduce((acc, q) => ({ ...acc, [q.key]: medical[q.key] }), {}),
        if_yes_details: medical.if_yes_details || "",
        medication_disability_details: medical.medication_disability_details || "",
        submitted_at: submittedAt,
        submitted_at_server: serverTimestamp(),
      });

      // 3. havs_questionnaires
      await addDoc(collection(db, "havs_questionnaires"), {
        employee_id: employeeId,
        ...HAVS_QUESTIONS.reduce((acc, q) => ({ ...acc, [q.key]: havs[q.key] }), {}),
        submitted_at: submittedAt,
        submitted_at_server: serverTimestamp(),
      });

      // 4. Uploads — using human-friendly folder path
      const uploads = {};
      if (files.passport)
        uploads.passport = await uploadFile(storageFolderPath, "passport", files.passport);
      if (files.driving_licence)
        uploads.driving_licence = await uploadFile(storageFolderPath, "driving_licence", files.driving_licence);
      if (files.bank_proof)
        uploads.bank_proof = await uploadFile(storageFolderPath, "bank_proof", files.bank_proof);
      if (files.insurance_certificate)
        uploads.insurance_certificate = await uploadFile(storageFolderPath, "insurance", files.insurance_certificate);

      // 5. Signature image
      const signatureRes = await uploadDataUrl(
        storageFolderPath,
        "signature",
        data.signature_image_data_url,
        `signature_${employeeId}.png`
      );
      uploads.signature = signatureRes;

      // 6. employee_documents doc
      await addDoc(collection(db, "employee_documents"), {
        employee_id: employeeId,
        storage_folder_path: storageFolderPath,
        files: uploads,
        pdf_url: null, // generated server-side later
        submitted_at: submittedAt,
        submitted_at_server: serverTimestamp(),
      });

      // 7. Mark access code as used
      try {
        await updateDoc(doc(db, "access_codes", session.accessCodeId), {
          used: true,
          used_at: serverTimestamp(),
          employee_id: employeeId,
        });
      } catch (err) {
        console.warn("Failed to mark code used", err);
      }

      // 8. Trigger server-side PDF generation + employee_summary (best-effort,
      //    does not block the success screen if the backend is slow/unreachable)
      const apiBase = process.env.REACT_APP_BACKEND_URL || "";
      try {
        const resp = await fetch(`${apiBase}/api/induction/finalize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ employee_id: employeeId }),
        });
        if (!resp.ok) {
          console.warn("PDF finalize returned", resp.status);
        }
      } catch (err) {
        console.warn("PDF finalize failed (will be retried by HR)", err);
      }

      clearProgress();
      sessionStorage.removeItem("pnc_session_v1");
      navigate(`/success?id=${employeeId}`, { replace: true });
    } catch (err) {
      console.error(err);
      setSubmitError(
        "Something went wrong submitting your induction. Your progress is still saved — please try again, or contact PNC HR if the problem continues."
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
          {step < 2 ? (
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
