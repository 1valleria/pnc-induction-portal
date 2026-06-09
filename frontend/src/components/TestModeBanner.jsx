import React, { useEffect, useState } from "react";
import { adminFetch, hasCreds } from "@/lib/adminAuth";
import { AlertTriangle, X } from "lucide-react";

/**
 * Shows a non-dismissable warning banner across the Admin Portal whenever
 * the Resend test-mode override is active. The override routes every
 * outgoing email to a single test inbox, NOT to the real inductee — so HR
 * must know it's happening before they tell a subcontractor "I sent it".
 */
export default function TestModeBanner() {
  const [status, setStatus] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!hasCreds()) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await adminFetch("/api/admin/system-status");
        const data = await res.json();
        if (!cancelled) setStatus(data);
      } catch {
        /* ignore — banner is best-effort */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!status || !status.email_test_mode || dismissed) return null;

  return (
    <div
      data-testid="test-mode-banner"
      className="w-full bg-[#FEF3C7] border-b border-[#FDE68A] text-[#92400E] text-xs"
    >
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-2 flex items-center gap-3">
        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
        <div className="flex-1 leading-snug">
          <b>Email test mode is active.</b> All invitations, approval and
          rejection emails are being delivered to{" "}
          <span className="font-mono">{status.email_redirect_to}</span> instead of
          the real recipient. Inductees will NOT receive email until your PNC
          domain is verified in Resend and{" "}
          <span className="font-mono">RESEND_TEST_OVERRIDE_EMAIL</span> is removed
          from <span className="font-mono">backend/.env</span>.
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="opacity-70 hover:opacity-100 p-1"
          aria-label="Dismiss"
          data-testid="test-mode-banner-dismiss"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
