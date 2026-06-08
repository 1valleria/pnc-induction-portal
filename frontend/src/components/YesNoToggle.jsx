import React from "react";

export const YesNoToggle = ({ value, onChange, name }) => {
  const opt = (val, label) => {
    const active = value === val;
    return (
      <button
        type="button"
        data-testid={`${name}-${val}`}
        data-state={active ? "active" : "inactive"}
        onClick={() => onChange(val)}
        className={[
          "flex-1 h-12 sm:h-14 rounded-xl border font-medium text-base transition-all duration-150",
          active
            ? "bg-[#166534] text-white border-[#166534] shadow-sm"
            : "bg-white text-[#57534E] border-[#E7E5E4] hover:bg-[#FAFAF9]",
        ].join(" ")}
      >
        {label}
      </button>
    );
  };
  return (
    <div className="flex gap-3" role="radiogroup">
      {opt("yes", "Yes")}
      {opt("no", "No")}
    </div>
  );
};

export default YesNoToggle;
