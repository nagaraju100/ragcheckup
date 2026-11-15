IT Security Policy
2024-01-15
V2024.1

This policy applies to all employees, contractors, and third-party vendors accessing Northwind Gear's information systems. Compliance is mandatory.

## Access Control

All users must use company-issued devices for work. Personal devices may be used only through the approved Mobile Device Management (MDM) program. Account access is granted on a need-to-know basis and reviewed quarterly.

## Password Requirements

- Minimum 12 characters with upper, lower, numbers, and symbols
- No reuse of the last 10 passwords
- Automatic lock after 15 minutes of inactivity
- Mandatory change every 90 days
- Cannot contain company name, personal names, or common words

## Multi-Factor Authentication

All employees must enable MFA on:
- Company email (Microsoft 365)
- Cloud services (AWS, GCP)
- Version control (GitHub)
- Internal tools (Slack, Jira, Confluence)
- HR portal
- Customer database (Salesforce)

MFA bypass requires VP approval and is logged. Bypasses are reviewed monthly by the Security team.

## Device Management

All company devices must have:
- Full-disk encryption (BitLocker or FileVault)
- Endpoint detection and response (EDR) agent
- Up-to-date antivirus definitions
- Automatic OS patching enabled
- Remote wipe capability

Lost or stolen devices must be reported to IT within 1 hour. Failure to report within 24 hours may result in disciplinary action.

## Network Security

- VPN required for all remote access
- No direct database access from personal networks
- Wireless access must use WPA3 encryption
- Guest networks are air-gapped from internal systems
- Network segmentation isolates PCI-scoped systems

## Email Security

- All external emails are scanned for malware
- Phishing awareness training quarterly
- Report suspicious emails via the "Report Phishing" button
- No forwarding of company-internal emails to personal accounts
- Email retention policy: 7 years for financial communications

## Data Classification

All company data must be classified:
- Public: Marketing materials, press releases
- Internal: Employee directories, meeting notes
- Confidential: Customer data, financial records, source code
- Restricted: Patent applications, merger details, PII

Employees must handle Confidential and Restricted data according to the Data Handling Procedures (DOC-2024-001).

## Incident Response

Security incidents must be reported immediately:
- Security Operations Center: soc@northwindgear.com
- Hotline: 1-800-555-0555 (24/7)
- Response SLA: 1 hour for Critical, 4 hours for High, 24 hours for Medium severity

The Security Incident Response Team (SIRT) follows the NIST framework for investigation, containment, and recovery.

## Vendor Security Assessment

All third-party vendors with access to company systems must undergo a security assessment annually. High-risk vendors (handling PII or financial data) undergo bi-annual assessment. Assessment results are stored in the Vendor Security Portal.

## Employee Offboarding

When an employee leaves (voluntary or involuntary):
- All access revoked within 1 hour (Critical employees)
- All access revoked within 24 hours (Standard employees)
- Company device collected within 48 hours
- Data handover documented and verified
- Email forwarding disabled immediately
- Access to shared drives revoked

## Physical Security

- Badges required for all areas
- Visitor badges must be escorted at all times
- Clean desk policy: no documents left unattended
- Secure destruction of sensitive materials via cross-cut shredders
- Server room access logged and reviewed monthly

## Compliance Audit

Northwind Gear undergoes annual SOC 2 Type II audits. Department heads are responsible for ensuring their teams comply with this policy. Non-compliance may result in access revocation, disciplinary action, or termination.
