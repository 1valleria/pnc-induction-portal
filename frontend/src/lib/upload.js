import { ref, uploadBytes, getDownloadURL } from "firebase/storage";
import { storage } from "./firebase";

export const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB
export const ALLOWED_MIME = ["image/jpeg", "image/png", "image/jpg", "application/pdf"];

export function validateFile(file) {
  if (!file) return "No file selected";
  if (!ALLOWED_MIME.includes(file.type)) return "Only JPG, PNG, or PDF allowed";
  if (file.size > MAX_FILE_BYTES) return "File exceeds 10 MB";
  return null;
}

/**
 * Slugify a full name into a Storage-safe segment.
 * - lower-case
 * - spaces -> hyphens
 * - remove every character except a-z, 0-9, hyphen
 * - collapse repeats and trim leading/trailing hyphens
 */
export function slugifyName(name) {
  if (!name) return "employee";
  const slug = String(name)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "") // strip accents
    .replace(/[^a-z0-9\s-]/g, "")    // drop disallowed chars
    .trim()
    .replace(/\s+/g, "-")            // spaces -> hyphen
    .replace(/-+/g, "-")             // collapse repeats
    .replace(/^-+|-+$/g, "");        // trim leading/trailing
  return slug || "employee";
}

/** Build the canonical Storage folder for an employee. Always ends with "/". */
export function buildStorageFolderPath(fullName, employeeId) {
  return `employees/${slugifyName(fullName)}-${employeeId}/`;
}

export async function uploadFile(folderPath, slot, file) {
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const path = `${folderPath}${slot}/${safeName}`;
  const r = ref(storage, path);
  await uploadBytes(r, file, { contentType: file.type });
  const url = await getDownloadURL(r);
  return { path, url, name: file.name, size: file.size, type: file.type };
}

export async function uploadDataUrl(folderPath, slot, dataUrl, filename = "signature.png") {
  const res = await fetch(dataUrl);
  const blob = await res.blob();
  const path = `${folderPath}${slot}/${filename}`;
  const r = ref(storage, path);
  await uploadBytes(r, blob, { contentType: blob.type || "image/png" });
  const url = await getDownloadURL(r);
  return { path, url };
}
