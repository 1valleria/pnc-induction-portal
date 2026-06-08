import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { collection, query, where, getDocs, limit } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { GATE } from "@/constants/testIds";
import { TextInput, Field } from "@/components/Field";
import { Lock, ShieldCheck, ArrowRight } from "lucide-react";

export default function AccessGate() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email || !code) {
      setError("Please enter both email and access code.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    try {
      const normalisedCode = code.trim().toUpperCase();
      const normalisedEmail = email.trim().toLowerCase();
      const q = query(
        collection(db, "access_codes"),
        where("code", "==", normalisedCode),
        limit(1)
      );
      const snap = await getDocs(q);
      if (snap.empty) {
        setError("Access code not recognised. Please check the code from your invitation email.");
        setLoading(false);
        return;
      }
      const docSnap = snap.docs[0];
      const data = docSnap.data();
      if (data.used) {
        setError("This access code has already been used. Please contact PNC HR if you believe this is a mistake.");
        setLoading(false);
        return;
      }
      if (data.email && data.email.toLowerCase() !== normalisedEmail) {
        setError("This access code is registered to a different email address.");
        setLoading(false);
        return;
      }
      sessionStorage.setItem(
        "pnc_session_v1",
        JSON.stringify({
          accessCodeId: docSnap.id,
          accessCode: normalisedCode,
          invitedEmail: data.email || normalisedEmail,
        })
      );
      navigate("/induction");
    } catch (err) {
      console.error(err);
      if (err && err.code === "permission-denied") {
        setError(
          "Firebase access is not configured yet. Please ask PNC IT to apply the Firestore security rules described in SETUP_FIREBASE.md."
        );
      } else {
        setError(
          "We couldn't validate your code. Please check your connection and try again."
        );
      }
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF9] flex flex-col">
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{
          backgroundImage:
            'url("https://images.unsplash.com/photo-1483959651481-dc75b89291f1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwyfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMGJhY2tncm91bmQlMjBsaWdodCUyMGNsZWFufGVufDB8fHx8MTc4MDkwOTMxOHww&ixlib=rb-4.1.0&q=85")',
          backgroundSize: "cover",
          backgroundPosition: "center",
          filter: "blur(6px)",
        }}
      />
      <div className="relative flex-1 flex flex-col items-center justify-center p-5 sm:p-8">
        <div className="w-full max-w-md">
          <div className="mb-7 text-center">
            <div className="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-[#166534] text-white shadow-sm mb-4">
              <ShieldCheck className="h-6 w-6" strokeWidth={2} />
            </div>
            <h1 className="font-heading text-3xl sm:text-4xl tracking-tight text-[#1C1917]">
              PNC Induction Portal
            </h1>
            <p className="text-sm text-[#57534E] mt-2 leading-relaxed">
              Welcome. Enter the email and access code from your invitation to
              begin your digital induction.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="rounded-2xl bg-white border border-[#E7E5E4] shadow-sm p-5 sm:p-6 space-y-4"
          >
            <Field label="Email Address" required>
              <TextInput
                data-testid={GATE.emailInput}
                type="text"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Access Code" required>
              <TextInput
                data-testid={GATE.codeInput}
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="e.g. PNC-AB12-CD34"
                autoCapitalize="characters"
                spellCheck={false}
              />
            </Field>

            {error && (
              <div
                data-testid={GATE.error}
                className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C] text-sm p-3"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              data-testid={GATE.submitBtn}
              disabled={loading}
              className="w-full h-14 rounded-xl bg-[#166534] hover:bg-[#14532D] active:bg-[#14532D] disabled:opacity-60 text-white font-medium text-base inline-flex items-center justify-center gap-2 transition-colors shadow-sm"
            >
              {loading ? "Validating..." : "Begin Induction"}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>

            <div className="text-xs text-[#57534E] flex items-start gap-2 pt-1">
              <Lock className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
              Your information is encrypted and stored securely. Access codes
              are single-use and tied to your email.
            </div>
          </form>

          <p className="text-center text-xs text-[#57534E] mt-6">
            Need help? Contact PNC HR at{" "}
            <a className="underline" href="mailto:hr@pnc.co.uk">hr@pnc.co.uk</a>
          </p>
        </div>
      </div>
    </div>
  );
}
