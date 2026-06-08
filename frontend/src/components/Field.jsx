import React from "react";

export const Field = ({ label, required, error, children, hint }) => (
  <div className="space-y-1.5">
    <label className="block text-sm font-medium text-[#1C1917]">
      {label} {required && <span className="text-[#EF4444]">*</span>}
    </label>
    {children}
    {hint && !error && <p className="text-xs text-[#57534E]">{hint}</p>}
    {error && <p className="text-xs text-[#EF4444]">{error}</p>}
  </div>
);

export const TextInput = React.forwardRef(({ className = "", ...props }, ref) => (
  <input
    ref={ref}
    className={
      "w-full h-12 sm:h-14 px-4 rounded-lg border border-[#E7E5E4] bg-white text-base text-[#1C1917] placeholder:text-[#A8A29E] focus:outline-none focus:ring-2 focus:ring-[#166534]/20 focus:border-[#166534] transition " +
      className
    }
    {...props}
  />
));
TextInput.displayName = "TextInput";

export const TextArea = React.forwardRef(({ className = "", ...props }, ref) => (
  <textarea
    ref={ref}
    rows={3}
    className={
      "w-full min-h-[88px] px-4 py-3 rounded-lg border border-[#E7E5E4] bg-white text-base text-[#1C1917] placeholder:text-[#A8A29E] focus:outline-none focus:ring-2 focus:ring-[#166534]/20 focus:border-[#166534] transition resize-y " +
      className
    }
    {...props}
  />
));
TextArea.displayName = "TextArea";

export default Field;
