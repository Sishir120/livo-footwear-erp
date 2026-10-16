# LIVO FOOTWEAR ERP — PHASE 6A: FRANCHISE & BRANCH ACCOUNTING SPECIFICATION

**Status:** ARCHITECTURAL SPECIFICATION & OPERATIONAL MODEL CONTRACT  
**Version:** 1.0.0  
**Phase:** 6A (Specification-Only)  
**Target Systems:** LIVO Footwear ERP Core Accounting & Multi-Location Architecture  
**Statutory Context:** Nepal Companies Act 2063, Value Added Tax Act 2052 (§14 Consignment & Branches), Income Tax Act 2058 (§33 Transfer Pricing)  

---

## 1. Structural Demarcation: Company Branch vs. Independent Franchise

To eliminate the common architectural failure of conflating physical custody with statutory ownership, the LIVO ERP design establishes a rigid structural distinction:

```
+---------------------------------------------------------------------------------------------------------+
|                                        LEGAL ENTITY (PARENT COMPANY)                                    |
|                              LIVO Footwear Industries Pvt. Ltd. (PAN: 60XXXXXXX)                        |
+---------------------------------------------------------------------------------------------------------+
                    |                                                             |
                    | 100% Owned Operating Division                               | Arm's-Length Commercial Contract
                    v                                                             v
+-------------------------------------------------------+   +-------------------------------------------------------+
|                COMPANY-OWNED BRANCH                   |   |                 INDEPENDENT FRANCHISE                 |
|  Example: Kathmandu Main Showroom (New Road)          |   |  Example: Pokhara Footwear Center Pvt. Ltd.           |
|                                                       |   |                                                       |
|  - Legal Persona: Same Legal Entity                   |   |  - Legal Persona: Separate Legal Entity               |
|  - PAN / VAT: Uses Parent PAN (Branch Suffix)         |   |  - PAN / VAT: Own Independent 9-digit PAN / VAT       |
|  - Inventory Title: 100% Owned by Parent Company      |   |  - Inventory Title: Transferred or Held as Agent      |
|  - Accounting Nature: Operating Segment / Profit Ctr  |   |  - Accounting Nature: External Debtor / Customer      |
|  - Internal Transfer: Stock Movement (No Revenue)     |   |  - Transfer: B2B Tax Invoice (Sale) or Consignment    |
|  - Invoicing: Retail Bill under Parent PAN            |   |  - Invoicing: Retail Bill under Franchisee's Own PAN  |
|  - Financial Output: Segmental P&L (Contribution)     |   |  - Financial Output: Customer Ledger & Statements     |
+-------------------------------------------------------+   +-------------------------------------------------------+
```

---

## 2. Company-Owned Branch Accounting Architecture

### 2.1 Branch Inventory Lifecycle & In-Transit Accounting
When finished footwear moves from the central factory in Birgunj to the Kathmandu showroom:
1. **Physical Transfer Dispatch (`DRAFT` $\to$ `IN_TRANSIT`):**
   - Accompanied by non-tax **Internal Delivery Challan** (`DC-2083-XXXXX`).
   - *Physical Ledger:* Factory Warehouse balance decreases; In-Transit bucket increases.
   - *Financial Ledger:*
     $$\text{DR } 1390 \text{ Inventory In-Transit Clearing} \quad \text{CR } 1350 \text{ Finished Goods - Factory}$$
     $$\text{Valuation Basis: Exact standard manufacturing cost in paisa (No margin or profit markup)}$$
2. **Physical Transfer Receipt (`IN_TRANSIT` $\to$ `RECEIVED`):**
   - Showroom manager inspects cartons and acknowledges receipt.
   - *Physical Ledger:* In-Transit bucket decreases; Showroom Warehouse balance increases.
   - *Financial Ledger:*
     $$\text{DR } 1360 \text{ Finished Goods - Showroom} \quad \text{CR } 1390 \text{ Inventory In-Transit Clearing}$$
3. **In-Transit Shortage / Transit Damage Resolution:**
   - If 2 pairs are damaged in transit:
     $$\text{DR } 5390 \text{ Inventory Shrinkage \& Transit Loss} \quad \text{CR } 1390 \text{ Inventory In-Transit Clearing}$$
   - If driver is contractually liable:
     $$\text{DR } 1280 \text{ Claims Receivable (Logistics Carrier)} \quad \text{CR } 1390 \text{ Inventory In-Transit Clearing}$$

### 2.2 Branch Sales, Retail Billing & Daily Cash Sweeping
1. **Retail Billing to Walk-in Consumers:**
   - Cashier issues retail tax invoice under Parent PAN with branch code (e.g., `INV-KTM-2083-00012`).
   - Financial entry:
     $$\text{DR } 1120 \text{ Cash on Hand - Kathmandu Showroom} \quad \text{CR } 4120 \text{ Footwear Sales - Retail Showroom}$$
     $$\text{CR } 2310 \text{ Value Added Tax Output Liability (13\%)}$$
   - COGS recognition:
     $$\text{DR } 5400 \text{ Cost of Goods Sold} \quad \text{CR } 1360 \text{ Finished Goods - Showroom}$$
2. **Daily Cash Sweep to Central Operating Bank:**
   - Showroom manager deposits physical cash into local branch of Nabil Bank:
     $$\text{DR } 1150 \text{ Operating Bank Account (Nabil Bank)} \quad \text{CR } 1120 \text{ Cash on Hand - Kathmandu Showroom}$$

### 2.3 Centrally Paid Branch Expenses
When headquarters pays branch lease, electricity, or internet bills:
- Rent payment:
  $$\text{DR } 6210 \text{ Retail Showroom Rent - Kathmandu} \quad [\text{branch\_id} = \text{KTM}]$$
  $$\text{CR } 1150 \text{ Operating Bank Account (Nabil Bank)}$$
  $$\text{CR } 2320 \text{ TDS Payable - Rent (10\%)}$$

### 2.4 Branch Contribution Margin & Profitability Statement
The General Ledger tags all revenue and expense lines with `branch_id`, producing an automated Branch P&L:

$$\begin{aligned}
&\text{Retail Sales Revenue (Kathmandu Showroom)} \\
- &\text{Cost of Goods Sold (Manufacturing Cost)} \\
\hline
= &\mathbf{\text{Branch Gross Profit}} \\
- &\text{Direct Branch Operating Expenses (Rent, Utilities, Staff Salaries)} \\
- &\text{Direct Showroom Marketing \& Freight} \\
\hline
= &\mathbf{\text{Branch Contribution Margin (Operating Profit)}}
\end{aligned}$$

---

## 3. Independent Franchise Accounting Architecture

Independent franchises operate under an external B2B commercial agreement. LIVO ERP supports two primary commercial models:

### 3.1 Model 1: Outright Wholesale Purchase (Recommended Default)
Under this model, the franchisee is an authorized wholesale distributor:
- **Title Passage:** Ownership of footwear passes to the franchisee upon dispatch from central factory.
- **Invoicing:** LIVO issues a statutory B2B Tax Invoice with 13% Nepal VAT.
- **Retail Sale:** The franchisee sells the shoes to end-consumers under their own independent company PAN, pricing at or above LIVO's Minimum Advertised Price (MAP).
- **Posting Sequence:**
  1. *Dispatch & Billing:*
     $$\text{DR } 1220 \text{ Accounts Receivable - Franchise Partner} \quad \text{CR } 4130 \text{ Footwear Sales - Franchise Outright}$$
     $$\text{CR } 2310 \text{ Value Added Tax Output Liability (13\%)}$$
     $$\text{DR } 5400 \text{ Cost of Goods Sold} \quad \text{CR } 1350 \text{ Finished Goods - Factory}$$
  2. *Settlement:*
     $$\text{DR } 1150 \text{ Operating Bank Account} \quad \text{CR } 1220 \text{ Accounts Receivable - Franchise Partner}$$

### 3.2 Model 2: Consignment Stock & Settlement Model
Under this model, goods are placed in the custody of the franchisee, but legal ownership remains with LIVO Footwear Industries Pvt. Ltd. until the franchisee makes a retail sale:
- **Statutory Guard (Nepal VAT Act §14):** Movement of goods on consignment does not trigger VAT upon dispatch, provided an official Consignment Challan (`CNG-`) is recorded and reported to IRD.
- **Posting Sequence:**
  1. *Dispatch to Consignment Warehouse:*
     $$\text{DR } 1370 \text{ Consignment Inventory - Franchise Stores} \quad \text{CR } 1350 \text{ Finished Goods - Factory}$$
     $$\text{Valuation: Standard manufacturing cost (NPR 0 revenue recognized)}$$
  2. *Monthly Certified Sales Settlement Report:*
     The franchisee submits a certified sales report showing 150 pairs sold at retail for NPR 300,000 (inclusive of VAT). Contractually, the franchisee retains a 20% retail margin and remits 80% (NPR 240,000) wholesale settlement.
  3. *LIVO Commercial Settlement Invoicing:*
     LIVO issues a statutory Tax Invoice for the wholesale settlement amount:
     $$\text{DR } 1220 \text{ Accounts Receivable - Franchise Partner} \quad \text{CR } 4140 \text{ Footwear Sales - Franchise Consignment}$$
     $$\text{CR } 2310 \text{ Value Added Tax Output Liability (13\%)}$$
     $$\text{DR } 5400 \text{ Cost of Goods Sold} \quad \text{CR } 1370 \text{ Consignment Inventory - Franchise}$$

### 3.3 Franchise Fees, Royalties & Security Deposits
1. **Franchise Security Deposit:**
   - Refundable cash deposit required prior to store opening:
     $$\text{DR } 1150 \text{ Operating Bank Account} \quad \text{CR } 2140 \text{ Franchise Security Deposits (Liability)}$$
2. **Annual Brand Royalty & Franchise License Fee:**
   - Fixed annual brand license fee of NPR 100,000 + 13% VAT:
     $$\text{DR } 1220 \text{ Accounts Receivable - Franchise Partner} \quad 113,000 \text{ NPR}$$
     $$\text{CR } 4210 \text{ Franchise Onboarding \& Royalty Fees} \quad 100,000 \text{ NPR}$$
     $$\text{CR } 2310 \text{ Value Added Tax Output Liability} \quad 13,000 \text{ NPR}$$

---

## 4. Multi-Entity / Intercompany Transactions (Sister Concerns)

If LIVO operates alongside sister manufacturing or distribution entities (e.g., a separate Sole Moulding Company or Retail Holding Company):
- **Transfer Pricing Guard:** Transactions must comply with Section 33 of Nepal Income Tax Act 2058 (Arm's-length pricing documentation).
- **Mandatory Intercompany Invoicing:** Goods transferred between separate legal entities **cannot move on internal challans**; they must be accompanied by full statutory Tax Invoices with 13% VAT.
- **Ledger Entries:**
  - *Selling Entity:* Dr. Intercompany Accounts Receivable, Cr. Sales Revenue, Cr. VAT Output.
  - *Purchasing Entity:* Dr. Raw Materials / Inventory, Dr. VAT Input, Cr. Intercompany Accounts Payable.
