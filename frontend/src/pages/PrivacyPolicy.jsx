import React from "react";
import LegalShell from "@/components/LegalShell";

export default function PrivacyPolicy() {
  return (
    <LegalShell title="Privacy Notice" subtitle="Legal">
      <p><em>Last reviewed: <span data-placeholder="privacy-review-date">[to be confirmed]</span></em></p>

      <h2>1. Who we are</h2>
      <p>
        <strong>PNC UNIQUE LTD</strong> (&quot;PNC&quot;, &quot;we&quot;, &quot;us&quot;) is the
        data controller for the personal information collected through this
        Contractor Induction Portal. Our registered office and contact details are
        published in the footer of every page.
      </p>
      <ul>
        <li>Company Number: <em data-placeholder="company-number">[to be confirmed]</em></li>
        <li>Registered Office: <em data-placeholder="registered-address">[to be confirmed]</em></li>
        <li>Data Protection Contact: <em data-placeholder="dpo-email">[to be confirmed]</em></li>
        <li>ICO Registration: <em data-placeholder="ico-registration">[to be confirmed]</em></li>
      </ul>

      <h2>2. What we collect and why</h2>
      <p>
        We only ask for information that is necessary to on-board you as an
        approved subcontractor and to satisfy our legal duties as a construction
        principal contractor. Specifically:
      </p>
      <ul>
        <li><strong>Identity data</strong> — full name, date of birth, National Insurance number, passport or national identity document, right-to-work share code.</li>
        <li><strong>Contact data</strong> — home address, postcode, telephone, personal email, emergency contact.</li>
        <li><strong>Business data</strong> — company name, UTR, VAT number, business bank account and sort code.</li>
        <li><strong>Health data (special category)</strong> — a short medical questionnaire and a Hand-Arm Vibration Syndrome (HAVS) declaration required for site safety.</li>
        <li><strong>Compliance</strong> — confirmation that you have read the Health &amp; Safety Tool Box Talks and Site Rules.</li>
        <li><strong>Signature</strong> — a typed and drawn digital signature confirming the accuracy of your submission.</li>
      </ul>

      <h2>3. Lawful basis</h2>
      <ul>
        <li><strong>Contract</strong> (Art. 6(1)(b) UK GDPR) — to on-board you as a subcontractor and administer payments.</li>
        <li><strong>Legal obligation</strong> (Art. 6(1)(c)) — to satisfy right-to-work checks, HMRC reporting and CDM 2015 duties.</li>
        <li><strong>Employment / social security context</strong> (Art. 9(2)(b)) — for the health-related questions above.</li>
        <li><strong>Legitimate interests</strong> (Art. 6(1)(f)) — to prevent fraud and to keep an auditable record of induction.</li>
      </ul>

      <h2>4. Who we share it with</h2>
      <p>Your information is not sold and is only shared with:</p>
      <ul>
        <li>PNC UNIQUE LTD HR and directly-relevant site management staff.</li>
        <li>Our infrastructure providers (Google Firebase, Cloud Run) under written processing agreements.</li>
        <li>Our transactional email provider (Resend) solely to deliver the notification emails you receive.</li>
        <li>HMRC and other statutory bodies where we are legally required to disclose the data.</li>
      </ul>

      <h2>5. Where it is stored</h2>
      <p>
        Records are held in Google Firebase (Firestore + Cloud Storage) in the
        <strong> europe-west2 (London)</strong> region. Access is restricted to
        authorised PNC personnel and audited in Google Cloud Run logs.
      </p>

      <h2>6. How long we keep it</h2>
      <p>
        We retain your induction record for the duration of your engagement with
        PNC and for a minimum of <em data-placeholder="retention-period">[retention period to be confirmed — typically 6 years for tax and CDM purposes]</em> after your last day worked. After that period the record is deleted or fully anonymised.
      </p>

      <h2>7. Your rights</h2>
      <p>You can, at any time and free of charge, request to:</p>
      <ul>
        <li>Access a copy of the personal data we hold about you.</li>
        <li>Rectify inaccurate personal data.</li>
        <li>Erase your data, subject to our statutory retention obligations.</li>
        <li>Restrict or object to certain processing.</li>
        <li>Port your data to another controller.</li>
        <li>Withdraw consent where processing was consent-based.</li>
      </ul>
      <p>
        Please make requests via <em data-placeholder="dpo-email">[data protection contact to be confirmed]</em>.
        You may also complain to the UK Information Commissioner&#39;s Office
        (<a href="https://ico.org.uk" target="_blank" rel="noreferrer">ico.org.uk</a>, 0303 123 1113).
      </p>

      <h2>8. Cookies &amp; local storage</h2>
      <p>
        The portal does not use any advertising or analytics cookies. It uses
        your browser&#39;s <strong>localStorage</strong> only to auto-save your
        induction form so you can leave and come back without losing progress,
        and <strong>sessionStorage</strong> to keep you signed in for the length
        of a single visit. Both are cleared when your induction is submitted.
      </p>

      <h2>9. Changes to this notice</h2>
      <p>
        We will revise this notice as our processing changes. The current
        version is always available at this URL. Material changes will be
        notified by email to contractors with active accounts.
      </p>
    </LegalShell>
  );
}
