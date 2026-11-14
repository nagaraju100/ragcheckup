# Tier 2 Support Runbook

**Effective Date:** 2024-02-01
**Version:** 2024.1
**Classification: Internal — Do Not Distribute**

## Scope

This runbook covers advanced customer issues escalated from Tier 1 support. Tier 2 agents have additional CRM permissions and direct access to warehouse, logistics, and IT systems.

## Ticket Handling

### Priority Levels

| Priority | Response Time | Resolution Target | Example |
|---|---|---|---|
| P1 — Critical | 15 minutes | 4 hours | Safety issue, security breach |
| P2 — High | 1 hour | 24 hours | Large order issues, multiple affected customers |
| P3 — Medium | 4 hours | 3 business days | Individual product issues |
| P4 — Low | 24 hours | 7 business days | General inquiries, feature requests |

### Escalation from Tier 1

Tier 1 agents escalate tickets using the escalation form in the CRM. Each escalation must include:
- Customer name and order number
- Detailed description of the issue
- All actions taken by Tier 1
- Customer impact assessment
- Recommended resolution (if any)

## Common Issue #1: Large Order Fulfillment Failure

**Error Code:** ERR-LOG-001
**Ticket Pattern:** LOG-XXXX-XXXX

When an order exceeds the available inventory (inventory discrepancy):
1. Check warehouse system (WMS-2024) for actual stock
2. If stock exists: expedite to customer (free shipping)
3. If stock does not exist:
   a. Notify customer within 24 hours
   b. Offer equivalent product (with 15% discount) or full refund
   c. Provide written apology and 10% courtesy credit

## Common Issue #2: Multiple Customer Reports of Same Product

**Error Code:** ERR-PRD-002

When 3 or more customers report the same product issue within 48 hours:
1. Immediately flag the product in the CRM as "Under Investigation"
2. Pull remaining inventory from stores and warehouse
3. Notify Product Development team (email: pd@northwindgear.com)
4. Issue a product notice to all active orders containing the affected SKU
5. Process all related returns/refunds (no restocking fee)

## Common Issue #3: International Shipping Dispute

**Error Code:** ERR-SHP-003
**Ticket Pattern:** SHP-INTL-XXXX

When a customer disputes international customs charges:
1. Verify the shipping destination and declared value
2. If the value was under-declared (any case):
   a. Apologize sincerely
   b. Provide a 20% discount on the order as goodwill
   c. Note: We cannot refund customs charges as they are government-imposed
3. If the value was correctly declared:
   a. Provide the customer with the customs documentation
   b. Offer 10% discount as goodwill

## Common Issue #4: IT System Access — After Hours

**Error Code:** ERR-IT-001
**Ticket Pattern:** IT-SEC-XXXX

For after-hours IT access issues (account lockout, suspected compromise):
1. Contact IT Security Hotline: 1-800-555-0555
2. Verify caller identity through security questions
3. Temporary account lock (15 minutes) if more than 3 failed login attempts
4. Password reset via secret question (if set) or HR verification
5. Document all after-hours access in the IT Security Log (DOC-IT-2024-001)

## Common Issue #5: Store Return Dispute

**Error Code:** ERR-RET-002
**Ticket Pattern:** RET-XXXX-XXXX

When a customer purchased online but is returned at a retail store:
1. Verify original online order number in the CRM
2. Check store return records
3. If the return was processed correctly:
   a. Refund to original payment method (may take 5–7 additional business days)
4. If the return was NOT processed (system failure):
   a. Process the return from your terminal
   b. Issue a courtesy credit of 5% for the inconvenience

## Documentation Requirements

All Tier 2 resolutions must include:
- Root cause analysis (if applicable)
- Corrective action taken
- Follow-up required (and timeframe)
- Any system changes recommended

## Contact for Tier 2 Support

- Phone: 1-800-555-0199 (option 6 — Tier 2)
- Email: tier2-support@northwindgear.com
- CRM: Northwind CRM (Tier 2 access level)
