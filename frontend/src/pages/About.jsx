import React from "react";
import LegalShell from "@/components/LegalShell";

export default function About() {
  return (
    <LegalShell title="About PNC UNIQUE LTD" subtitle="Company">
      <p>
        <strong>PNC UNIQUE LTD</strong> is a construction and property-services
        contractor operating across the United Kingdom. Our subcontractor
        network delivers refurbishment, maintenance and fit-out projects for
        public and private-sector clients.
      </p>
      <p>
        This Contractor Induction Portal is our digital replacement for the
        paper-and-spreadsheet on-boarding process that PNC UNIQUE LTD HR has
        run for many years. It exists so that new subcontractors can complete
        one secure form on their phone in about five minutes, and so that our
        site managers always have an up-to-date, auditable record of every
        contractor working under PNC UNIQUE LTD supervision.
      </p>

      <h2>What the Portal does</h2>
      <ul>
        <li>Collects the identity, business, insurance and right-to-work information required by CDM 2015 and HMRC.</li>
        <li>Captures a short medical and Hand-Arm Vibration Syndrome (HAVS) questionnaire required for site safety.</li>
        <li>Records that you have read the mandatory Health &amp; Safety Tool Box Talks and Site Rules.</li>
        <li>Produces a PDF induction record that PNC UNIQUE LTD HR reviews and either approves or requests amendments to.</li>
      </ul>

      <h2>What the Portal does not do</h2>
      <ul>
        <li>It never asks for a password or for banking security details.</li>
        <li>It does not process payments and does not sell or share your data with third parties beyond those listed in the Privacy Notice.</li>
        <li>It does not send unsolicited email — emails are only sent as part of the invitation, resubmission or approval workflow you have opted into.</li>
      </ul>

      <h2>How to reach us</h2>
      <p>
        Please see our <a href="/contact">Contact page</a> for the official ways
        to contact PNC UNIQUE LTD HR. All corporate identity details are printed
        in the footer of every page.
      </p>
    </LegalShell>
  );
}
