import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { adminFetch, clearCreds, hasCreds } from "@/lib/adminAuth";
import { CheckCircle2, Clock, LogOut, RefreshCw, ShieldCheck, UserPlus, XCircle, Mail, MessageSquare, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import InviteModal from "@/components/InviteModal";

const STATUS_BADGE = {
  sent: { tone: "bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]", icon: <Mail className="h-3 w-3" /> },
  created: { tone: "bg-[#F5F5F4] text-[#57534E] border-[#E7E5E4]", icon: <MessageSquare className="h-3 w-3" /> },
  failed: { tone: "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]", icon: <XCircle className="h-3 w-3" /> },
  used: { tone: "bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]", icon: <CheckCircle2 className="h-3 w-3" /> },
};

const STATUS_LABEL = {
  sent: "Sent",
  created: "Code Only",
  failed: "Email Failed",
  used: "Used",
};

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AdminInvitations() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showInvite, setShowInvite] = useState(false);

  useEffect(() => {
    if (!hasCreds()) {
      navigate("/admin", { replace: true });
    }
  }, [navigate]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminFetch("/api/admin/invites");
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
  }, [navigate]);

  useEffect(() => {
    load();
  }, [load]);

  const signOut = () => {
    clearCreds();
    navigate("/admin", { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#FAFAF9]">
      <header className="bg-white border-b border-[#E7E5E4] sticky top-0 z-30">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-3 flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-[#1C1917] text-white flex items-center justify-center">
            <ShieldCheck className="h-4.5 w-4.5" />
          </div>
          <div>
            <div className="font-heading text-lg text-[#1C1917] leading-tight">PNC HR Admin</div>
            <div className="text-[11px] text-[#57534E] -mt-0.5">Invitations</div>
          </div>
          <nav className="ml-6 hidden sm:flex items-center gap-1 text-sm">
            <Link
              to="/admin/employees"
              className="px-3 py-1.5 rounded-lg text-[#57534E] hover:text-[#1C1917] hover:bg-[#FAFAF9]"
            >
              Employees
            </Link>
            <span className="px-3 py-1.5 rounded-lg bg-[#FAFAF9] text-[#1C1917] font-medium">
              Invitations
            </span>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button
              data-testid="invitations-refresh-btn"
              onClick={load}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg border border-[#E7E5E4] bg-white hover:bg-[#FAFAF9]"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
            <button
              data-testid="invitations-invite-btn"
              onClick={() => setShowInvite(true)}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg bg-[#166534] hover:bg-[#14532D] text-white"
            >
              <UserPlus className="h-3.5 w-3.5" /> Invite Employee
            </button>
            <button
              data-testid="invitations-signout-btn"
              onClick={signOut}
              className="h-9 px-3 inline-flex items-center gap-1.5 text-sm rounded-lg border border-[#E7E5E4] bg-white hover:bg-[#FAFAF9] text-[#57534E]"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-5">
        <div className="bg-white border border-[#E7E5E4] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="invitations-table">
              <thead className="bg-[#FAFAF9] text-[11px] uppercase tracking-wide text-[#57534E]">
                <tr>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]">Full Name</th>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]">Email</th>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]">Access Code</th>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]">Invite Status</th>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]">Used</th>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]">Invited At</th>
                  <th className="text-left font-semibold px-3 py-3 border-b border-[#E7E5E4]"></th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={7} className="px-3 py-10 text-center text-[#57534E]">Loading invitations…</td></tr>
                )}
                {!loading && error && (
                  <tr><td colSpan={7} className="px-3 py-6 text-center text-[#B91C1C]">{error}</td></tr>
                )}
                {!loading && !error && items.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-10 text-center text-[#57534E]">
                      No invitations yet. Click <b>Invite Employee</b> to send the first one.
                    </td>
                  </tr>
                )}
                {!loading && !error && items.map((it) => {
                  const badgeKey = it.used ? "used" : (it.invite_status || "created");
                  const badge = STATUS_BADGE[badgeKey] || STATUS_BADGE.created;
                  return (
                    <tr key={it.id} className="border-b border-[#F5F5F4] hover:bg-[#FAFAF9]" data-testid={`invite-row-${it.id}`}>
                      <td className="px-3 py-3 text-[#1C1917]">{it.full_name || <span className="text-[#A8A29E]">—</span>}</td>
                      <td className="px-3 py-3 text-[#1C1917]">{it.email || <span className="text-[#A8A29E]">—</span>}</td>
                      <td className="px-3 py-3 font-mono text-[#1C1917]">{it.code}</td>
                      <td className="px-3 py-3">
                        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${badge.tone}`}>
                          {badge.icon} {STATUS_LABEL[badgeKey] || badgeKey}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-[#1C1917]">
                        {it.used ? (
                          <span className="inline-flex items-center gap-1 text-[#166534] text-xs"><CheckCircle2 className="h-3.5 w-3.5" /> Used</span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[#57534E] text-xs"><Clock className="h-3.5 w-3.5" /> Not used</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-[#57534E] text-xs whitespace-nowrap">{fmtTime(it.invited_at)}</td>
                      <td className="px-3 py-3">
                        {it.employee_id ? (
                          <Link
                            to={`/admin/employees?focus=${it.employee_id}`}
                            className="inline-flex items-center gap-1 text-[#166534] text-xs hover:underline"
                          >
                            Open record <ExternalLink className="h-3 w-3" />
                          </Link>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <p className="text-xs text-[#57534E] mt-3">
          During Resend test mode every email is delivered only to the Resend account owner. The inductee's real address will start receiving mail once the PNC domain is verified.
        </p>
      </div>

      <InviteModal
        open={showInvite}
        onClose={() => setShowInvite(false)}
        onCreated={() => {
          // Refresh the list a short moment after creating
          setTimeout(load, 300);
          toast.success("Invitation recorded.");
        }}
      />
    </div>
  );
}
