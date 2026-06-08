import React, { useRef, useState } from "react";
import { UploadCloud, FileText, X, CheckCircle2 } from "lucide-react";
import { validateFile } from "@/lib/upload";

export const FileDropzone = ({ label, hint, value, onChange, testId, required }) => {
  const inputRef = useRef(null);
  const [error, setError] = useState(null);

  const handleFiles = (files) => {
    const file = files && files[0];
    if (!file) return;
    const err = validateFile(file);
    if (err) {
      setError(err);
      onChange(null);
      return;
    }
    setError(null);
    onChange(file);
  };

  const clear = () => {
    onChange(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-[#1C1917]">
        {label} {required && <span className="text-[#EF4444]">*</span>}
      </label>
      {!value ? (
        <button
          type="button"
          data-testid={testId}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            handleFiles(e.dataTransfer.files);
          }}
          className="w-full min-h-[120px] border-2 border-dashed border-[#E7E5E4] rounded-xl flex flex-col items-center justify-center bg-[#FAFAF9] hover:bg-[#F5F5F4] active:bg-[#F0EFEE] transition-colors p-5 text-center"
        >
          <UploadCloud className="h-7 w-7 text-[#166534] mb-2" strokeWidth={2} />
          <div className="text-sm font-medium text-[#1C1917]">Tap to upload or drag a file</div>
          <div className="text-xs text-[#57534E] mt-0.5">{hint || "JPG, PNG or PDF · max 10 MB"}</div>
        </button>
      ) : (
        <div className="flex items-center gap-3 border border-[#BBF7D0] bg-[#F0FDF4] rounded-xl p-3">
          <div className="h-10 w-10 rounded-lg bg-white border border-[#BBF7D0] flex items-center justify-center">
            <FileText className="h-5 w-5 text-[#166534]" strokeWidth={2} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-[#1C1917] truncate flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-[#166534]" /> {value.name || "Selected file"}
            </div>
            <div className="text-xs text-[#57534E]">
              {value.size ? `${(value.size / 1024 / 1024).toFixed(2)} MB` : ""}
            </div>
          </div>
          <button
            type="button"
            onClick={clear}
            data-testid={`${testId}-remove`}
            className="h-9 w-9 rounded-lg hover:bg-white flex items-center justify-center text-[#57534E]"
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/jpg,application/pdf"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {error && <p className="text-xs text-[#EF4444]">{error}</p>}
    </div>
  );
};

export default FileDropzone;
