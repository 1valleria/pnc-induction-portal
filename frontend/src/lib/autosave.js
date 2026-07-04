const STORAGE_KEY = "pnc_induction_progress_v1";

export function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (err) {
    console.debug("[autosave] loadProgress failed", err);
    return null;
  }
}

export function saveProgress(state) {
  try {
    // strip File objects (cannot be serialized) - keep only file name metadata
    const cleanFiles = {};
    if (state.files) {
      Object.entries(state.files).forEach(([k, f]) => {
        if (f && f.name) cleanFiles[k] = { name: f.name, size: f.size };
      });
    }
    const toSave = { ...state, files: cleanFiles, signature_image_data_url: state.signature_image_data_url || null };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    return true;
  } catch (err) {
    console.debug("[autosave] saveProgress failed", err);
    return false;
  }
}

export function clearProgress() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.debug("[autosave] clearProgress failed", err);
  }
}
