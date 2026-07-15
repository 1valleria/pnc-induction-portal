import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { adminFetch, clearCreds, downloadCsv, hasCreds } from "@/lib/adminAuth";
import { TextInput } from "@/components/Field";
import InviteModal from "@/components/InviteModal";
import ReviewActionModal from "@/components/ReviewActionModal";
import TestModeBanner from "@/components/TestModeBanner";
import { Download, LogOut, Mail, RefreshCw, Search, ShieldCheck, ExternalLink, CheckCircle2, XCircle, Clock, UserPlus } from "lucide-react";
import { toast } from "sonner";

// The exact column order PNC's existing subcontractor spreadsheet uses.
// Each column declares (label, source key on the employee_summary record,
// render hint: "text" | "status" | "doc" | "review" | "link").
const COLUMNS = [
  { label: "Name", key: "full_name", kind: "text" },
  { label: "Date Of Birth", key: "dob", kind: "text" },
  { label: "Address", key: "address1", kind: "text" },
  { label: "Post Code", key: "postcode", kind: "text" },
  { label: "Phone Number", key: "telephone", kind: "text" },
  { label: "Email Address", key: "email", kind: "text" },
  { label: "NI Number", key: "ni_number", kind: "text" },
  { label: "Induction Status", key: "induction_status", kind: "status" },
  { label: "Medical Status", key: "medical_status", kind: "status" },
  { label: "Driving Licence", key: "driving_licence_url", kind: "doc" },
  { label: "Driving Licence Check", key: "dvla_check", kind: "yesno" },
  { label: "Passport", key: "passport_url", kind: "doc" },
  { label: "Right To Work", key: "right_to_work_share_code", kind: "text" },
  { label: "Proof Of Bank", key: "bank_proof_url", kind: "doc" },
  { label: "Insurance Proof", key: "insurance_certificate_url", kind: "insurance" },
  { label: "Business Name", key: "company_name", kind: "text" },
  { label: "Account Number", key: "bank_account", kind: "text" },
  { label: "Sort Code", key: "sort_code", kind: "text" },
  { label: "VAT Number", key: "vat_number", kind: "text" },
  { label: "UTR", key: "utr", kind: "text" },
  { label: "Review Status", key: "review_status", kind: "review" },
  { label: "PDF Link", key: "pdf_url", kind: "link" },
];

const STATUS_TONE = {
  Complete: "bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]",
  "Awaiting Documents": "bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]",
  Pending: "bg-[#F5F5F4] text-[#57534E] border-[#E7E5E4]",
  Clear: "bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]",
  Disclosed: "bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]",
  Incomplete: "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]",
};

const REVIEW_TONE = {
  pending_review: "bg-[#F5F5F4] text-[#57534E] border-[#E7E5E4]",
  approved: "bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]",
  rejected: "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]",
};

const REVIEW_LABEL = {
  pending_review: "Pending Review",
  approved: "Approved",
  rejected: "Rejected",
};

const StatusPill = ({ value, tone }) => (
  <span
    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${tone}`}
  >
    {value === "Complete" || value === "Clear" || value === "Approved" ? (
      <CheckCircle2 className="h-3 w-3" />
    ) : value === "Pending" || value === "Pending Review" ? (
      <Clock className="h-3 w-3" />
    ) : value === "Rejected" || value === "Incomplete" ? (
      <XCircle className="h-3 w-3" />
    ) : null}
    {value}
  </span>
);

function Cell({ col, value, row, onChangeReview }) {
  if (col.kind === "insurance") {
    // The Insurance Proof column shows the state of the "own vs covered by
    // PNC" choice made in Step 1 of the wizard. Only inductees who chose
    // "own" are required to upload a certificate; anyone covered by PNC's
    // £5/wk group policy has no certificate to show.
    const option = (row && (row.insurance_option || "")).toString().toLowerCase();
    const url = value;
    if (option === "own") {
      if (url) {
        return (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            data-testid="insurance-cell-own-provided"
            className="inline-flex items-center gap-1 text-[#166534] hover:underline text-xs whitespace-nowrap"
            title="View liability-insurance certificate"
          >
            <CheckCircle2 className="h-3 w-3" /> View <ExternalLink className="h-3 w-3" />
          </a>
        );
      }
      return (
        <span
          data-testid="insurance-cell-own-missing"
          className="inline-flex items-center gap-1 text-[#B91C1C] text-[11px] font-medium whitespace-nowrap"
          title="Own-insurance selected but certificate not uploaded"
        >
          <XCircle className="h-3 w-3" /> Missing
        </span>
      );
    }
    if (option === "pnc") {
      return (
        <span
          data-testid="insurance-cell-pnc"
          className="inline-flex items-center gap-1 text-[#57534E] text-[11px] font-medium whitespace-nowrap"
          title="Covered by PNC's group liability policy (£5/wk)"
        >
          Covered by PNC
        </span>
      );
    }
    return <span className="text-[#A8A29E] text-xs">—</span>;
  }
  if (col.kind === "invoice_service") {
    const requested = Boolean(value);
    const emails = (row && Array.isArray(row.invoice_emails)) ? row.invoice_emails : [];
    if (!requested) {
      return (
        <span
          data-testid="invoice-service-cell-no"
          className="inline-flex items-center gap-1 text-[#57534E] text-[11px] font-medium"
        >
          <XCircle className="h-3 w-3" /> No
        </span>
      );
    }
    return (
      <div className="flex flex-col gap-1" data-testid="invoice-service-cell-yes">
        <span className="inline-flex items-center gap-1 text-[#166534] text-[11px] font-medium whitespace-nowrap">
          <CheckCircle2 className="h-3 w-3" /> Yes · £2/wk
        </span>
        {emails.length > 0 && (
          <span
            className="text-[10px] text-[#57534E] leading-tight max-w-[180px] break-words"
            title={emails.join(", ")}
          >
            {emails.join(", ")}
          </span>
        )}
      </div>
    );
  }
  if (col.kind === "compliance") {
    const hsOk = Boolean(row && row.health_safety_acknowledged);
    const srOk = Boolean(row && row.site_rules_acknowledged);
    if (hsOk && srOk) {
      return (
        <div className="flex flex-col gap-1" data-testid="compliance-cell-complete">
          <span className="inline-flex items-center gap-1 text-[#166534] text-[11px] font-medium whitespace-nowrap">
            <CheckCircle2 className="h-3 w-3" /> Health &amp; Safety
          </span>
          <span className="inline-flex items-center gap-1 text-[#166534] text-[11px] font-medium whitespace-nowrap">
            <CheckCircle2 className="h-3 w-3" /> Site Rules
          </span>
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-1" data-testid="compliance-cell-incomplete">
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-medium whitespace-nowrap ${
            hsOk ? "text-[#166534]" : "text-[#B91C1C]"
          }`}
        >
          {hsOk ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
          Health &amp; Safety
        </span>
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-medium whitespace-nowrap ${
            srOk ? "text-[#166534]" : "text-[#B91C1C]"
          }`}
        >
          {srOk ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
          Site Rules
        </span>
        {!hsOk && !srOk && (
          <span className="text-[10px] text-[#A8A29E]">Not Completed</span>
        )}
      </div>
    );
  }
  if (value === null || value === undefined || value === "") {
    if (col.kind === "doc") return <span className="text-[#A8A29E] text-xs">—</span>;
    return <span className="text-[#A8A29E]">—</span>;
  }
  switch (col.kind) {
    case "status":
      return <StatusPill value={value} tone={STATUS_TONE[value] || STATUS_TONE.Pending} />;
    case "yesno": {
      const v = String(value).toLowerCase();
      return v === "yes" ? (
        <span className="inline-flex items-center gap-1 text-[#166534] text-xs font-medium">
          <CheckCircle2 className="h-3.5 w-3.5" /> Yes
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-[#B91C1C] text-xs font-medium">
          <XCircle className="h-3.5 w-3.5" /> No
        </span>
      );
    }
    case "doc":
      return (
        <a
          href={value}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[#166534] hover:underline text-xs"
        >
          View <ExternalLink className="h-3 w-3" />
        </a>
      );
    case "link":
      return (
        <a
          href={value}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[#1C1917] underline-offset-2 hover:underline text-xs"
        >
          Open PDF <ExternalLink className="h-3 w-3" />
        </a>
      );
    case "review": {
      const v = String(value);
      const managerEmails = (row && Array.isArray(row.manager_emails)) ? row.manager_emails : [];
      const managerCount = managerEmails.length > 0
        ? managerEmails.length
        : (row && row.manager_email
            ? row.manager_email.split(/[,;]/).map((s) => s.trim()).filter(Boolean).length
            : 0);
      return (
        <div className="flex items-center gap-1.5 flex-wrap">
          <select
            value={v}
            onChange={(e) => {
              const next = e.target.value;
              // No-op if the value didn't actually change (defensive; browsers
              // sometimes fire change with the same value on programmatic
              // resets after failed PATCHes).
              if (next === v) return;
              onChangeReview(next, v);
            }}
            className={`text-[11px] font-medium px-2 py-1 rounded-full border focus:outline-none focus:ring-2 focus:ring-[#166534]/30 ${REVIEW_TONE[v] || REVIEW_TONE.pending_review}`}
            data-testid="admin-row-review-select"
          >
            <option value="pending_review">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          {managerCount > 0 && (
            <span
              data-testid="admin-row-manager-chip"
              title={managerEmails.length > 0 ? managerEmails.join(", ") : (row.manager_email || "")}
              className="inline-flex items-center gap-1 rounded-full border border-[#E7E5E4] bg-[#FAFAF9] text-[#57534E] px-2 py-0.5 text-[11px] font-medium whitespace-nowrap"
            >
              <Mail className="h-3 w-3" />
              Manager: {managerCount}
            </span>
          )}
        </div>
      );
    }
    default:
      return <span className="whitespace-nowrap">{String(value)}</span>;
  }
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [q, setQ] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [reviewModal, setReviewModal] = useState(null); // { employee_id, mode, name, email }
  const [defaultManagerEmails, setDefaultManagerEmails] = useState([]);

  useEffect(() => {
    if (!hasCreds()) {
      navigate("/admin", { replace: true });
    }
  }, [navigate]);

  // One-shot fetch of runtime config so the review modal can pre-fill
  // the "Manager Email(s)" field with DEFAULT_MANAGER_EMAILS from the
  // deployment env.
  useEffect(() => {
    if (!hasCreds()) return;
    (async () => {
      try {
        const res = await adminFetch("/api/admin/system-status");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.default_manager_emails)) {
            setDefaultManagerEmails(data.default_manager_emails);
          }
        }
      } catch (statusErr) {
        console.debug("[AdminDashboard] system-status fetch failed", statusErr);
      }
    })();
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (reviewFilter) params.set("review_status", reviewFilter);
      const res = await adminFetch(`/api/admin/employees?${params}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (err) {
      if (err.message === "Unauthorized") {
        navigate("/admin", { replace: true });
        return;
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [navigate, reviewFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!q.trim()) return items;
    const n = q.trim().toLowerCase();
    return items.filter((r) =>
      [r.full_name, r.email, r.ni_number, r.company_name, r.telephone]
        .map((v) => (v || "").toLowerCase())
        .some((v) => v.includes(n))
    );
  }, [items, q]);

  /** Triggered by the inline review dropdown.
   *   - Every status change (including "pending_review") now goes through
   *     ReviewActionModal so nothing can happen silently. The modal calls
   *     submitReview() once HR confirms.
   */
  const onReviewSelect = (employeeId, review_status, currentValue) => {
    const rec = items.find((r) => r.employee_id === employeeId);
    setReviewModal({
      employee_id: employeeId,
      mode: review_status,
      name: rec?.full_name,
      email: rec?.email || rec?.invited_email,
      // Snapshot the DB value the admin saw BEFORE picking the new option.
      // The backend uses this for optimistic-concurrency protection.
      if_previous_status: currentValue || rec?.review_status || "pending_review",
    });
  };

  /** Actually submit the review (called from ReviewActionModal on confirm).
   *  Returns the backend response so the modal can reveal the freshly minted
   *  access code after a rejection.
   */
  const submitReview = async ({ employeeId, review_status, review_note, manager_email, manager_count, if_previous_status }) => {
    try {
      const body = { review_status };
      if (review_note !== undefined) body.review_note = review_note;
      if (manager_email) body.manager_email = manager_email;
      if (if_previous_status) body.if_previous_status = if_previous_status;
      const res = await adminFetch(`/api/admin/employees/${employeeId}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      // 409 = optimistic-concurrency conflict. Refresh and abort.
      if (res.status === 409) {
        toast.error(
          "This record was changed by someone else since you loaded the dashboard. Refreshing…"
        );
        load();
        return undefined;
      }
      // 4xx / 5xx other than 409 — throw so the catch below surfaces the error.
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();

      // If the backend short-circuited (idempotent no-op) it echoes back the
      // existing state with idempotent:true and skipped_no_change. Treat as
      // success but tell HR nothing changed.
      if (data.idempotent) {
        toast.info("Status unchanged — no email sent.");
        setReviewModal(null);
        return data;
      }
      setItems((prev) =>
        prev.map((r) =>
          r.employee_id === employeeId
            ? {
                ...r,
                review_status,
                review_note: review_note ?? r.review_note,
                manager_email: data.manager_email ?? r.manager_email,
                manager_emails: data.manager_emails ?? r.manager_emails,
                manager_notified_at: data.manager_notified_at ?? r.manager_notified_at,
                resubmission_code: data.new_access_code ?? r.resubmission_code,
                resubmission_requested:
                  data.new_access_code ? true : r.resubmission_requested,
              }
            : r
        )
      );

      const mgrStatus = data.manager_email_status;
      const mgrCount = Array.isArray(data.manager_emails) ? data.manager_emails.length : (manager_count || 0);
      const mgrLabel = mgrCount > 1 ? `${mgrCount} managers` : "manager";
      const mgrSent = mgrStatus === "sent";
      const mgrPartial = mgrStatus === "partial";
      const mgrFailed = mgrStatus === "failed";

      if (review_status === "approved") {
        setReviewModal(null);
        if (mgrSent) toast.success(`Employee approved and ${mgrLabel} notified`);
        else if (mgrPartial) toast.warning(`Employee approved · some manager emails failed (check Cloud Run logs)`);
        else if (mgrFailed) toast.warning(`Employee approved · manager email(s) failed to send`);
        else if (data.email_status === "sent") toast.success("Employee approved");
        else if (data.email_status === "failed") toast.error("Approved · employee email failed");
        else toast.success("Employee approved");
      } else if (review_status === "rejected") {
        if (mgrSent) {
          toast.success(`Employee rejected and ${mgrLabel} notified`);
        } else if (mgrPartial) {
          toast.warning("Employee rejected · some manager emails failed (check Cloud Run logs)");
        } else if (mgrFailed) {
          toast.warning("Employee rejected · manager email(s) failed to send");
        } else if (data.email_status === "sent") {
          toast.success("Employee rejected and resubmission code sent");
        } else if (data.email_status === "failed") {
          toast.error("Rejected · email failed to send (access code still generated)");
        } else {
          toast.success("Employee rejected and resubmission code sent");
        }
      } else {
        setReviewModal(null);
        toast.success("Marked Pending Review");
      }
      return data;
    } catch (err) {
      toast.error("Could not update review status.");
      return undefined;
    }
  };

  const handleCsv = async () => {
    try {
      const filters = {};
      if (reviewFilter) filters.review_status = reviewFilter;
      await downloadCsv(filters);
    } catch {
      toast.error("CSV download failed. Please re-authenticate.");
      navigate("/admin");
    }
  };

  const signOut = () => {
    clearCreds();
    navigate("/admin", { replace: true });
  };

  const totals = useMemo(() => {
    const t = { all: items.length, pending: 0, approved: 0, rejected: 0, awaiting: 0 };
    for (const r of items) {
      if (r.review_status === "approved") t.approved++;
      else if (r.review_status === "rejected") t.rejected++;
      else t.pending++;
      if (r.induction_status === "Awaiting Documents") t.awaiting++;
    }
    return t;
  }, [items]);

  return (
    <div className="min-h-screen bg-[#FAFAF9]">
      <TestModeBanner />
      {/* Header */}
      <header className="bg-white border-b border-[#E7E5E4] sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3 flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-[#1C1917] text-white flex items-center justify-center">
            <ShieldCheck className="h-4.5 w-4.5" />
          </div>
          <div>
            <div className="font-heading text-lg text-[#1C1917] leading-tight">
              PNC UNIQUE LTD HR
            </div>
            <div className="text-[11px] text-[#57534E] -mt-0.5">
              Subcontractor database
            </div>
          </div>
          <nav className="ml-6 hidden sm:flex items-center gap-1 text-sm">
            <span className="px-3 py-1.5 rounded-lg bg-[#FAFAF9] text-[#1C1917] font-medium">
              Employees
            </span>
            <Link
              to="/admin/invitations"
              data-testid="admin-nav-invitations"
              className="px-3 py-1.5 rounded-lg text-[#57534E] hover:text-[#1C1917] hover:bg-[#FAFAF9]"
            >
              Invitations
            </Link>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button
              data-testid="admin-invite-btn"
              onClick={() => setShowInvite(true)}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg bg-[#166534] hover:bg-[#14532D] text-white"
            >
              <UserPlus className="h-3.5 w-3.5" /> Invite Employee
            </button>
            <button
              data-testid="admin-refresh-btn"
              onClick={load}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg border border-[#E7E5E4] bg-white hover:bg-[#FAFAF9]"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
            <button
              data-testid="admin-csv-btn"
              onClick={handleCsv}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg border border-[#E7E5E4] bg-white hover:bg-[#FAFAF9] text-[#1C1917]"
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
            <button
              data-testid="admin-signout-btn"
              onClick={signOut}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg border border-[#E7E5E4] bg-white hover:bg-[#FAFAF9] text-[#57534E]"
              title="Sign out"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* Stats */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 pt-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Inductees" value={totals.all} />
          <Stat label="Pending Review" value={totals.pending} tone="warn" />
          <Stat label="Approved" value={totals.approved} tone="good" />
          <Stat label="Awaiting Documents" value={totals.awaiting} tone="bad" />
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 pt-4">
        <div className="bg-white border border-[#E7E5E4] rounded-xl p-3 flex flex-wrap gap-2 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#A8A29E]" />
            <TextInput
              data-testid="admin-search-input"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name, email, NI, company…"
              className="!h-10 pl-9"
            />
          </div>
          <select
            data-testid="admin-review-filter"
            value={reviewFilter}
            onChange={(e) => setReviewFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-[#E7E5E4] bg-white text-sm"
          >
            <option value="">All review states</option>
            <option value="pending_review">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <div className="text-xs text-[#57534E] ml-auto">
            Showing {filtered.length} of {items.length}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4">
        <div className="bg-white border border-[#E7E5E4] rounded-xl overflow-hidden">
          <div className="overflow-x-auto" data-testid="admin-table-scroll">
            <table className="min-w-full text-sm" data-testid="admin-employee-table">
              <thead className="bg-[#FAFAF9] text-[11px] uppercase tracking-wide text-[#57534E]">
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="text-left font-semibold px-3 py-3 whitespace-nowrap border-b border-[#E7E5E4]">
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={COLUMNS.length} className="px-3 py-10 text-center text-[#57534E]">
                      Loading inductees…
                    </td>
                  </tr>
                )}
                {!loading && error && (
                  <tr>
                    <td colSpan={COLUMNS.length} className="px-3 py-6 text-center text-[#B91C1C]">
                      {error}
                    </td>
                  </tr>
                )}
                {!loading && !error && filtered.length === 0 && (
                  <tr>
                    <td colSpan={COLUMNS.length} className="px-3 py-10 text-center text-[#57534E]">
                      No inductees match the current filters.
                    </td>
                  </tr>
                )}
                {!loading && !error &&
                  filtered.map((rec) => (
                    <tr
                      key={rec.employee_id}
                      className="border-b border-[#F5F5F4] hover:bg-[#FAFAF9]"
                      data-testid={`admin-row-${rec.employee_id}`}
                    >
                      {COLUMNS.map((c) => (
                        <td key={c.key} className="px-3 py-3 align-top text-[#1C1917]">
                          <Cell
                            col={c}
                            value={rec[c.key]}
                            row={rec}
                            onChangeReview={(v) => onReviewSelect(rec.employee_id, v)}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="mt-4 text-xs text-[#57534E]">
          <Link to="/" className="underline">Back to induction portal</Link>
        </div>
      </div>

      <InviteModal
        open={showInvite}
        onClose={() => setShowInvite(false)}
        onCreated={() => {
          toast.success("Invitation recorded — see the Invitations tab to track delivery.");
        }}
      />

      <ReviewActionModal
        open={!!reviewModal}
        mode={reviewModal?.mode}
        employeeName={reviewModal?.name}
        employeeEmail={reviewModal?.email}
        defaultManagerEmails={defaultManagerEmails}
        onClose={() => setReviewModal(null)}
        onConfirm={async ({ review_status, review_note, manager_email, manager_count }) => {
          return await submitReview({
            employeeId: reviewModal.employee_id,
            review_status,
            review_note,
            manager_email,
            manager_count,
            if_previous_status: reviewModal.if_previous_status,
          });
        }}
      />
    </div>
  );
}

function Stat({ label, value, tone }) {
  const toneCls =
    tone === "good"
      ? "border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]"
      : tone === "warn"
      ? "border-[#FDE68A] bg-[#FEF3C7] text-[#92400E]"
      : tone === "bad"
      ? "border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]"
      : "border-[#E7E5E4] bg-white text-[#1C1917]";
  return (
    <div className={`rounded-xl border p-4 ${toneCls}`}>
      <div className="text-[11px] uppercase tracking-wide opacity-80">{label}</div>
      <div className="font-heading text-2xl mt-0.5">{value}</div>
    </div>
  );
}
