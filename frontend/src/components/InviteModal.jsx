import React, { useState } from "react";
import { adminFetch } from "@/lib/adminAuth";
import { Field, TextInput } from "@/components/Field";
import { X, Mail, Copy, Check, ShieldCheck, ArrowRight, MessageSquare } from "lucide-react";
import { toast } from "sonner";

export default function InviteModal({ open, onClose, onCreated }) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [created, setCreated] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  if (!open) return null;

  const reset = () => {
    setFullName("");
    setEmail("");
    setCreated(null);
    setCopiedField(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const submit = async (sendEmail) => {
    if (!fullName.trim()) {
      toast.error("Full name is required.");
      return;
    }
    if (sendEmail && !email.trim()) {
      toast.error("Email is required to send the invitation.");
      return;
    }
    setSending(true);
    try {
      const res = await adminFetch("/api/admin/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim() || null,
          send_email: sendEmail,
        }),
      });
      const data = await res.json();
      setCreated(data);
      onCreated?.(data);
      if (sendEmail) {
        toast.success(
          data.email_result?.redirected
            ? `Email sent (redirected to ${data.email_result.actual_recipient} — Resend test mode).`
            : `Invitation sent to ${data.email}`
        );
      } else {
        toast.success(`Access code created: ${data.code}`);
      }
    } catch (err) {
      toast.error("Could not create invitation. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const copy = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 1600);
    } catch {
      toast.error("Could not copy to clipboard.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] bg-[#1C1917]/60 backdrop-blur-sm flex items-center justify-center p-4"
      data-testid="invite-modal"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="w-full max-w-md bg-white rounded-2xl border border-[#E7E5E4] shadow-xl overflow-hidden">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[#E7E5E4]">
          <div className="h-9 w-9 rounded-lg bg-[#166534] text-white flex items-center justify-center">
            <ShieldCheck className="h-4.5 w-4.5" />
          </div>
          <div className="flex-1">
            <h2 className="font-heading text-lg text-[#1C1917] leading-tight">
              {created ? "Invitation ready" : "Invite an employee"}
            </h2>
            <p className="text-xs text-[#57534E]">
              {created
                ? "Share the access code by email, WhatsApp, SMS or Teams."
                : "Send a one-time access code by email — or generate a code to share manually."}
            </p>
          </div>
          <button
            onClick={handleClose}
            data-testid="invite-modal-close"
            className="h-8 w-8 rounded-lg hover:bg-[#FAFAF9] text-[#57534E] flex items-center justify-center"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {!created ? (
          <div className="p-5 space-y-4">
            <Field label="Full Name" required>
              <TextInput
                data-testid="invite-full-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. John Smith"
                autoFocus
              />
            </Field>
            <Field
              label="Email Address"
              hint="Required only if you want PNC to send the invitation email automatically."
            >
              <TextInput
                data-testid="invite-email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. john@example.com"
                type="text"
                inputMode="email"
              />
            </Field>

            <div className="flex flex-col sm:flex-row gap-2 pt-2">
              <button
                type="button"
                disabled={sending}
                onClick={() => submit(true)}
                data-testid="invite-send-email-btn"
                className="flex-1 h-12 rounded-xl bg-[#166534] hover:bg-[#14532D] disabled:opacity-60 text-white font-medium inline-flex items-center justify-center gap-2"
              >
                <Mail className="h-4 w-4" /> Send Email
              </button>
              <button
                type="button"
                disabled={sending}
                onClick={() => submit(false)}
                data-testid="invite-just-create-btn"
                className="flex-1 h-12 rounded-xl border border-[#E7E5E4] bg-white text-[#1C1917] font-medium hover:bg-[#FAFAF9] inline-flex items-center justify-center gap-2"
              >
                <MessageSquare className="h-4 w-4" /> Just Create Code
              </button>
            </div>
          </div>
        ) : (
          <div className="p-5 space-y-4">
            <div className="rounded-xl bg-[#F0FDF4] border border-[#BBF7D0] p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[#166534] font-semibold">
                Access code
              </div>
              <div className="flex items-center justify-between mt-1 gap-3">
                <div
                  className="font-mono text-xl text-[#1C1917] font-bold tracking-wider"
                  data-testid="invite-result-code"
                >
                  {created.code}
                </div>
                <button
                  onClick={() => copy(created.code, "code")}
                  data-testid="invite-copy-code-btn"
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
                  Ready-to-paste invitation
                </div>
                <button
                  onClick={() => copy(created.invitation_text, "invite")}
                  data-testid="invite-copy-invitation-btn"
                  className="h-9 px-3 rounded-lg bg-white border border-[#E7E5E4] text-[#1C1917] text-xs font-medium inline-flex items-center gap-1.5"
                >
                  {copiedField === "invite" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  {copiedField === "invite" ? "Copied" : "Copy invitation"}
                </button>
              </div>
              <pre className="mt-2 text-xs text-[#1C1917] whitespace-pre-wrap font-mono leading-relaxed">
{created.invitation_text}
              </pre>
            </div>

            {created.email_result?.status === "sent" && (
              <div className="rounded-lg bg-[#F0FDF4] border border-[#BBF7D0] text-[#166534] text-xs p-3 flex items-start gap-2">
                <Mail className="h-3.5 w-3.5 mt-0.5" />
                <div>
                  Invitation emailed to <b>{created.email}</b>
                  {created.email_result.redirected && (
                    <span> (Resend test-mode redirected to {created.email_result.actual_recipient})</span>
                  )}
                  .
                </div>
              </div>
            )}
            {created.email_result?.status === "failed" && (
              <div className="rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] text-xs p-3">
                Email failed to send. The access code is still valid — share it manually using the copy buttons above.
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => {
                  reset();
                }}
                data-testid="invite-create-another-btn"
                className="h-10 px-4 rounded-lg border border-[#E7E5E4] bg-white text-[#1C1917] text-sm font-medium hover:bg-[#FAFAF9] inline-flex items-center gap-1.5"
              >
                Create another <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={handleClose}
                data-testid="invite-done-btn"
                className="h-10 px-4 rounded-lg bg-[#1C1917] hover:bg-[#0C0A09] text-white text-sm font-medium"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
