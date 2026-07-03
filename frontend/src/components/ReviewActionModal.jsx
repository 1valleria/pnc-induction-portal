import React, { useEffect, useState } from "react";
import { X, ShieldCheck, AlertTriangle, Mail, Send, Copy, Check, ArrowRight } from "lucide-react";
import { Field, TextArea, TextInput } from "@/components/Field";

/**
 * Review action modal:
 *   mode="approved"  -> confirm approval and send approval email
 *   mode="rejected"  -> capture required rejection reason and send email
 *
 * onConfirm receives { review_status, review_note } and is expected to
 * return the backend response (or undefined on failure). For rejections we
 * stay open after success to surface the freshly minted access code.
 */
export default function ReviewActionModal({ open, mode, employeeName, employeeEmail, defaultManagerEmails, onConfirm, onClose }) {
  const [note, setNote] = useState("");
  const [managerEmail, setManagerEmail] = useState("");
  const [managerError, setManagerError] = useState(null);
  const [sending, setSending] = useState(false);
  const [resubmitResult, setResubmitResult] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  useEffect(() => {
    if (open) {
      setNote("");
      // Pre-fill with the deployment-configured default manager address(es)
      // so HR never forgets to notify the admin inbox. HR can edit/clear
      // freely before submitting.
      setManagerEmail(
        Array.isArray(defaultManagerEmails) && defaultManagerEmails.length > 0
          ? defaultManagerEmails.join(", ")
          : ""
      );
      setManagerError(null);
      setSending(false);
      setResubmitResult(null);
      setCopiedField(null);
    }
  }, [open, mode, defaultManagerEmails]);

  if (!open) return null;

  const isReject = mode === "rejected";
  const showResubmit = isReject && resubmitResult;
  const title = showResubmit
    ? "Rejection sent · new access code"
    : isReject
    ? "Reject induction"
    : "Approve induction";
  const accent = isReject ? "#B91C1C" : "#166534";
  const accentBg = isReject ? "#FEF2F2" : "#F0FDF4";
  const accentBorder = isReject ? "#FECACA" : "#BBF7D0";
  const Icon = showResubmit ? ShieldCheck : isReject ? AlertTriangle : ShieldCheck;
  const headerAccent = showResubmit
    ? { bg: "#F0FDF4", border: "#BBF7D0", color: "#166534" }
    : { bg: accentBg, border: accentBorder, color: accent };

  const canSubmit = isReject ? note.trim().length > 0 : true;

  const parseManagerEmails = (raw) => {
    return (raw || "")
      .split(/[,;\n]/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0);
  };

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    if (!canSubmit || sending) return;
    const emails = parseManagerEmails(managerEmail);
    const invalid = emails.filter((addr) => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(addr));
    if (invalid.length > 0) {
      setManagerError(
        invalid.length === 1
          ? `Invalid email address: ${invalid[0]}`
          : `Invalid email addresses: ${invalid.join(", ")}`
      );
      return;
    }
    setManagerError(null);
    setSending(true);
    try {
      const result = await onConfirm({
        review_status: isReject ? "rejected" : "approved",
        review_note: isReject ? note.trim() : undefined,
        manager_email: emails.join(", ") || undefined,
        manager_count: emails.length,
      });
      if (isReject && result && result.new_access_code) {
        setResubmitResult(result);
        setSending(false);
        return;
      }
    } finally {
      if (!isReject) setSending(false);
    }
  };

  const copy = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 1600);
    } catch {
      /* ignore */
    }
  };

  return (
    <div
      className="fixed inset-0 z-[70] bg-[#1C1917]/60 backdrop-blur-sm flex items-center justify-center p-4"
      data-testid="review-modal"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-white rounded-2xl border border-[#E7E5E4] shadow-xl overflow-hidden"
      >
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[#E7E5E4]">
          <div
            className="h-9 w-9 rounded-lg flex items-center justify-center"
            style={{ background: headerAccent.bg, color: headerAccent.color, border: `1px solid ${headerAccent.border}` }}
          >
            <Icon className="h-4.5 w-4.5" />
          </div>
          <div className="flex-1">
            <h2 className="font-heading text-lg text-[#1C1917] leading-tight" data-testid="review-modal-title">
              {title}
            </h2>
            <p className="text-xs text-[#57534E]">
              {employeeName ? <><b>{employeeName}</b> · {employeeEmail || "no email on file"}</> : "Selected inductee"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="review-modal-close"
            className="h-8 w-8 rounded-lg hover:bg-[#FAFAF9] text-[#57534E] flex items-center justify-center"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {showResubmit ? (
            <>
              <p className="text-sm text-[#1C1917] leading-relaxed" data-testid="review-modal-success-message">
                Rejection email sent and new access code generated.
              </p>

              <div className="rounded-xl bg-[#F0FDF4] border border-[#BBF7D0] p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-[#166534] font-semibold">
                  New access code
                </div>
                <div className="flex items-center justify-between mt-1 gap-3">
                  <div
                    className="font-mono text-xl text-[#1C1917] font-bold tracking-wider"
                    data-testid="review-modal-new-code"
                  >
                    {resubmitResult.new_access_code}
                  </div>
                  <button
                    type="button"
                    onClick={() => copy(resubmitResult.new_access_code, "code")}
                    data-testid="review-modal-copy-code"
                    className="h-10 px-3 rounded-lg bg-white border border-[#BBF7D0] text-[#166534] text-xs font-medium inline-flex items-center gap-1.5"
                  >
                    {copiedField === "code" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    {copiedField === "code" ? "Copied" : "Copy code"}
                  </button>
                </div>
              </div>

              <div className="rounded-xl bg-[#FAFAF9] border border-[#E7E5E4] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[#57534E] font-semibold">
                    Resubmission invitation
                  </div>
                  <button
                    type="button"
                    onClick={() => copy(resubmitResult.invitation_text || "", "invite")}
                    data-testid="review-modal-copy-invite"
                    className="h-9 px-3 rounded-lg bg-white border border-[#E7E5E4] text-[#1C1917] text-xs font-medium inline-flex items-center gap-1.5"
                  >
                    {copiedField === "invite" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    {copiedField === "invite" ? "Copied" : "Copy resubmission invite"}
                  </button>
                </div>
                <pre className="mt-2 text-xs text-[#1C1917] whitespace-pre-wrap font-mono leading-relaxed">
{resubmitResult.invitation_text}
                </pre>
              </div>

              <div className="rounded-lg bg-[#F0FDF4] border border-[#BBF7D0] text-[#166534] text-xs p-3 flex items-start gap-2">
                <Mail className="h-3.5 w-3.5 mt-0.5" />
                Email delivered{resubmitResult.email_status === "sent" ? "" : " (status: " + (resubmitResult.email_status || "unknown") + ")"}.
                Share the code manually if HR needs to reach the inductee on another channel.
              </div>
            </>
          ) : isReject ? (
            <>
              <p className="text-sm text-[#1C1917] leading-relaxed">
                The inductee will receive an automated email containing your reason <b>and a fresh one-time access code</b> so they can resubmit. Please add a clear reason — your note appears in the email exactly as written.
              </p>
              <Field label="Reason / comment for the subcontractor" required>
                <TextArea
                  data-testid="review-modal-note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. Driving licence is expired — please re-upload a current one."
                  autoFocus
                  rows={4}
                  required
                />
              </Field>
              <Field label="Manager Email(s)" hint="Enter one or more email addresses separated by commas. Optional — copies the rejection notice to the inductee's manager(s)." error={managerError}>
                <TextInput
                  data-testid="review-modal-manager-email"
                  value={managerEmail}
                  onChange={(e) => setManagerEmail(e.target.value)}
                  placeholder="manager1@company.com, manager2@company.com"
                  type="text"
                  inputMode="email"
                />
              </Field>
              <div className="rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] text-xs p-3 flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 mt-0.5" />
                On submit we&apos;ll mark the record <b>Rejected</b>, generate a new access code and send the email immediately.
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-[#1C1917] leading-relaxed">
                The inductee will be marked <b>Approved</b> and immediately notified by email that they are cleared to start.
              </p>
              <Field label="Manager Email(s)" hint="Enter one or more email addresses separated by commas. Optional — copies the approval notice to the inductee's manager(s)." error={managerError}>
                <TextInput
                  data-testid="review-modal-manager-email"
                  value={managerEmail}
                  onChange={(e) => setManagerEmail(e.target.value)}
                  placeholder="manager1@company.com, manager2@company.com"
                  type="text"
                  inputMode="email"
                />
              </Field>
              <div className="rounded-lg bg-[#F0FDF4] border border-[#BBF7D0] text-[#166534] text-xs p-3 flex items-start gap-2">
                <Mail className="h-3.5 w-3.5 mt-0.5" />
                Subject line: <b>PNC Induction Approved</b>
              </div>
            </>
          )}
        </div>

        <div className="px-5 py-4 border-t border-[#E7E5E4] flex items-center justify-end gap-2 bg-[#FAFAF9]">
          {showResubmit ? (
            <button
              type="button"
              onClick={onClose}
              data-testid="review-modal-done"
              className="h-10 px-4 rounded-lg bg-[#1C1917] hover:bg-[#0C0A09] text-white text-sm font-medium inline-flex items-center gap-1.5"
            >
              Done <ArrowRight className="h-4 w-4" />
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                data-testid="review-modal-cancel"
                className="h-10 px-4 rounded-lg border border-[#E7E5E4] bg-white text-[#1C1917] text-sm font-medium hover:bg-[#FAFAF9]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit || sending}
                data-testid="review-modal-confirm"
                className="h-10 px-4 rounded-lg text-white text-sm font-medium inline-flex items-center gap-1.5 disabled:opacity-60"
                style={{ background: isReject ? "#B91C1C" : "#166534" }}
              >
                <Send className="h-4 w-4" />
                {sending ? "Sending…" : isReject ? "Reject and Send Email" : "Approve and Send Email"}
              </button>
            </>
          )}
        </div>
      </form>
    </div>
  );
}
