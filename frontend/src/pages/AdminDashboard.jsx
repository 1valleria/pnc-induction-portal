import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { adminFetch, clearCreds, downloadCsv, hasCreds } from "@/lib/adminAuth";
import { TextInput } from "@/components/Field";
import InviteModal from "@/components/InviteModal";
import ReviewActionModal from "@/components/ReviewActionModal";
import { Download, LogOut, RefreshCw, Search, ShieldCheck, ExternalLink, CheckCircle2, XCircle, Clock, UserPlus } from "lucide-react";
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

function Cell({ col, value, onChangeReview }) {
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
      return (
        <select
          value={v}
          onChange={(e) => onChangeReview(e.target.value)}
          className={`text-[11px] font-medium px-2 py-1 rounded-full border focus:outline-none focus:ring-2 focus:ring-[#166534]/30 ${REVIEW_TONE[v] || REVIEW_TONE.pending_review}`}
        >
          <option value="pending_review">Pending Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
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

  useEffect(() => {
    if (!hasCreds()) {
      navigate("/admin", { replace: true });
    }
  }, [navigate]);

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
   *   - "pending_review" → set directly with no email (just resets state).
   *   - "approved" / "rejected" → open ReviewActionModal; the modal calls
   *     submitReview() once HR confirms.
   */
  const onReviewSelect = (employeeId, review_status) => {
    if (review_status === "pending_review") {
      submitReview({ employeeId, review_status });
      return;
    }
    const rec = items.find((r) => r.employee_id === employeeId);
    setReviewModal({
      employee_id: employeeId,
      mode: review_status,
      name: rec?.full_name,
      email: rec?.email || rec?.invited_email,
    });
  };

  /** Actually submit the review (called both for "pending_review" picks and
   *  modal confirmations). */
  const submitReview = async ({ employeeId, review_status, review_note }) => {
    try {
      const body = { review_status };
      if (review_note !== undefined) body.review_note = review_note;
      const res = await adminFetch(`/api/admin/employees/${employeeId}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setItems((prev) =>
        prev.map((r) =>
          r.employee_id === employeeId
            ? { ...r, review_status, review_note: review_note ?? r.review_note }
            : r
        )
      );
      setReviewModal(null);

      if (review_status === "approved") {
        if (data.email_status === "sent") toast.success("Approved · approval email sent");
        else if (data.email_status === "failed") toast.error("Approved · email failed to send");
        else toast.success("Approved");
      } else if (review_status === "rejected") {
        if (data.email_status === "sent") toast.success("Rejected · rejection email sent");
        else if (data.email_status === "failed") toast.error("Rejected · email failed to send");
        else toast.success("Rejected");
      } else {
        toast.success("Marked Pending Review");
      }
    } catch (err) {
      toast.error("Could not update review status.");
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
      {/* Header */}
      <header className="bg-white border-b border-[#E7E5E4] sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3 flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-[#1C1917] text-white flex items-center justify-center">
            <ShieldCheck className="h-4.5 w-4.5" />
          </div>
          <div>
            <div className="font-heading text-lg text-[#1C1917] leading-tight">
              PNC HR Admin
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
        onClose={() => setReviewModal(null)}
        onConfirm={async ({ review_status, review_note }) => {
          await submitReview({
            employeeId: reviewModal.employee_id,
            review_status,
            review_note,
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
