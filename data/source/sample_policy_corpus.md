# Acme Corporation Enterprise Operations & Governance Policy Manual
Corpus Version: 2026.1

## Document: SEC-2026-01 (Information Security & Data Retention)
[doc_id: SEC-2026-01]
### Section 1: Customer Data Retention and Cryptographic Erasure
All customer transactional logs, user telemetry, and personally identifiable information (PII) must be retained in encrypted cold storage for exactly 7 years from the date of official account closure. After the 7-year retention window expires, cryptographic erasure must be executed across all storage replicas and logged in the immutable audit ledger within 48 hours.

### Section 2: Password, MFA, and Credential Governance
All employee accounts require multi-factor authentication (MFA) utilizing hardware FIDO2 security keys or approved authenticator applications. SMS-based 2FA is strictly prohibited for production environment access. Passwords must be at least 16 characters in length and are not subject to periodic calendar expiration unless a compromise is suspected.

### Section 3: Data Classification and Transmission Rules
Enterprise data is classified into four distinct tiers: Public, Internal, Confidential, and Restricted. Restricted data (including raw payment card data, cryptographic keys, and unredacted PII) may never be copied to local workstations or transmitted via email or unencrypted chat tools.

---

## Document: SEC-2026-02 (Cloud Infrastructure, Production Access, and Keys)
[doc_id: SEC-2026-02]
### Section 1: Production Infrastructure Access
Direct SSH access to production Kubernetes worker nodes and database clusters is prohibited. All engineering access must occur through ephemeral bastion sessions secured by identity-aware proxy and just-in-time (JIT) role elevation.

### Section 2: Secrets Management and Rotation
All API keys, database credentials, and service tokens must reside in HashiCorp Vault or AWS Secrets Manager. Hardcoded credentials in source repositories or configuration files will trigger immediate automated revocation and security ticket creation. API keys must be rotated every 90 days.

---

## Document: SEC-2026-03 (Security Incident Response & Escalation Protocol)
[doc_id: SEC-2026-03]
### Section 1: Incident Severity Classification
Security incidents are classified into three levels: Severity 1 (Critical: active breach of customer PII or critical infrastructure outage), Severity 2 (High: unauthorized access detected without confirmed exfiltration), and Severity 3 (Moderate/Low: policy deviation, phishing attempt, or isolated malware containment).

### Section 2: Severity 1 Escalation Timelines
For Severity 1 incidents, the Incident Commander must notify executive leadership, legal counsel, and the Data Protection Officer within 60 minutes of confirmation. External regulatory notification (where legally mandated by GDPR or CCPA) must be coordinated by Legal within 72 hours.

---

## Document: HR-2026-01 (Remote Work, Working Hours, and Collaboration)
[doc_id: HR-2026-01]
### Section 1: Core Collaboration Hours
Full-time remote employees must maintain availability for synchronous collaboration during core hours from 10:00 AM to 3:00 PM Eastern Time, Monday through Thursday. Fridays are designated as asynchronous deep-work days where meetings should be avoided.

### Section 2: Secondary Employment and Moonlighting
Employees may engage in non-competitive secondary employment provided it does not exceed 10 hours per week, does not utilize company hardware or intellectual property, and is pre-approved in writing by the VP of People Operations.

### Section 3: Intellectual Property and Inventions
All inventions, software code, designs, and patents developed by employees during their period of employment that relate to the company's current or prospective business remain the sole intellectual property of Acme Corporation.

---

## Document: HR-2026-02 (Home Office Equipment and Ergonomics)
[doc_id: HR-2026-02]
### Section 1: Standard Home Office Setup Stipend
Eligible full-time employees receive a one-time home office setup stipend of $1,500 upon hire to purchase approved desks, chairs, and monitors. An annual ergonomic upgrade stipend of $500 becomes available starting on their first employment anniversary. All purchased computing hardware remains company property.

### Section 2: Equipment Return upon Separation
Upon separation of employment (voluntary or involuntary), all company-issued laptops, security keys, and computing peripherals must be returned via pre-paid shipping container within 14 calendar days of the last working day.

---

## Document: HR-2026-03 (Code of Conduct, Ethics, and Whistleblower Protection)
[doc_id: HR-2026-03]
### Section 1: Gift Acceptance and Anti-Bribery Thresholds
Employees may not accept gifts, entertainment, meals, or hospitality from vendors, partners, or prospective clients exceeding $50 in cumulative value per calendar year. Any gift offer exceeding $50 must be formally reported to the Compliance Office within 5 business days.

### Section 2: Non-Retaliation and Whistleblower Hotline
Acme Corporation maintains a strict zero-tolerance policy against retaliation of any kind against employees who report suspected violations of law or policy in good faith. Reports can be submitted 24/7 anonymously via the Ethics Hotline at extension 8888 or via email at ethics@acmecorp.internal.

---

## Document: FIN-2024-03 (Legacy Travel & Expense Policy - SUPERSEDED)
[doc_id: FIN-2024-03]
### Status Notice: SUPERSEDED by FIN-2026-03 on January 1, 2026.
### Section 1: Domestic Per Diem Allowance (Historical 2024 - Inactive)
Employees traveling for business within the continental United States are allocated a flat per diem meal allowance of $65 per day. Receipts are not required for individual meals under $25.

### Section 2: Airfare Booking Rules (Historical 2024 - Inactive)
All domestic flights must be booked in economy class. Flight bookings exceeding $500 require prior approval from the department director.

---

## Document: FIN-2026-03 (Current Travel & Expense Policy - ACTIVE)
[doc_id: FIN-2026-03]
### Status Notice: ACTIVE as of January 1, 2026. Replaces FIN-2024-03.
### Section 1: Domestic Per Diem Allowance (Current 2026)
Employees traveling on authorized company business within the continental United States receive an increased meal and incidental per diem of $90 per day ($20 breakfast, $25 lunch, $45 dinner). Itemized electronic receipts are mandatory for all expense report submissions regardless of amount.

### Section 2: Airfare and Rail Booking Rules (Current 2026)
Domestic flights under 5 hours must be booked in economy or premium economy class. Domestic flights with continuous scheduled flight time exceeding 5 hours qualify for business class booking. All travel must be booked through the corporate travel portal at least 14 days in advance.

### Section 3: Expense Submission Window and Automatic Rejection
All expense reports must be submitted within 30 calendar days of the completion of business travel. Expenses submitted after 60 calendar days will be automatically rejected and ineligible for reimbursement without written CFO waiver.

---

## Document: FIN-2026-04 (Corporate Procurement and Vendor Governance)
[doc_id: FIN-2026-04]
### Section 1: Purchase Order Approval Thresholds
Department managers have signing authority for purchases up to $5,000. Department Directors may approve purchase orders up to $25,000. Purchases between $25,000 and $100,000 require VP and Finance approval. Contracts exceeding $100,000 require CFO signature.

### Section 2: Preferred Vendor Requirements
Software licenses, cloud subscriptions, and hardware purchases must be routed through approved preferred vendors. Non-catalog vendors require a completed security review and vendor assessment before payment processing.

---

## Document: OPS-2026-04 (Field Research Branch Special Guidelines - CONFLICTING)
[doc_id: OPS-2026-04]
### Section 1: Field Unit Equipment Policy (Conflict Clause)
Field research technicians assigned to the Autonomous Sensing Team are authorized an initial equipment and rugged hardware stipend of $3,500, which supersedes the standard HR-2026-02 home office stipend for field-deployed personnel.

### Section 2: Hazardous Environmental Operations
Field personnel operating in offshore or extreme weather environments must operate in pairs and check in every 2 hours via satellite transponder.
