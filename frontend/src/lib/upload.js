import { ref, uploadBytes } from "firebase/storage";
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
 *   lower-case, spaces → hyphens, drop everything except a-z, 0-9, hyphen,
 *   collapse repeats, trim ends.
 */
export function slugifyName(name) {
  if (!name) return "employee";
  const slug = String(name)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "employee";
}

/** Canonical Storage folder for an employee. Always ends with "/". */
export function buildStorageFolderPath(fullName, employeeId) {
  return `employees/${slugifyName(fullName)}-${employeeId}/`;
}

/**
 * Upload a file to Cloud Storage. The browser has WRITE permission only —
 * read permission is denied by security rules, so we no longer call
 * getDownloadURL from the client. The FastAPI backend mints a download-token
 * URL server-side after receiving the path.
 */
export async function uploadFile(folderPath, slot, file) {
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const path = `${folderPath}${slot}/${safeName}`;
  const r = ref(storage, path);
  await uploadBytes(r, file, { contentType: file.type });
  return { path, name: file.name, size: file.size, type: file.type };
}

export async function uploadDataUrl(folderPath, slot, dataUrl, filename = "signature.png") {
  const res = await fetch(dataUrl);
  const blob = await res.blob();
  const path = `${folderPath}${slot}/${filename}`;
  const r = ref(storage, path);
  await uploadBytes(r, blob, { contentType: blob.type || "image/png" });
  return { path };
}
