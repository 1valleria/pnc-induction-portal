import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setCreds } from "@/lib/adminAuth";
import { Field, TextInput } from "@/components/Field";
import { Lock, ShieldCheck, ArrowRight } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL || "";

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!username || !password) {
      setError("Please enter both username and password.");
      return;
    }
    setLoading(true);
    try {
      const token = btoa(`${username}:${password}`);
      const res = await fetch(`${API}/api/admin/employees?limit=1`, {
        headers: { Authorization: `Basic ${token}` },
      });
      if (res.status === 401) {
        setError("Invalid username or password.");
        setLoading(false);
        return;
      }
      if (!res.ok) {
        setError(`Server returned ${res.status}. Please try again.`);
        setLoading(false);
        return;
      }
      setCreds(username, password);
      navigate("/admin/employees", { replace: true });
    } catch (err) {
      setError("Connection error. Please check your network and try again.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF9] flex items-center justify-center p-5">
      <div className="w-full max-w-md">
        <div className="mb-7 text-center">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-[#1C1917] text-white mb-4">
            <ShieldCheck className="h-6 w-6" strokeWidth={2} />
          </div>
          <h1 className="font-heading text-3xl sm:text-4xl tracking-tight text-[#1C1917]">
            PNC HR Admin
          </h1>
          <p className="text-sm text-[#57534E] mt-2">
            Subcontractor database & induction records
          </p>
        </div>
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl bg-white border border-[#E7E5E4] shadow-sm p-5 sm:p-6 space-y-4"
        >
          <Field label="Admin Username" required>
            <TextInput
              data-testid="admin-login-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="pnc-admin"
            />
          </Field>
          <Field label="Admin Password" required>
            <TextInput
              data-testid="admin-login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </Field>
          {error && (
            <div
              data-testid="admin-login-error"
              className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C] text-sm p-3"
            >
              {error}
            </div>
          )}
          <button
            type="submit"
            data-testid="admin-login-submit"
            disabled={loading}
            className="w-full h-14 rounded-xl bg-[#1C1917] hover:bg-[#0C0A09] disabled:opacity-60 text-white font-medium text-base inline-flex items-center justify-center gap-2 transition-colors"
          >
            {loading ? "Signing in..." : "Sign in"}
            {!loading && <ArrowRight className="h-4 w-4" />}
          </button>
          <div className="text-xs text-[#57534E] flex items-start gap-2 pt-1">
            <Lock className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
            Credentials are validated against the backend's Basic Auth. They are stored only in this browser session.
          </div>
        </form>
      </div>
    </div>
  );
}
