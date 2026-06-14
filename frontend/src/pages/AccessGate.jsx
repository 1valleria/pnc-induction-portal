import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { GATE } from "@/constants/testIds";
import { TextInput, Field } from "@/components/Field";
import { Lock, ShieldCheck, ArrowRight } from "lucide-react";

const API_BASE = process.env.REACT_APP_BACKEND_URL || "";

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
    const normalisedCode = code.trim().toUpperCase();
    const normalisedEmail = email.trim().toLowerCase();
    const endpoint = `${API_BASE}/api/validate-access-code`;
    console.info("[AccessGate] POST", endpoint, { email: normalisedEmail, code: normalisedCode });

    try {
      const { data } = await axios.post(endpoint, {
        email: normalisedEmail,
        code: normalisedCode,
      });
      console.info("[AccessGate] response", data);

      if (!data || data.valid !== true) {
        const reason = data && data.reason;
        if (reason === "already_used") {
          setError("This access code has already been used. Please contact PNC Admin if you believe this is a mistake.");
        } else if (reason === "email_mismatch") {
          setError("This access code is registered to a different email address.");
        } else if (reason === "missing_fields") {
          setError("Please enter both email and access code.");
        } else {
          setError("Access code not recognised. Please check the code from your invitation email.");
        }
        setLoading(false);
        return;
      }

      sessionStorage.setItem(
        "pnc_session_v1",
        JSON.stringify({
          accessCodeId: data.access_code_id,
          accessCode: data.code || normalisedCode,
          invitedEmail: data.email || normalisedEmail,
        })
      );
      navigate("/induction");
    } catch (err) {
      console.error("[AccessGate] validation request failed", err);
      const status = err && err.response && err.response.status;
      if (status === 404) {
        setError("Login service unavailable (endpoint not deployed). Please contact PNC Admin.");
      } else if (status && status >= 500) {
        setError("Login service is temporarily unavailable. Please try again in a minute.");
      } else {
        setError("We couldn't validate your code. Please check your connection and try again.");
      }
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F5F4] px-4"
      style={{
        backgroundImage:
          "url('https://images.unsplash.com/photo-1486718448742-163732cd1544?ixlib=rb-4.0.3&q=80&w=1920&auto=format&fit=crop')",
        backgroundBlendMode: "lighten",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundColor: "#F5F5F4cc",
      }}
      data-testid={GATE.root}
    >
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#166534] text-white mb-3">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <h1 className="font-heading text-3xl tracking-tight text-[#1C1917]">PNC Induction Portal</h1>
          <p className="text-[#57534E] mt-2 text-sm">
            Welcome. Enter the email and access code from your invitation to begin your digital induction.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-[#E7E5E4] p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="Email Address" required>
              <TextInput
                data-testid={GATE.emailInput}
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                autoFocus
              />
            </Field>
            <Field label="Access Code" required>
              <TextInput
                data-testid={GATE.codeInput}
                type="text"
                placeholder="e.g. PNC-AB12-CD34"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                autoComplete="one-time-code"
              />
            </Field>

            {error && (
              <p data-testid={GATE.errorMsg} className="text-sm text-[#B91C1C] bg-[#FEF2F2] border border-[#FECACA] rounded-md p-3">
                {error}
              </p>
            )}

            <button
              data-testid={GATE.submitBtn}
              type="submit"
              disabled={loading}
              className="w-full bg-[#166534] hover:bg-[#14532D] disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium py-3 rounded-md transition-colors flex items-center justify-center gap-2"
            >
              {loading ? "Validating..." : (<>Begin Induction <ArrowRight className="w-4 h-4" /></>)}
            </button>
            <div className="text-xs text-[#57534E] flex items-start gap-2 pt-1">
              <Lock className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
              Your information is encrypted and stored securely. Access codes
              are single-use and tied to your email.
            </div>
          </form>

          <p className="text-center text-xs text-[#57534E] mt-6">
            Need help? Contact PNC Admin at{" "}
            <a className="underline" href="mailto:admin@pncunique.com">admin@pncunique.com</a>
          </p>
        </div>
      </div>
    </div>
  );
}
