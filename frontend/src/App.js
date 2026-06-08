import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import AccessGate from "@/pages/AccessGate";
import Wizard from "@/pages/Wizard";
import Success from "@/pages/Success";
import AdminLogin from "@/pages/AdminLogin";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminInvitations from "@/pages/AdminInvitations";
import "@/App.css";

function App() {
  return (
    <div className="App font-body">
      <BrowserRouter>
        <Toaster
          position="top-center"
          richColors
          toastOptions={{
            style: { fontFamily: "'IBM Plex Sans', system-ui, sans-serif" },
          }}
        />
        <Routes>
          <Route path="/" element={<AccessGate />} />
          <Route path="/induction" element={<Wizard />} />
          <Route path="/success" element={<Success />} />
          <Route path="/admin" element={<AdminLogin />} />
          <Route path="/admin/employees" element={<AdminDashboard />} />
          <Route path="/admin/invitations" element={<AdminInvitations />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
