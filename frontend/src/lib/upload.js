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

export async function uploadFile(employeeId, slot, file) {
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const path = `employees/${employeeId}/${slot}/${safeName}`;
  const r = ref(storage, path);
  await uploadBytes(r, file, { contentType: file.type });
  const url = await getDownloadURL(r);
  return { path, url, name: file.name, size: file.size, type: file.type };
}

export async function uploadDataUrl(employeeId, slot, dataUrl, filename = "signature.png") {
  const res = await fetch(dataUrl);
  const blob = await res.blob();
  const path = `employees/${employeeId}/${slot}/${filename}`;
  const r = ref(storage, path);
  await uploadBytes(r, blob, { contentType: blob.type || "image/png" });
  const url = await getDownloadURL(r);
  return { path, url };
}
