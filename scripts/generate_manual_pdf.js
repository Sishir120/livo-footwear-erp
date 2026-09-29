const puppeteer = require('../frontend/node_modules/puppeteer-core');
const fs = require('fs');
const path = require('path');

const DOCS_DIR = path.resolve(__dirname, '../docs');
const SCREENSHOTS_DIR = path.resolve(__dirname, '../docs/screenshots');
const ARTIFACT_DIR = 'C:/Users/sishi/.gemini/antigravity-ide/brain/1849f93e-c4c7-4ece-b3df-2d5c85fa991d';

function getBase64Image(filename) {
  const filePath = path.join(SCREENSHOTS_DIR, filename);
  if (!fs.existsSync(filePath)) {
    console.warn(`File not found: ${filePath}`);
    return '';
  }
  const ext = path.extname(filename).replace('.', '');
  const data = fs.readFileSync(filePath).toString('base64');
  return `data:image/${ext};base64,${data}`;
}

const images = {
  screen_01: getBase64Image('screen_01_login_gateway.png'),
  screen_02: getBase64Image('screen_02_global_appshell_and_nav.png'),
  screen_03: getBase64Image('screen_03_production_batch_terminal.png'),
  screen_04: getBase64Image('screen_04_stock_ledger_matrix.png'),
  screen_05: getBase64Image('screen_05_stock_card_modal.png'),
  screen_06: getBase64Image('screen_06_stock_adjustment_modal.png'),
  screen_07: getBase64Image('screen_07_wholesale_dispatch_invoice_form.png'),
  screen_08: getBase64Image('screen_08_schedule_5_printable_tax_invoice.png'),
  screen_09: getBase64Image('screen_09_party_aging_worklist.png'),
  screen_10: getBase64Image('screen_10_party_statement_dispute_modal.png'),
  screen_11: getBase64Image('screen_11_supervisor_exception_cockpit.png'),
  screen_12: getBase64Image('screen_12_settings_and_diagnostics.png'),
  screen_13: getBase64Image('screen_13_auditor_viewer_read_only.png'),
  seq_A1: getBase64Image('seq_A1_model_and_line_selection.png'),
  seq_A2: getBase64Image('seq_A2_rapid_numeric_entry.png'),
  seq_A3: getBase64Image('seq_A3_live_strip_variance_update.png'),
  seq_B1: getBase64Image('seq_B1_excessive_dispatch_input.png'),
  seq_C1: getBase64Image('seq_C1_credit_limit_hold_badge.png')
};

const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LIVO Footwear ERP — Factory Operations Manual & Implementation Playbook</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap');

  @page {
    size: A4;
    margin: 16mm 14mm 16mm 14mm;
    @top-right {
      content: "LIVO ERP Factory Manual • Ver 2.4";
      font-family: 'Inter', sans-serif;
      font-size: 8pt;
      color: #94A3B8;
      font-weight: 600;
    }
    @bottom-center {
      content: "Page " counter(page) " of " counter(pages);
      font-family: 'Inter', sans-serif;
      font-size: 8.5pt;
      color: #64748B;
      font-weight: 600;
    }
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #0F172A;
    background-color: #FFFFFF;
    margin: 0;
    padding: 0;
    font-size: 9.5pt;
    line-height: 1.5;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* Page Break Helpers */
  .page-break {
    page-break-before: always;
  }
  .avoid-break {
    page-break-inside: avoid;
  }

  /* Typography */
  h1, h2, h3, h4, h5 {
    color: #0F172A;
    font-weight: 800;
    margin-top: 0;
    letter-spacing: -0.02em;
  }
  h1 { font-size: 20pt; line-height: 1.2; margin-bottom: 8pt; color: #1E3A8A; }
  h2 { font-size: 14pt; border-bottom: 2px solid #E2E8F0; padding-bottom: 4pt; margin-top: 14pt; margin-bottom: 8pt; color: #0F172A; }
  h3 { font-size: 11pt; margin-top: 10pt; margin-bottom: 4pt; color: #1E293B; }
  p { margin: 0 0 6pt 0; color: #334155; }

  /* Badges & Pills */
  .badge {
    display: inline-block;
    padding: 1.5pt 5pt;
    border-radius: 3pt;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .badge-blue { background: #EFF6FF; color: #1E3A8A; border: 1px solid #BFDBFE; }
  .badge-green { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
  .badge-orange { background: #FFFBEB; color: #9A3412; border: 1px solid #FDE68A; }
  .badge-red { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
  .badge-slate { background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }

  .callout-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16pt;
    height: 16pt;
    border-radius: 50%;
    background: #DC2626;
    color: #FFFFFF;
    font-weight: 900;
    font-size: 8.5pt;
    margin-right: 4pt;
    vertical-align: middle;
  }

  kbd {
    display: inline-block;
    padding: 1.5pt 4pt;
    font-size: 8pt;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 3pt;
    box-shadow: 0 1px 1px rgba(0,0,0,0.1);
    color: #0F172A;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin-bottom: 8pt;
  }
  th {
    background: #F8FAFC;
    color: #475569;
    font-weight: 700;
    text-align: left;
    padding: 5pt 7pt;
    border-top: 1px solid #CBD5E1;
    border-bottom: 1px solid #CBD5E1;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  td {
    padding: 4.5pt 7pt;
    border-bottom: 1px solid #E2E8F0;
    color: #334155;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background: #FAFAFA;
  }

  /* Visual Screenshot Cards */
  .screenshot-card {
    border: 1px solid #CBD5E1;
    border-radius: 4pt;
    background: #FFFFFF;
    padding: 4pt;
    margin: 8pt 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    page-break-inside: avoid;
  }
  .screenshot-card img {
    width: 100%;
    height: auto;
    display: block;
    border-radius: 3pt;
    border: 1px solid #E2E8F0;
  }
  .screenshot-caption {
    font-size: 8pt;
    color: #64748B;
    margin-top: 4pt;
    padding: 0 4pt;
    display: flex;
    justify-content: space-between;
    font-weight: 600;
  }

  /* Persona Card */
  .persona-box {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-left: 4px solid #1E3A8A;
    border-radius: 3pt;
    padding: 8pt 10pt;
    margin: 8pt 0;
  }
  .persona-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4pt;
  }
  .persona-title {
    font-size: 10.5pt;
    font-weight: 800;
    color: #0F172A;
  }

  /* Info / Alert Boxes */
  .info-box {
    border-radius: 3pt;
    padding: 6pt 8pt;
    margin: 6pt 0;
    font-size: 8.5pt;
  }
  .info-box-tip { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E3A8A; }
  .info-box-warn { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; }
  .info-box-danger { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }

  /* Cover Page */
  .cover-container {
    height: 92vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    border: 3px double #CBD5E1;
    padding: 28pt;
    background: #FFFFFF;
    box-sizing: border-box;
  }
  .cover-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #0F172A;
    padding-bottom: 12pt;
  }
  .cover-company {
    font-size: 16pt;
    font-weight: 900;
    color: #0F172A;
    letter-spacing: -0.02em;
  }
  .cover-meta {
    font-size: 9pt;
    color: #475569;
    text-align: right;
    font-weight: 600;
  }
  .cover-title-block {
    margin: 30pt 0;
  }
  .cover-supertitle {
    font-size: 11pt;
    font-weight: 800;
    text-transform: uppercase;
    color: #1E3A8A;
    letter-spacing: 0.1em;
    margin-bottom: 8pt;
  }
  .cover-title {
    font-size: 28pt;
    font-weight: 900;
    color: #0F172A;
    line-height: 1.15;
    margin-bottom: 12pt;
    letter-spacing: -0.03em;
  }
  .cover-subtitle {
    font-size: 12pt;
    color: #334155;
    line-height: 1.45;
    max-width: 90%;
  }
  .cover-footer {
    border-top: 1px solid #E2E8F0;
    padding-top: 12pt;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12pt;
    font-size: 8.5pt;
  }
  .cover-footer-col strong {
    display: block;
    color: #0F172A;
    margin-bottom: 2pt;
    text-transform: uppercase;
    font-size: 8pt;
    letter-spacing: 0.03em;
  }

  /* Grid of Steps */
  .step-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8pt;
    margin: 8pt 0;
  }
  .step-card {
    border: 1px solid #E2E8F0;
    border-radius: 3pt;
    padding: 6pt;
    background: #F8FAFC;
  }
  .step-card img {
    width: 100%;
    border-radius: 2pt;
    margin-top: 4pt;
    border: 1px solid #CBD5E1;
  }
</style>
</head>
<body>

<!-- ========================================================================= -->
<!-- COVER PAGE -->
<!-- ========================================================================= -->
<div class="cover-container">
  <div class="cover-header">
    <div>
      <div class="cover-company">LIVO FOOTWEAR INDUSTRIES PVT. LTD.</div>
      <div style="font-size: 8.5pt; color: #64748B; margin-top: 2pt;">Kathmandu & Biratnagar Factory Deployment • IRD PAN: 609823412</div>
    </div>
    <div class="cover-meta">
      <span class="badge badge-blue">Official SOP Release</span><br>
      <span style="font-size: 8pt; color: #64748B;">Document Ref: LIVO-SOP-2026-V2.4</span>
    </div>
  </div>

  <div class="cover-title-block">
    <div class="cover-supertitle">Standard Operating Procedure & Training Manual</div>
    <div class="cover-title">LIVO FOOTWEAR ERP<br>FACTORY OPERATIONS MANUAL & CLIENT IMPLEMENTATION PLAYBOOK</div>
    <div class="cover-subtitle">
      A complete, plain-language visual operations guide for shop-floor data clerks, warehouse storekeepers, wholesale dispatchers, factory supervisors, and statutory auditors.
    </div>
  </div>

  <div class="cover-footer">
    <div class="cover-footer-col">
      <strong>Target Hardware</strong>
      Factory Terminals (1920×1080)<br>
      Shop-Floor Tablets (1280×800)<br>
      High-Speed Barcode Readers
    </div>
    <div class="cover-footer-col">
      <strong>Statutory Authority</strong>
      Inland Revenue Dept (IRD) Nepal<br>
      Schedule-5 Tax Invoicing (अनुसूची-५)<br>
      13% VAT Exact Paisa Math
    </div>
    <div class="cover-footer-col">
      <strong>Deployment Details</strong>
      Production Version: 2.4<br>
      Offline Architecture: IndexedDB<br>
      Effective Date: September 2026
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- TABLE OF CONTENTS & PERSONA OVERVIEW -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h2>Table of Contents</h2>
<table>
  <thead>
    <tr>
      <th style="width: 15%;">Chapter</th>
      <th style="width: 55%;">Topic & Core Procedures</th>
      <th style="width: 30%;">Primary Factory Persona</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Chapter 1</strong></td>
      <td>Getting Started & Computer Setup (Implementation Guide)</td>
      <td>All Plant Staff & IT Technicians</td>
    </tr>
    <tr>
      <td><strong>Chapter 2</strong></td>
      <td>The Factory Screen Layout (Every Icon, Badge & Button Explained)</td>
      <td>Shop-Floor Operators & Supervisors</td>
    </tr>
    <tr>
      <td><strong>Chapter 3</strong></td>
      <td>Production Batch Entry (How Ramesh Enters Finished Shoes Without a Mouse)</td>
      <td><strong>Ramesh</strong> (Shop-Floor Data Clerk)</td>
    </tr>
    <tr>
      <td><strong>Chapter 4</strong></td>
      <td>Stock Ledger & Sizing Matrix (How Sita Audits Physical Pairs on Racks)</td>
      <td><strong>Sita</strong> (Warehouse Storekeeper)</td>
    </tr>
    <tr>
      <td><strong>Chapter 5</strong></td>
      <td>Controlled Stock Corrections (Physical Counting Reconciliations & Spoilage)</td>
      <td>Floor Supervisor & Sita</td>
    </tr>
    <tr>
      <td><strong>Chapter 6</strong></td>
      <td>Wholesale Dispatch & Nepal Tax Invoices (Carton Math & Schedule-5 Billing)</td>
      <td><strong>Sita</strong> (Dispatch & Billing Clerk)</td>
    </tr>
    <tr>
      <td><strong>Chapter 7</strong></td>
      <td>Party Accounts & Customer Aging (Managing Credit Limits & Cash Receipts)</td>
      <td>Accountant & Credit Controller</td>
    </tr>
    <tr>
      <td><strong>Chapter 8</strong></td>
      <td>Auditor Read-Only Mode (How Hari Prasad Verifies Books & Exports Data)</td>
      <td><strong>Hari Prasad</strong> (Chartered Auditor)</td>
    </tr>
    <tr>
      <td><strong>Chapter 9</strong></td>
      <td>10-Second Quick Troubleshooting Guide (Cold Boots, Sync & Stock Errors)</td>
      <td>All Shift Staff & Dispatchers</td>
    </tr>
  </tbody>
</table>

<h2>Factory Personas: "A Day on the Factory Floor"</h2>
<p>To eliminate confusing technical jargon, all procedures in this manual are explained through the real-life tasks of three dedicated employees at Livo Footwear Industries:</p>

<div class="persona-box">
  <div class="persona-header">
    <span class="persona-title">1. Ramesh — Shop-Floor Data Entry Clerk</span>
    <span class="badge badge-blue">Line 1 & 2 Assembly Plant</span>
  </div>
  <p><strong>Environment & Habits:</strong> Works on a dusty, brightly lit assembly floor near the conveyor lines. Uses a standard keyboard with a dedicated numeric keypad. He hates using the mouse because picking it up slows down batch logging.</p>
  <p><strong>Daily Mission:</strong> Record 400 to 800 finished pairs per shift across Continental Paris Points (Sizes 32–43). He relies on <kbd>Tab</kbd>, <kbd>Enter</kbd>, and <kbd>Ctrl+Enter</kbd> to log batches in seconds, even if the plant Wi-Fi drops momentarily.</p>
</div>

<div class="persona-box">
  <div class="persona-header">
    <span class="persona-title">2. Sita — Warehouse Storekeeper & Wholesale Dispatcher</span>
    <span class="badge badge-green">Finished Goods Warehouse & Loading Dock</span>
  </div>
  <p><strong>Environment & Habits:</strong> Meticulous, counts actual cardboard cartons on flatbed delivery trucks, inspects size ratios, and checks that every bill strictly complies with Nepal Inland Revenue Department (IRD) regulations.</p>
  <p><strong>Daily Mission:</strong> Dispatch master cartons to wholesale dealers in New Road and Narayangarh. She uses the <code>1 Carton = 12 Pairs</code> carton calculator, confirms Buyer PAN numbers, and prints statutory Schedule-5 Tax Invoices.</p>
</div>

<div class="persona-box">
  <div class="persona-header">
    <span class="persona-title">3. Hari Prasad — Statutory Auditor & Tax Consultant</span>
    <span class="badge badge-slate">Internal Audit & Accounts Office</span>
  </div>
  <p><strong>Environment & Habits:</strong> Skeptical, detail-oriented, checks balance arithmetic down to the exact paisa, ensures no staff member has altered historical records, and audits customer credit limits.</p>
  <p><strong>Daily Mission:</strong> Log in using the read-only <code>viewer_demo</code> profile to examine stock movements, inspect overdue accounts receivable (31–60d, 61–90d, >90d), verify dispute notes, and export CSV audit reports.</p>
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 1: GETTING STARTED & COMPUTER SETUP -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 1: Getting Started & Computer Setup</h1>
<p>This implementation chapter guides IT technicians and floor supervisors in setting up factory terminals and explaining the login boundary.</p>

<h3>1.1 Hardware & Browser Requirements</h3>
<ul>
  <li><strong>Factory PC / Shop-Floor Monitor:</strong> 1920×1080 resolution recommended. Works smoothly on older Core i3/i5 computers with 4GB RAM running Windows 10 or 11.</li>
  <li><strong>Shop-Floor Tablets:</strong> 10-inch Android or iPad tablets (1280×800 minimum resolution) using Google Chrome.</li>
  <li><strong>Supported Browsers:</strong> Google Chrome (Version 110+) or Microsoft Edge. Do not use Internet Explorer.</li>
  <li><strong>Barcode Scanners:</strong> Standard USB or Bluetooth HID barcode scanners (emulating keyboard strokes with a trailing <code>Enter</code>).</li>
</ul>

<h3>1.2 Creating a Desktop One-Click Icon</h3>
<ol>
  <li>Open Google Chrome and navigate to: <code>https://livo-footwear-erp.vercel.app</code></li>
  <li>Click the Chrome menu (<strong style="font-size: 11pt;">⋮</strong>) at the top-right corner.</li>
  <li>Select <strong>Save and Share</strong> &rarr; <strong>Create Shortcut...</strong></li>
  <li>Name the shortcut <strong>"LIVO Footwear ERP"</strong>, check the box <em>"Open as window"</em>, and click <strong>Create</strong>. An icon will appear on the desktop that opens like a clean native desktop application without address bars.</li>
</ol>

<h3>1.3 Logging In: The Authentication Gateway</h3>
<div class="screenshot-card">
  <img src="${images.screen_01}" alt="Screen 01 - Authentication Gateway">
  <div class="screenshot-caption">
    <span>SCREEN 01: Authentication Gateway (/login)</span>
    <span>Callouts: [1] Username [2] Password [3] Show/Hide [4] EN/नेपाली [5] Demo Personas</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 35%;">Factory Purpose</th>
      <th style="width: 30%;">Operator Action</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Username Input</strong></td>
      <td>Identifies operator identity (e.g., <code>admin_demo</code> or <code>viewer_demo</code>).</td>
      <td>Type operator ID or click Quick Persona.</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Password Input</strong></td>
      <td>Secures terminal with encrypted argon2id/bcrypt token.</td>
      <td>Type your password securely.</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Show/Hide Password</strong></td>
      <td>Reveals hidden characters to prevent typo lockouts in noisy plants.</td>
      <td>Click the Eye icon to view password in plain text.</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Language Toggle (EN / नेपाली)</strong></td>
      <td>Switches between Pure Industrial English and Nepali Factory Vernacular.</td>
      <td>Click <code>नेपाली</code> for local shop-floor terms or <code>EN</code> for English.</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Quick Persona Buttons</strong></td>
      <td>One-click credential fill for training and testing drills.</td>
      <td>Click <code>Admin Operator</code> or <code>Auditor Viewer</code>.</td>
    </tr>
  </tbody>
</table>

<div class="info-box info-box-tip">
  <strong>Language Rule:</strong> When <strong>EN</strong> is selected, 100% of labels and tables appear in standard English with zero Devnagari script. When <strong>नेपाली</strong> is selected, labels use authentic factory terms with bracketed technical terms (e.g., <code>उत्पादन दाखिला (Production Entry)</code>, <code>कर बिजक (Tax Invoice)</code>) so that new staff can learn fast.
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 2: THE FACTORY SCREEN LAYOUT -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 2: The Factory Screen Layout</h1>
<p>LIVO ERP utilizes an <strong>"Industrial Paper"</strong> visual design. The screen has a matte <code>#F8FAFC</code> off-white base with high-contrast <code>#0F172A</code> text and <code>#CBD5E1</code> borders to eliminate eye strain under harsh fluorescent shop-floor lighting.</p>

<div class="screenshot-card">
  <img src="${images.screen_02}" alt="Screen 02 - Global Navigation & AppShell">
  <div class="screenshot-caption">
    <span>SCREEN 02: Global Navigation & Header Shell</span>
    <span>Callouts: [1] Top Banner [2] Network Status [3] Active Role [4] Module Tabs [5] Language Toggle</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 40%;">What It Tells the Worker</th>
      <th style="width: 25%;">Click Behavior</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Top Brand Banner</strong></td>
      <td>Shows legal facility name and registered IRD PAN (<code>609823412</code>).</td>
      <td>Click to return to main dashboard.</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Connection Status Badge</strong></td>
      <td>
        <strong>🟩 Online:</strong> Terminal connected to central cloud server.<br>
        <strong>🟧 Offline (X Batches):</strong> Working locally in browser IndexedDB memory.<br>
        <strong>🟦 Syncing:</strong> Flushing saved offline records to server.
      </td>
      <td>Hover to see queue count; click to trigger manual sync check.</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Role Indicator</strong></td>
      <td>Shows current user permissions (<code>admin</code> with write access vs. <code>viewer</code> read-only).</td>
      <td>Displays active security boundary.</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Primary Module Tabs</strong></td>
      <td>Allows switching between the 6 operational factory departments.</td>
      <td>Click any tab to switch view instantly without full page reloads.</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Header Language Switch</strong></td>
      <td>Persistent toggle between English and Nepali factory vernacular.</td>
      <td>Remembers choice in browser memory.</td>
    </tr>
  </tbody>
</table>

<h3>2.1 The Connection Status Light Explained</h3>
<p>In Nepali industrial zones (Biratnagar, Hetauda, Bhaktapur), factory Wi-Fi frequently drops. LIVO ERP includes an automatic local storage engine (IndexedDB). Staff never need to stop typing when the internet fails:</p>
<ul>
  <li><span class="badge badge-green">🟩 Online (इन्टरनेट चालु छ)</span>: Everything saves directly to the central PostgreSQL database.</li>
  <li><span class="badge badge-orange">🟧 Offline — X Batches Stored (अफलाइन)</span>: You can continue entering batches. Data is safely locked into the computer's hard drive storage. A yellow alert bar appears.</li>
  <li><span class="badge badge-blue">🟦 Syncing Outbox (सिङ्क हुँदैछ)</span>: When Wi-Fi restores, the terminal automatically sends all pending batches to the server one by one without duplicate counting.</li>
</ul>

<!-- ========================================================================= -->
<!-- CHAPTER 3: PRODUCTION BATCH ENTRY (RAMESH'S WORKFLOW) -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 3: Production Batch Entry (उत्पादन दाखिला)</h1>
<p>This chapter teaches <strong>Ramesh</strong> how to log hundreds of finished shoe pairs coming off the assembly lines at high speed without lifting his fingers from the keyboard.</p>

<div class="screenshot-card">
  <img src="${images.screen_03}" alt="Screen 03 - Production Batch Terminal">
  <div class="screenshot-caption">
    <span>SCREEN 03: Production Batch Terminal</span>
    <span>Callouts: [1] Model Select [2] Line & Shift [3] Paris Points Grid (32-43) [4] Live Review Strip [5] Commit Batch</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 40%;">Factory Purpose & Validation Rules</th>
      <th style="width: 25%;">Keyboard Shortcut</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Shoe Model Select</strong></td>
      <td>Choose model code (e.g., <code>LIVO Urban Runner</code>, <code>Classic Oxford</code>).</td>
      <td><kbd>Alt+M</kbd> to focus dropdown</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Line & Shift Config</strong></td>
      <td>Tags entry to specific conveyor line (Line 1/2) and shift crew (Shift 1/2/3).</td>
      <td><kbd>Tab</kbd> to cycle fields</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Paris Points (Sizes 32–43)</strong></td>
      <td>12 individual input boxes representing Continental footwear sizing.</td>
      <td><kbd>Tab</kbd> / <kbd>Enter</kbd> to advance</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Live Batch Review Strip</strong></td>
      <td>Instantly sums total pairs and compares with Shift Target Plan.</td>
      <td>Calculates in real time</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Commit & Save Batch</strong></td>
      <td>Applies immutable stock movement and creates sequential voucher.</td>
      <td><kbd>Ctrl+Enter</kbd> (Instant Submit)</td>
    </tr>
  </tbody>
</table>

<h3>3.1 The "No-Mouse" High-Speed Entry Drill</h3>
<p>Follow this exact 5-step keystroke sequence to enter batches in under 10 seconds:</p>
<ol>
  <li>Select the Shoe Model and Production Line using <kbd>&darr;</kbd> arrow keys.</li>
  <li>Press <kbd>Tab</kbd> until the cursor jumps into the first size box: <strong>Size 32</strong>.</li>
  <li>Type the pair count on the numeric keypad (e.g., <code>0</code> or <code>12</code>), then press <kbd>Enter</kbd> or <kbd>Tab</kbd>. The cursor instantly snaps to <strong>Size 33</strong>.</li>
  <li>Continue typing counts across sizes 34, 35, 36, 37, 38, 39, 40, 41, 42, 43.</li>
  <li>Press <kbd>Ctrl+Enter</kbd>. The system confirms: <em>"Batch saved successfully!"</em>, logs the voucher (e.g. <code>BATCH-2026-0089</code>), clears the quantity boxes, and automatically returns the cursor to <strong>Size 32</strong> for the next batch. <strong>You never have to touch the mouse!</strong></li>
</ol>

<div class="info-box info-box-danger">
  <strong>Integer Pairs Only:</strong> Footwear manufacturing does not permit fractions or negative pairs. If Ramesh accidentally types <code>12.5</code> or <code>-5</code>, the input box flashes red and prevents submission until corrected to a whole positive number.
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 4: STOCK LEDGER & SIZING MATRIX (SITA'S WORKFLOW) -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 4: Stock Ledger & Sizing Matrix (मौज्दात खाता)</h1>
<p>This chapter teaches <strong>Sita</strong> how to inspect warehouse stock across the full Continental size curve and spot incomplete sets that wholesale buyers will reject.</p>

<div class="screenshot-card">
  <img src="${images.screen_04}" alt="Screen 04 - Stock Ledger Matrix">
  <div class="screenshot-caption">
    <span>SCREEN 04: Pinned Column Sizing Grid & Ledger</span>
    <span>Callouts: [1] Pinned SKU [2] Article Name [3] Paris Points Curve (32-43) [4] Broken-Curve Alert [5] Total Pairs</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 40%;">How to Read the Data</th>
      <th style="width: 25%;">Action Required</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Pinned SKU Column</strong></td>
      <td>Permanent unique item code (e.g., <code>SKU-URB-BLK</code>). Stays locked on left.</td>
      <td>Searchable via top bar</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Pinned Article Name</strong></td>
      <td>Model commercial name and colorway. Never scrolls off screen.</td>
      <td>Click to open Stock Card</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Horizontal Size Grid (32–43)</strong></td>
      <td>
        <strong>Bold Number:</strong> Exact pairs on warehouse shelves.<br>
        <strong>Dash (—):</strong> Size not manufactured for this article.<br>
        <strong>Red 0!:</strong> Completely out of stock in this size.
      </td>
      <td>Verify physical rack counts against bold numbers.</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Broken-Run Badge</strong></td>
      <td>
        <span class="badge badge-red">[39–41 Broken]</span> Core adult sizes missing.<br>
        <span class="badge badge-green">[Complete Set]</span> Full size curve available.
      </td>
      <td>Warn wholesale buyers before packing delivery trucks.</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Total Pairs Column</strong></td>
      <td>Sum of all sizes currently available in warehouse inventory.</td>
      <td>Audited against physical warehouse ledger.</td>
    </tr>
  </tbody>
</table>

<h3>4.1 Understanding Broken Size Runs (टुटेका साइजहरू)</h3>
<p>In wholesale footwear, shoe stores in Nepal buy shoes in full cartons containing an assortment of sizes (e.g., 1 pair of 38, 2 pairs of 39, 3 pairs of 40, 3 pairs of 41, 2 pairs of 42, 1 pair of 43). If a warehouse runs out of Sizes 39, 40, or 41 (the "Golden Sizes"), dealers will refuse the carton because customers cannot find their size. The red <strong>[Broken]</strong> indicator warns Sita not to promise orders until the assembly plant produces more core pairs.</p>

<!-- ========================================================================= -->
<!-- CHAPTER 4 CONTINUED: STOCK CARD MODAL -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h2>The Stock Card (स्टक कार्ड) — Complete History of Every Shoe</h2>
<p>When Sita or an auditor needs to know who added or removed shoes, clicking <strong>"Stock Card"</strong> opens an immutable transaction history showing every batch, every invoice, and every stock correction.</p>

<div class="screenshot-card">
  <img src="${images.screen_05}" alt="Screen 05 - Stock Card Modal">
  <div class="screenshot-caption">
    <span>SCREEN 05: Stock Card Modal (स्टक कार्ड विवरण)</span>
    <span>Callouts: [1] Live Size Curve [2] Inflow (+) [3] Outflow (-) [4] Running Balance [5] Source Voucher Tag</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 45%;">Statutory & Factory Meaning</th>
      <th style="width: 20%;">Audit Rule</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Live Size Curve Dock</strong></td>
      <td>Shows current shelf balance across all 12 Continental sizes in one glance.</td>
      <td>Matches physical shelf racks</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Inflow Column (+)</strong></td>
      <td>Shoes received into inventory from production batches or returns.</td>
      <td>Positive ledger entry</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Outflow Column (-)</strong></td>
      <td>Shoes dispatched to buyers via tax invoices or approved samples.</td>
      <td>Negative ledger entry</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Running Balance</strong></td>
      <td>Accumulated inventory balance after each movement occurred.</td>
      <td>Zero-Floor Protected</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Voucher Reference Tag</strong></td>
      <td>Clickable link to original source document (<code>BATCH-XXXX</code> or <code>INV-01-XXXX</code>).</td>
      <td>Immutable audit trail</td>
    </tr>
  </tbody>
</table>

<div class="info-box info-box-tip">
  <strong>The Physical Registered Notebook Analogy:</strong> LIVO ERP functions like a physical legal notebook where lines can never be erased or whited-out. If someone made a mistake, they cannot delete the row; they must record an official adjustment or reversal line.
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 5: CONTROLLED STOCK CORRECTIONS -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 5: Controlled Stock Corrections (स्टक मिलान)</h1>
<p>This chapter explains how to correct counting mistakes, record broken shoes, or log marketing samples without compromising government tax audit trails.</p>

<div class="screenshot-card">
  <img src="${images.screen_06}" alt="Screen 06 - Controlled Stock Adjustment Modal">
  <div class="screenshot-caption">
    <span>SCREEN 06: Controlled Stock Adjustment Modal</span>
    <span>Callouts: [1] Reason Code [2] Reason Options [3] Target Paris Point [4] Supervisor Token [5] Commit Adjustment</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 40%;">Factory Purpose</th>
      <th style="width: 25%;">Rules & Constraints</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Reason Code Selector</strong></td>
      <td>Statutory classification of why the physical count differed from system count.</td>
      <td>Mandatory selection</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Approved Reason Types</strong></td>
      <td>
        • <strong>RECOUNT:</strong> Physical inventory count reconciliation.<br>
        • <strong>DAMAGED:</strong> Torn leather, failed sole bonding.<br>
        • <strong>SAMPLE:</strong> Taken by marketing for retail showroom.<br>
        • <strong>SCRAP:</strong> Beyond repair; sent to recycling.
      </td>
      <td>Categorized in audit reports</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Select Paris Point</strong></td>
      <td>Identifies the exact shoe size being adjusted (e.g. Size 41).</td>
      <td>Adjusts individual size cell</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Supervisor Authorization</strong></td>
      <td>High-security PIN or token required whenever stock is <em>reduced</em>.</td>
      <td>Prevents unauthorized theft concealment</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Commit Adjustment</strong></td>
      <td>Applies movement and logs supervisor name in audit trail.</td>
      <td>Creates <code>ADJ-XXXX</code> voucher</td>
    </tr>
  </tbody>
</table>

<!-- ========================================================================= -->
<!-- CHAPTER 6: WHOLESALE DISPATCH & NEPAL TAX INVOICES -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 6: Wholesale Dispatch & Nepal Tax Invoices (कर बिजक)</h1>
<p>This chapter guides <strong>Sita</strong> through creating wholesale dispatch orders, using the carton-to-pair calculator, calculating 13% Nepal VAT, and printing official Schedule-5 tax bills.</p>

<div class="screenshot-card">
  <img src="${images.screen_07}" alt="Screen 07 - Wholesale Dispatch Form">
  <div class="screenshot-caption">
    <span>SCREEN 07: Wholesale Dispatch & Tax Invoice Form</span>
    <span>Callouts: [1] Buyer Name [2] Buyer PAN [3] Carton Helper (1 Ctn = 12 Prs) [4] 13% VAT Calculation [5] Grand Total</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Screen Element</th>
      <th style="width: 40%;">Statutory Meaning (Nepal IRD)</th>
      <th style="width: 25%;">Factory Validation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Buyer / Client Name</strong></td>
      <td>Registered wholesale dealer or institution purchasing footwear.</td>
      <td>Select from approved debtors</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Buyer PAN Number</strong></td>
      <td>Permanent Account Number (9 digits) issued by Inland Revenue Dept.</td>
      <td>Mandatory for transactions > Rs. 10,000</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Carton Packaging Helper</strong></td>
      <td>Dual-unit calculator: <code>Cartons &times; 12 = Total Loose Pairs</code>.</td>
      <td>Ensures truck loading matches invoice</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>VAT (13%) Computation</strong></td>
      <td>Statutory 13% Value Added Tax calculated in integer paisa arithmetic.</td>
      <td>Exact rounded currency math</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Grand Total (NPR)</strong></td>
      <td>Total receivable amount including base subtotal and 13% VAT.</td>
      <td>Appended to Party Aging ledger</td>
    </tr>
  </tbody>
</table>

<div class="info-box info-box-tip">
  <strong>The Carton Packaging Helper:</strong> Footwear master cartons contain exactly 12 pairs. If a customer orders 20 cartons, typing <code>20</code> in the Carton box automatically fills <code>240</code> pairs into the system. If loose pairs are also shipped, Sita can add loose pairs and the total updates instantly.
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 6 CONTINUED: OFFICIAL PRINTABLE TAX INVOICE -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h2>Official Nepal IRD Schedule-5 Printable Tax Invoice (अनुसूची-५ कर बिजक)</h2>
<p>When goods leave the factory gate, trucks must carry the official printed tax invoice to pass traffic police and tax checkpoint inspections across highways.</p>

<div class="screenshot-card">
  <img src="${images.screen_08}" alt="Screen 08 - Official Printable Tax Invoice">
  <div class="screenshot-caption">
    <span>SCREEN 08: Official IRD Schedule-5 Tax Invoice Print Layout</span>
    <span>Callouts: [1] Seller Details [2] Buyer Details [3] Itemized Table [4] Taxable Subtotal [5] Dual Signature Boxes</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Invoice Section</th>
      <th style="width: 45%;">Statutory Compliance Verification</th>
      <th style="width: 20%;">Print Verification</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Seller Details & PAN</strong></td>
      <td>LIVO GROUP OF INDUSTRIES PVT. LTD., PAN: <code>609823412</code>, Kathmandu.</td>
      <td>Must appear at top-left</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Buyer Details & PAN</strong></td>
      <td>Customer name, registered delivery address, and buyer's 9-digit PAN.</td>
      <td>Required for VAT deduction</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>Itemized Particulars</strong></td>
      <td>Model name, size specification, carton quantity, pairs, rate, and amount.</td>
      <td>Clean bordered table</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>Taxable Breakdown</strong></td>
      <td>Taxable Subtotal (करयोग्य रकम), 13% VAT, and Grand Total in NPR.</td>
      <td>Exact paisa precision</td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>Dual Signature Lines</strong></td>
      <td>
        • Left: <strong>Buyer / Receiver Signature (बुझिलिनेको दस्तखत)</strong><br>
        • Right: <strong>Store In-charge / Authorized Signatory (कारखाना प्रमुख)</strong>
      </td>
      <td>Mandatory physical signatures before gate pass</td>
    </tr>
  </tbody>
</table>

<div class="info-box info-box-warn">
  <strong>Printing Tips:</strong> When pressing <kbd>Ctrl+P</kbd>, ensure your print settings are set to: <strong>Destination:</strong> Thermal or Laser Printer, <strong>Paper Size:</strong> A4, <strong>Margins:</strong> Default, <strong>Background Graphics:</strong> Checked. The system automatically hides all web browser navigation buttons for a clean printout.
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 7: PARTY ACCOUNTS & CUSTOMER AGING -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 7: Party Accounts & Customer Aging (पार्टी बाँकी)</h1>
<p>This chapter explains how factory accountants and credit managers track unpaid customer bills, enforce credit limits, and record bank transfer receipts.</p>

<div class="screenshot-card">
  <img src="${images.screen_09}" alt="Screen 09 - Party Aging Worklist">
  <div class="screenshot-caption">
    <span>SCREEN 09: Accounts Receivable Aging Subledger</span>
    <span>Callouts: [1] Total Outstanding [2] Current (0-30d) [3] 61-90d Warning [4] >90d Default Risk [5] + Record Payment</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width: 10%;">Callout</th>
      <th style="width: 25%;">Aging Bucket</th>
      <th style="width: 40%;">Financial & Credit Meaning</th>
      <th style="width: 25%;">Credit Action Required</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="callout-num">1</span></td>
      <td><strong>Total Outstanding</strong></td>
      <td>Sum total of all unpaid customer balances across all wholesale clients.</td>
      <td>Audited monthly with bank</td>
    </tr>
    <tr>
      <td><span class="callout-num">2</span></td>
      <td><strong>Current (0–30 Days)</strong></td>
      <td>Fresh deliveries shipped within standard 30-day payment terms.</td>
      <td>Normal operation; no action</td>
    </tr>
    <tr>
      <td><span class="callout-num">3</span></td>
      <td><strong>61–90 Days (Warning)</strong></td>
      <td>Past due. Customer has not paid despite repeated delivery cycles.</td>
      <td>Issue formal payment reminder</td>
    </tr>
    <tr>
      <td><span class="callout-num">4</span></td>
      <td><strong>> 90 Days (Default Risk)</strong></td>
      <td>Critical default risk. Account automatically placed on Credit Hold.</td>
      <td><strong>Automatic dispatch freeze</strong></td>
    </tr>
    <tr>
      <td><span class="callout-num">5</span></td>
      <td><strong>+ Record Payment</strong></td>
      <td>Logs bank voucher or cash receipt against open customer invoices.</td>
      <td>Decrements outstanding balance</td>
    </tr>
  </tbody>
</table>

<h3>7.1 The Party Account Statement & Dispute Ledger</h3>
<p>Clicking <strong>"Statement"</strong> on any customer row opens their full subledger statement:</p>
<div class="screenshot-card">
  <img src="${images.screen_10}" alt="Screen 10 - Party Statement Modal">
  <div class="screenshot-caption">
    <span>SCREEN 10: Party Account Statement Modal (ग्राहक हिसाब विवरण)</span>
    <span>Callouts: [1] Debtor Info [2] Net Balance [3] Debit (+) [4] Credit (-) [5] Running Balance [6] Audit/Dispute</span>
  </div>
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 8: AUDITOR READ-ONLY MODE (HARI PRASAD'S WORKFLOW) -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 8: Auditor Read-Only Mode (निरीक्षण मोड)</h1>
<p>This chapter explains how <strong>Hari Prasad</strong> conducts external audits without the risk of accidental data modification or tampering.</p>

<div class="screenshot-card">
  <img src="${images.screen_13}" alt="Screen 13 - Auditor Viewer Read-Only Mode">
  <div class="screenshot-caption">
    <span>SCREEN 13: Auditor Read-Only Interface (/login via viewer_demo)</span>
    <span>Callouts: [1] Viewer Role Badge [2] Export CSV Available [3] Absence of Mutation Buttons</span>
  </div>
</div>

<h3>8.1 Tamper-Proof Safeguards</h3>
<p>When logged in as <code>viewer_demo</code>, the ERP user interface automatically enforces read-only safety mechanisms:</p>
<ul>
  <li><strong>All Mutation Buttons Vanish:</strong> The buttons <code>+ New Batch</code>, <code>+ Stock Adjustment</code>, <code>Commit Batch</code>, and <code>+ Record Payment</code> are completely removed from the DOM.</li>
  <li><strong>Keyboard Shortcut Guard:</strong> Shortcuts like <kbd>Ctrl+Enter</kbd> are deactivated.</li>
  <li><strong>Backend API RBAC:</strong> Even if a malicious user uses browser developer tools to send an HTTP POST request, the backend server rejects the mutation with an immediate <code>403 Forbidden: Insufficient operational privileges</code> error.</li>
  <li><strong>CSV / Excel Export:</strong> Auditors can export full raw ledger datasets via the <strong>Export CSV</strong> button for independent balance verification.</li>
</ul>

<!-- ========================================================================= -->
<!-- CHAPTER 9: 10-SECOND QUICK TROUBLESHOOTING GUIDE -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h1>Chapter 9: 10-Second Quick Troubleshooting Guide</h1>
<p>Keep this page pinned near factory computer terminals for immediate problem resolution.</p>

<table>
  <thead>
    <tr>
      <th style="width: 30%;">What the Screen Shows</th>
      <th style="width: 30%;">Why It Happened</th>
      <th style="width: 40%;">Exact Fix (What to Do)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>"504 Gateway Timeout" or screen takes 20 seconds to load on first morning launch</strong></td>
      <td>The free backend cloud server on Render goes to sleep after periods of inactivity.</td>
      <td>Wait 30 seconds for the cloud server to spin up, then press <kbd>Ctrl+F5</kbd> to reload. Once awake, the system responds instantly.</td>
    </tr>
    <tr>
      <td><strong>"Insufficient stock in Size 41" error when trying to dispatch an invoice</strong></td>
      <td>Zero-Floor Stockout Protection: You are trying to sell more pairs than physically exist on warehouse shelves.</td>
      <td>Open the Stock Card for that SKU. Verify physical pairs on shelf. If finished shoes just arrived from assembly, ensure Ramesh has entered the production batch first.</td>
    </tr>
    <tr>
      <td><strong>Customer row has red [HOLD] badge and dispatch is blocked</strong></td>
      <td>Credit Limit Lockdown: The customer's unpaid balance exceeds their authorized credit ceiling.</td>
      <td>Contact the customer to collect bank payments. Once the accountant logs a payment via <code>+ Record Payment</code>, the hold automatically clears.</td>
    </tr>
    <tr>
      <td><strong>Status light turns Orange: "अफलाइन (Offline)"</strong></td>
      <td>Plant Wi-Fi or router connection temporarily dropped.</td>
      <td>Do not panic! Continue entering batches. Data is safely stored in browser memory. When Wi-Fi restores, the badge turns Green automatically.</td>
    </tr>
    <tr>
      <td><strong>Printer cuts off the invoice right border or prints blank pages</strong></td>
      <td>Printer driver margin settings are incorrect.</td>
      <td>In the Chrome Print dialog, set <strong>Destination</strong> to your printer, <strong>Paper Size</strong> to <code>A4</code>, <strong>Margins</strong> to <code>Default</code>, and check <code>Background Graphics</code>.</td>
    </tr>
  </tbody>
</table>

<!-- ========================================================================= -->
<!-- WORKFLOW DEMO SEQUENCES -->
<!-- ========================================================================= -->
<div class="page-break"></div>

<h2>Appendix: Critical Factory Safety Demonstrations</h2>

<h3>Demonstration A: The Rapid Keyboard Entry Workflow</h3>
<p>Ramesh demonstrates typing finished shoe counts using only <kbd>Tab</kbd> and the numeric keypad:</p>
<div class="step-grid">
  <div class="step-card">
    <strong>Step 1: Select Model & Line</strong>
    <p style="font-size: 8pt; color: #64748B;">Cursor focuses on model dropdown.</p>
    <img src="${images.seq_A1}" alt="Step A1">
  </div>
  <div class="step-card">
    <strong>Step 2: Rapid Numeric Entry</strong>
    <p style="font-size: 8pt; color: #64748B;">Tab through size boxes entering quantities.</p>
    <img src="${images.seq_A2}" alt="Step A2">
  </div>
</div>
<div class="step-grid">
  <div class="step-card">
    <strong>Step 3: Live Variance Review</strong>
    <p style="font-size: 8pt; color: #64748B;">Live strip tallies pairs and shows plan variance.</p>
    <img src="${images.seq_A3}" alt="Step A3">
  </div>
  <div class="step-card">
    <strong>Step 4: Press <kbd>Ctrl+Enter</kbd> to Commit</strong>
    <p style="font-size: 8pt; color: #64748B;">System saves batch, increments number, and snaps cursor to Size 32.</p>
    <div style="padding: 20pt; text-align: center; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 2pt; margin-top: 4pt;">
      <span style="font-size: 14pt; font-weight: 800; color: #166534;">✓ Batch Saved Successfully!</span><br>
      <span style="font-size: 8.5pt; color: #15803D;">Ready for next batch in 0.2s</span>
    </div>
  </div>
</div>

<h3>Demonstration B & C: Zero-Floor & Credit Limit Protection</h3>
<div class="step-grid">
  <div class="step-card">
    <strong>Demonstration B: Zero-Floor Stockout Protection</strong>
    <p style="font-size: 8pt; color: #64748B;">Attempting to dispatch 9,999 pairs when stock is insufficient.</p>
    <img src="${images.seq_B1}" alt="Sequence B1">
    <div style="font-size: 7.5pt; color: #B91C1C; margin-top: 2pt; font-weight: 600;">
      ⛔ System blocks dispatch with clear explanation.
    </div>
  </div>
  <div class="step-card">
    <strong>Demonstration C: Credit Limit Lockdown</strong>
    <p style="font-size: 8pt; color: #64748B;">Customer with unpaid balance placed on credit hold.</p>
    <img src="${images.seq_C1}" alt="Sequence C1">
    <div style="font-size: 7.5pt; color: #B91C1C; margin-top: 2pt; font-weight: 600;">
      🔒 Invoicing disabled until account balance cleared.
    </div>
  </div>
</div>

<div style="margin-top: 20pt; padding: 12pt; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 3pt; text-align: center; font-size: 8.5pt; color: #64748B;">
  <strong>LIVO Footwear ERP • Standard Operating Procedure & Client Implementation Playbook</strong><br>
  Published by Livo Group of Industries Pvt. Ltd. • Quality & Systems Engineering Division<br>
  For factory technical support or training inquiries, contact your shift IT coordinator.
</div>

</body>
</html>
`;

async function generatePdf() {
  const htmlPath = path.join(DOCS_DIR, 'LIVO_ERP_Visual_Operations_Manual_and_Playbook.html');
  fs.writeFileSync(htmlPath, htmlContent, 'utf8');
  console.log(`[WROTE HTML] ${htmlPath}`);

  console.log('Launching Puppeteer to generate high-resolution PDF...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

  const pdfPath = path.join(DOCS_DIR, 'LIVO_ERP_Visual_Operations_Manual_and_Playbook.pdf');
  const artifactPdfPath = path.join(ARTIFACT_DIR, 'LIVO_ERP_Visual_Operations_Manual_and_Playbook.pdf');

  await page.pdf({
    path: pdfPath,
    format: 'A4',
    printBackground: true,
    margin: {
      top: '16mm',
      bottom: '16mm',
      left: '14mm',
      right: '14mm'
    }
  });
  console.log(`[GENERATED PDF] ${pdfPath}`);

  // Copy to artifact directory
  try {
    fs.copyFileSync(pdfPath, artifactPdfPath);
    console.log(`[COPIED PDF TO ARTIFACTS] ${artifactPdfPath}`);
  } catch (e) {
    console.warn('Failed to copy to artifact dir:', e);
  }

  await browser.close();
  console.log('PDF GENERATION COMPLETE!');
}

generatePdf().catch(err => {
  console.error('PDF Generation failed:', err);
  process.exit(1);
});
