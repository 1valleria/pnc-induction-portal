import React, { useEffect, useState } from "react";
import { X, ShieldCheck, AlertTriangle, Mail, Send } from "lucide-react";
import { Field, TextArea } from "@/components/Field";

/**
 * Review action modal:
 *   mode="approved"  -> confirm approval and send approval email
 *   mode="rejected"  -> capture required rejection reason and send email
 *
 * onConfirm receives { review_status, review_note }.
 */
export default function ReviewActionModal({ open, mode, employeeName, employeeEmail, onConfirm, onClose }) {
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (open) {
      setNote("");
      setSending(false);
    }
  }, [open, mode]);

  if (!open) return null;

  const isReject = mode === "rejected";
  const title = isReject ? "Reject induction" : "Approve induction";
  const accent = isReject ? "#B91C1C" : "#166534";
  const accentBg = isReject ? "#FEF2F2" : "#F0FDF4";
  const accentBorder = isReject ? "#FECACA" : "#BBF7D0";
  const Icon = isReject ? AlertTriangle : ShieldCheck;

  const canSubmit = isReject ? note.trim().length > 0 : true;

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    if (!canSubmit || sending) return;
    setSending(true);
    try {
      await onConfirm({
        review_status: isReject ? "rejected" : "approved",
        review_note: isReject ? note.trim() : undefined,
      });
    } finally {
      setSending(false);
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
            style={{ background: accentBg, color: accent, border: `1px solid ${accentBorder}` }}
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
          {isReject ? (
            <>
              <p className="text-sm text-[#1C1917] leading-relaxed">
                The inductee will receive an automated email asking them to provide more
                information or resubmit. Please add a clear reason — your note will appear in
                the email exactly as written.
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
              <div className="rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] text-xs p-3 flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 mt-0.5" />
                Rejecting moves the record to <b>Rejected</b> and sends the email immediately.
                You can re-approve later if the inductee resubmits.
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-[#1C1917] leading-relaxed">
                The inductee will be marked <b>Approved</b> and immediately notified by email
                that they are cleared to start.
              </p>
              <div className="rounded-lg bg-[#F0FDF4] border border-[#BBF7D0] text-[#166534] text-xs p-3 flex items-start gap-2">
                <Mail className="h-3.5 w-3.5 mt-0.5" />
                Subject line: <b>PNC Induction Approved</b>
              </div>
            </>
          )}
        </div>

        <div className="px-5 py-4 border-t border-[#E7E5E4] flex items-center justify-end gap-2 bg-[#FAFAF9]">
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
            {sending ? "Sending…" : isReject ? "Send Rejection Email" : "Send Approval Email"}
          </button>
        </div>
      </form>
    </div>
  );
}
