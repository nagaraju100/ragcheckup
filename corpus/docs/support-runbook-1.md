# Tier 1 Support Runbook

**Effective Date:** 2024-02-01
**Version:** 2024.1
**Classification: Internal — Do Not Distribute**

## Scope

This runbook covers common customer issues handled by Tier 1 support. Escalate any issue not covered here to Tier 2 (see Support Runbook 2).

## Getting Started

### System Login

All support agents must log in to the CRM system (Salesforce) using their company credentials. Default password is sent to the agent's work email. Change your password on first login.

### Ticket Queue

New tickets are assigned automatically based on product category. Check your queue every 15 minutes during business hours. Target response time: 4 hours for standard, 1 hour for urgent.

## Common Issue #1: Order Not Received

**Error Code:** ERR-SHP-001
**Ticket Pattern:** ORD-XXXX-XXXX

1. Verify order number in CRM
2. Check shipping status (shipped = tracking available, processing = hasn't shipped)
3. If shipped, provide tracking number to customer
4. If not shipped, offer to:
   a. Expedite shipping (no charge if within 48 hours of order)
   b. Cancel and refund
5. Log resolution in CRM

## Common Issue #2: Wrong Item Received

**Error Code:** ERR-SHP-002
**Ticket Pattern:** ORD-XXXX-XXXX

1. Verify order details and shipped items
2. Confirm the error with customer photos
3. Arrange return of wrong item (prepaid label provided)
4. Ship correct item (expedited, no charge)
5. Log resolution in CRM

## Common Issue #3: Product Defect

**Error Code:** ERR-PRD-001

1. Collect product SKU from label
2. Request photos of the defect
3. Determine if defect is covered under warranty (see Warranty Policy)
4. If covered:
   - Process replacement (free shipping both ways)
   - Provide prepaid return label
   - If not covered: offer repair option at a discount

## Common Issue #4: Return / Refund Request

**Error Code:** ERR-RET-001

1. Verify order date (within 30-day window, 45 days for 2025 policy)
2. Confirm item is not final sale
3. Check original payment method
4. Process return:
   a. Generate prepaid shipping label
   b. Customer ships item within 14 days of label receipt
   c. Refund processed 3–5 business days after warehouse receipt
5. Log resolution in CRM

## Common Issue #5: Account Access Problems

**Error Code:** ERR-ACC-001
**Ticket Pattern:** ACC-XXXX-XXXX

1. Verify customer identity (name, email, last 4 digits of payment method)
2. Reset password via CRM (send reset link to registered email)
3. If customer cannot access registered email:
   a. Escalate to IT Security (Ticket: IT-SEC)
   b. Do NOT provide account details to unverified callers

## Escalation Guide

| Issue | Tier 2 Contact | Ticket Reference |
|---|---|---|
| Product defect over $200 | Tier 2 Product Specialist | T2-PROD |
| Suspected fraud | Security Team | IT-SEC |
| Shipping delay over 14 days | Logistics Manager | LOG-001 |
| Store return dispute | Store Manager + HQ | RET-STD |
| Warranty claim denied (appeal) | Warranty Team | WTY-Appeal |
| IT system access issue | IT Helpdesk | IT-HELP |

## Contact for Tier 1 Support

- Phone: 1-800-555-0199 (option 1)
- Email: support@northwindgear.com
- CRM: Northwind CRM (internal)
