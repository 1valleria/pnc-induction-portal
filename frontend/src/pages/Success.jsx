import React from "react";
import { useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, FileText, Mail } from "lucide-react";

export default function Success() {
  const [params] = useSearchParams();
  const employeeId = params.get("id");

  return (
    <div className="min-h-screen bg-[#FAFAF9] relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage:
            'url("https://images.unsplash.com/photo-1454117096348-e4abbeba002c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGdlb21ldHJpYyUyMGJhY2tncm91bmQlMjBsaWdodCUyMGNsZWFufGVufDB8fHx8MTc4MDkwOTMxOHww&ixlib=rb-4.1.0&q=85")',
          backgroundSize: "cover",
          backgroundPosition: "center",
          filter: "blur(4px)",
        }}
      />
      <div className="relative max-w-xl mx-auto px-5 sm:px-6 pt-16 pb-10">
        <div className="rounded-2xl bg-white border border-[#E7E5E4] shadow-sm p-6 sm:p-8 text-center">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-[#F0FDF4] border border-[#BBF7D0] flex items-center justify-center text-[#166534] mb-5">
            <CheckCircle2 className="h-7 w-7" strokeWidth={2} />
          </div>
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#166534]">
            Submission Complete
          </div>
          <h1 className="font-heading text-3xl sm:text-4xl tracking-tight text-[#1C1917] mt-1">
            Thanks — you are all set.
          </h1>
          <p className="text-sm text-[#57534E] mt-3 leading-relaxed">
            Your induction has been submitted to PNC. We have recorded your details
            and uploaded your documents securely. The HR team will be in touch
            shortly.
          </p>

          {employeeId && (
            <div className="mt-5 rounded-xl bg-[#FAFAF9] border border-[#E7E5E4] p-4 text-left">
              <div className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#57534E]">
                Reference
              </div>
              <div
                className="font-mono text-sm text-[#1C1917] mt-1 break-all"
                data-testid="success-employee-id"
              >
                {employeeId}
              </div>
            </div>
          )}

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
            <div className="rounded-xl border border-[#E7E5E4] p-4 bg-white">
              <FileText className="h-5 w-5 text-[#166534]" />
              <div className="text-sm font-semibold text-[#1C1917] mt-2">
                Official PDF
              </div>
              <div className="text-xs text-[#57534E] mt-1">
                A signed induction PDF will be generated and filed by PNC HR.
              </div>
            </div>
            <div className="rounded-xl border border-[#E7E5E4] p-4 bg-white">
              <Mail className="h-5 w-5 text-[#166534]" />
              <div className="text-sm font-semibold text-[#1C1917] mt-2">
                Next steps
              </div>
              <div className="text-xs text-[#57534E] mt-1">
                Watch your inbox for confirmation and onboarding details.
              </div>
            </div>
          </div>

          <Link
            to="/"
            className="inline-block mt-7 text-sm text-[#57534E] hover:text-[#1C1917] underline"
          >
            Return to start
          </Link>
        </div>
      </div>
    </div>
  );
}
