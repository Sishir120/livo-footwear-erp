const puppeteer = require('../frontend/node_modules/puppeteer-core');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = 'C:/Users/sishi/.gemini/antigravity-ide/brain/1849f93e-c4c7-4ece-b3df-2d5c85fa991d';
const DOCS_DIR = path.resolve(__dirname, '../docs/screenshots');

if (!fs.existsSync(DOCS_DIR)) {
  fs.mkdirSync(DOCS_DIR, { recursive: true });
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function saveScreen(page, filename) {
  const docsPath = path.join(DOCS_DIR, filename);
  const artifactPath = path.join(ARTIFACT_DIR, filename);
  await page.screenshot({ path: docsPath, fullPage: false });
  try {
    fs.copyFileSync(docsPath, artifactPath);
  } catch (e) {}
  console.log(`[CAPTURED] ${filename}`);
}

async function injectCallouts(page, callouts) {
  await page.evaluate((callouts) => {
    // Remove previous callouts
    document.querySelectorAll('.manual-callout-badge').forEach(el => el.remove());

    callouts.forEach(({ selector = '*', label, position = 'top-left', offsetX = 0, offsetY = 0, textMatch }) => {
      let target = null;
      try {
        if (textMatch) {
          const elements = Array.from(document.querySelectorAll(selector));
          target = elements.find(el => el.textContent && el.textContent.includes(textMatch));
        } else if (selector) {
          target = document.querySelector(selector);
        }
      } catch (e) {
        console.warn('Selector error:', selector, e);
      }

      if (!target) return;

      const rect = target.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return;

      const badge = document.createElement('div');
      badge.className = 'manual-callout-badge';
      badge.textContent = label;
      badge.style.position = 'fixed';
      badge.style.background = '#DC2626';
      badge.style.color = '#FFFFFF';
      badge.style.fontFamily = 'Inter, -apple-system, sans-serif';
      badge.style.fontSize = '12px';
      badge.style.fontWeight = '900';
      badge.style.width = '24px';
      badge.style.height = '24px';
      badge.style.borderRadius = '50%';
      badge.style.display = 'flex';
      badge.style.alignItems = 'center';
      badge.style.justifyContent = 'center';
      badge.style.boxShadow = '0 2px 8px rgba(0,0,0,0.35), 0 0 0 2px #FFFFFF';
      badge.style.zIndex = '999999';
      badge.style.pointerEvents = 'none';

      let top = rect.top;
      let left = rect.left;

      if (position === 'top-right') {
        left = rect.right - 12;
        top = rect.top - 12;
      } else if (position === 'top-left') {
        left = rect.left - 12;
        top = rect.top - 12;
      } else if (position === 'bottom-left') {
        left = rect.left - 12;
        top = rect.bottom - 12;
      } else if (position === 'bottom-right') {
        left = rect.right - 12;
        top = rect.bottom - 12;
      } else if (position === 'right-center') {
        left = rect.right + 6;
        top = rect.top + (rect.height / 2) - 12;
      } else if (position === 'left-center') {
        left = rect.left - 30;
        top = rect.top + (rect.height / 2) - 12;
      }

      badge.style.left = `${Math.max(4, left + offsetX)}px`;
      badge.style.top = `${Math.max(4, top + offsetY)}px`;

      document.body.appendChild(badge);
    });
  }, callouts);
}

async function removeCallouts(page) {
  await page.evaluate(() => {
    document.querySelectorAll('.manual-callout-badge').forEach(el => el.remove());
  });
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    defaultViewport: { width: 1920, height: 1080 },
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  console.log('Navigating to Live ERP Login...');
  await page.goto('https://livo-footwear-erp.vercel.app/login', { waitUntil: 'networkidle2' });
  await delay(1500);

  // 1. SCREEN 01 - Authentication Gateway
  await injectCallouts(page, [
    { selector: 'input[name="username"], input[type="text"]', label: '1', position: 'left-center' },
    { selector: 'input[name="password"], input[type="password"]', label: '2', position: 'left-center' },
    { selector: 'button', textMatch: '', position: 'right-center', selector: 'div[style*="position: relative"] button' },
    { selector: 'div[role="group"]', label: '3', position: 'top-left' },
    { selector: 'button', textMatch: 'Admin Operator', label: '4', position: 'top-left' }
  ]);
  await saveScreen(page, 'screen_01_login_gateway.png');
  await removeCallouts(page);

  // Click Admin Operator demo button & log in
  console.log('Logging in as Admin Operator...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const adminBtn = btns.find(b => b.textContent && b.textContent.includes('Admin Operator'));
    if (adminBtn) adminBtn.click();
  });
  await delay(400);

  // Submit form
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const submitBtn = btns.find(b => b.textContent && b.textContent.includes('Sign In'));
    if (submitBtn) submitBtn.click();
  });

  await page.waitForNavigation({ waitUntil: 'networkidle2' }).catch(() => delay(3000));
  await delay(3000);

  // 2. SCREEN 02 - Global Navigation & AppShell
  await injectCallouts(page, [
    { selector: 'h1, div:has(h1)', label: '1', position: 'top-left', offsetX: 10, offsetY: 0 },
    { selector: 'span', textMatch: 'Online', label: '2', position: 'top-left', offsetX: -10, offsetY: -5 },
    { selector: 'div', textMatch: 'Role: admin', label: '3', position: 'top-left', offsetX: -5, offsetY: -5 },
    { selector: 'button', textMatch: 'Stock Ledger', label: '4', position: 'top-left', offsetX: -10, offsetY: -10 },
    { selector: 'button', textMatch: 'नेपाली', label: '5', position: 'top-left', offsetX: -10, offsetY: -5 }
  ]);
  await saveScreen(page, 'screen_02_global_appshell_and_nav.png');
  await removeCallouts(page);

  // Ensure on Stock Ledger
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const tab = btns.find(b => b.textContent && b.textContent.includes('Stock Ledger'));
    if (tab) tab.click();
  });
  await delay(1500);

  // 4. SCREEN 04 - Sizing Matrix & Stock Ledger
  await injectCallouts(page, [
    { selector: 'th', textMatch: 'SKU', label: '1', position: 'top-left', offsetX: 5, offsetY: 5 },
    { selector: 'th', textMatch: 'Article', label: '2', position: 'top-left', offsetX: 5, offsetY: 5 },
    { selector: 'th', textMatch: '32', label: '3', position: 'top-left', offsetX: 2, offsetY: 5 },
    { selector: 'span', textMatch: 'Broken', label: '4', position: 'top-left', offsetX: -5, offsetY: -5 },
    { selector: 'th', textMatch: 'Total Pairs', label: '5', position: 'top-left', offsetX: -5, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_04_stock_ledger_matrix.png');
  await removeCallouts(page);

  // 5. SCREEN 05 - Stock Card Modal
  console.log('Opening Stock Card modal...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const cardBtn = btns.find(b => b.textContent && b.textContent.includes('Stock Card'));
    if (cardBtn) cardBtn.click();
  });
  await delay(2000);

  await injectCallouts(page, [
    { selector: 'div', textMatch: 'Balance Across Continental Paris Points', label: '1', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'th', textMatch: 'In (+)', label: '2', position: 'top-left', offsetX: -5, offsetY: 5 },
    { selector: 'th', textMatch: 'Out (-)', label: '3', position: 'top-left', offsetX: -5, offsetY: 5 },
    { selector: 'th', textMatch: 'Balance', label: '4', position: 'top-left', offsetX: -5, offsetY: 5 },
    { selector: 'td', textMatch: 'BATCH-', label: '5', position: 'top-left', offsetX: 5, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_05_stock_card_modal.png');
  await removeCallouts(page);

  // Close Stock Card modal
  await page.evaluate(() => {
    const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.querySelector('svg.lucide-x'));
    if (closeBtn) closeBtn.click();
  });
  await delay(800);

  // 6. SCREEN 06 - Controlled Stock Adjustment Modal
  console.log('Opening Stock Adjustment modal...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const adjBtn = btns.find(b => b.textContent && b.textContent.includes('Stock Adjustment'));
    if (adjBtn) adjBtn.click();
  });
  await delay(1500);

  await injectCallouts(page, [
    { selector: 'label', textMatch: 'Reason Code', label: '1', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'span', textMatch: 'Recount Correction', label: '2', position: 'top-left', offsetX: -5, offsetY: -5 },
    { selector: 'label', textMatch: 'Select Paris Point', label: '3', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'label', textMatch: 'Supervisor Authorization', label: '4', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'button', textMatch: 'Commit Stock Adjustment', label: '5', position: 'top-left', offsetX: 10, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_06_stock_adjustment_modal.png');
  await removeCallouts(page);

  // Close adjustment modal
  await page.evaluate(() => {
    const cancelBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Cancel'));
    if (cancelBtn) cancelBtn.click();
  });
  await delay(800);

  // 3. SCREEN 03 - Production Batch Terminal
  console.log('Switching to Production Batches...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const prodTab = btns.find(b => b.textContent && (b.textContent.includes('Production Batches') || b.textContent.includes('उत्पादन दाखिला')));
    if (prodTab) prodTab.click();
  });
  await delay(2000);

  // Fill in some sample numbers into size inputs
  await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input[type="number"]'));
    if (inputs.length >= 6) {
      inputs[4].value = '12';
      inputs[4].dispatchEvent(new Event('input', { bubbles: true }));
      inputs[5].value = '18';
      inputs[5].dispatchEvent(new Event('input', { bubbles: true }));
      inputs[6].value = '24';
      inputs[6].dispatchEvent(new Event('input', { bubbles: true }));
      inputs[7].value = '12';
      inputs[7].dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
  await delay(500);

  await injectCallouts(page, [
    { selector: 'label', textMatch: 'Shoe Model', label: '1', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'label', textMatch: 'Production Line', label: '2', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'label', textMatch: 'Continental Paris Points', label: '3', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'div', textMatch: 'Total Batch Quantity', label: '4', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'button', textMatch: 'Commit & Save Batch', label: '5', position: 'top-left', offsetX: 10, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_03_production_batch_terminal.png');
  await removeCallouts(page);

  // Workflow Demo Sequence A: Rapid Keyboard Batch Entry frames
  console.log('Capturing Sequence A (Rapid Keyboard Batch Entry)...');
  await saveScreen(page, 'seq_A1_model_and_line_selection.png');
  // Type into Size 38
  await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input[type="number"]'));
    if (inputs[6]) {
      inputs[6].focus();
      inputs[6].value = '36';
      inputs[6].dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
  await delay(300);
  await saveScreen(page, 'seq_A2_rapid_numeric_entry.png');
  // Live batch strip variance
  await saveScreen(page, 'seq_A3_live_strip_variance_update.png');

  // 7. SCREEN 07 - Wholesale Dispatch & Tax Invoice Form
  console.log('Switching to Sales & Invoicing...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const salesTab = btns.find(b => b.textContent && (b.textContent.includes('Sales & Invoicing') || b.textContent.includes('कर बिजक')));
    if (salesTab) salesTab.click();
  });
  await delay(2000);

  // Open New Order modal
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const newBtn = btns.find(b => b.textContent && (b.textContent.includes('New Sales') || b.textContent.includes('New Order') || b.textContent.includes('Dispatch')));
    if (newBtn) newBtn.click();
  });
  await delay(1500);

  await injectCallouts(page, [
    { selector: 'label', textMatch: 'Buyer / Client Name', label: '1', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'label', textMatch: 'Buyer PAN Number', label: '2', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'div', textMatch: 'Carton Packaging Helper', label: '3', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div', textMatch: 'VAT (13%)', label: '4', position: 'top-left', offsetX: -10, offsetY: 2 },
    { selector: 'div', textMatch: 'Grand Total', label: '5', position: 'top-left', offsetX: -10, offsetY: 2 }
  ]);
  await saveScreen(page, 'screen_07_wholesale_dispatch_invoice_form.png');
  await removeCallouts(page);

  // Workflow Demo Sequence B: Zero-floor stockout test
  console.log('Capturing Sequence B (Zero-Floor Stockout Protection)...');
  await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input[type="number"]'));
    if (inputs.length > 0) {
      inputs[0].value = '9999';
      inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
  await delay(400);
  await saveScreen(page, 'seq_B1_excessive_dispatch_input.png');

  // Close order modal
  await page.evaluate(() => {
    const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.querySelector('svg.lucide-x') || (b.textContent && b.textContent.includes('Cancel')));
    if (closeBtn) closeBtn.click();
  });
  await delay(800);

  // 8. SCREEN 08 - Official Nepal IRD Schedule-5 Printable Tax Invoice
  console.log('Opening Tax Invoice Printable Preview...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const printBtn = btns.find(b => b.textContent && (b.textContent.includes('Preview & Print') || b.textContent.includes('Tax Invoice') || b.textContent.includes('Print')));
    if (printBtn) printBtn.click();
  });
  await delay(2000);

  await injectCallouts(page, [
    { selector: 'div', textMatch: 'Seller Details', label: '1', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div', textMatch: 'Buyer Details', label: '2', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'table', label: '3', position: 'top-left', offsetX: 20, offsetY: 15 },
    { selector: 'div', textMatch: 'Taxable Subtotal', label: '4', position: 'top-left', offsetX: -10, offsetY: 2 },
    { selector: 'div', textMatch: 'Buyer Signature', label: '5', position: 'top-left', offsetX: 10, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_08_schedule_5_printable_tax_invoice.png');
  await removeCallouts(page);

  // Close printable modal
  await page.evaluate(() => {
    const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.querySelector('svg.lucide-x') || (b.textContent && b.textContent.includes('Close')));
    if (closeBtn) closeBtn.click();
  });
  await delay(800);

  // 9. SCREEN 09 - Accounts Receivable Aging Worklist
  console.log('Switching to Party Aging & AR...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const arTab = btns.find(b => b.textContent && (b.textContent.includes('Party Aging') || b.textContent.includes('पार्टी बाँकी')));
    if (arTab) arTab.click();
  });
  await delay(2000);

  await injectCallouts(page, [
    { selector: 'div.glass-card', textMatch: 'Total Outstanding', label: '1', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div.glass-card', textMatch: 'Current (0–30', label: '2', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div.glass-card', textMatch: '61–90', label: '3', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div.glass-card', textMatch: '> 90', label: '4', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'button', textMatch: 'Record Payment', label: '5', position: 'top-left', offsetX: 5, offsetY: 2 }
  ]);
  await saveScreen(page, 'screen_09_party_aging_worklist.png');
  await removeCallouts(page);

  // Workflow Demo Sequence C: Credit Limit Lockdown
  console.log('Capturing Sequence C (Credit Limit Lockdown)...');
  await injectCallouts(page, [
    { selector: 'span', textMatch: 'HOLD', label: 'C1', position: 'top-left', offsetX: -5, offsetY: -5 }
  ]);
  await saveScreen(page, 'seq_C1_credit_limit_hold_badge.png');
  await removeCallouts(page);

  // 10. SCREEN 10 - Party Statement & Dispute Ledger
  console.log('Opening Party Statement modal...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const stmtBtn = btns.find(b => b.textContent && (b.textContent.includes('Statement') || b.textContent.includes('खाता')));
    if (stmtBtn) stmtBtn.click();
  });
  await delay(2000);

  await injectCallouts(page, [
    { selector: 'div', textMatch: 'Debtor Account', label: '1', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div', textMatch: 'Net Ledger Balance', label: '2', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'th', textMatch: 'Debit (+)', label: '3', position: 'top-left', offsetX: -5, offsetY: 2 },
    { selector: 'th', textMatch: 'Credit (-)', label: '4', position: 'top-left', offsetX: -5, offsetY: 2 },
    { selector: 'th', textMatch: 'Balance', label: '5', position: 'top-left', offsetX: -5, offsetY: 2 },
    { selector: 'th', textMatch: 'Audit', label: '6', position: 'top-left', offsetX: -5, offsetY: 2 }
  ]);
  await saveScreen(page, 'screen_10_party_statement_dispute_modal.png');
  await removeCallouts(page);

  // Close statement modal
  await page.evaluate(() => {
    const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.querySelector('svg.lucide-x'));
    if (closeBtn) closeBtn.click();
  });
  await delay(800);

  // 11. SCREEN 11 - Supervisor Exception Cockpit
  console.log('Switching to Supervisor Cockpit...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const cockpitTab = btns.find(b => b.textContent && (b.textContent.includes('Supervisor Cockpit') || b.textContent.includes('ककपिट')));
    if (cockpitTab) cockpitTab.click();
  });
  await delay(2000);

  await injectCallouts(page, [
    { selector: 'div.glass-card', textMatch: 'Blocked Dispatches', label: '1', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div.glass-card', textMatch: 'Over-Limit Orders', label: '2', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div.glass-card', textMatch: 'Broken Core Runs', label: '3', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div.glass-card', textMatch: 'Outbox Backlog', label: '4', position: 'top-left', offsetX: 10, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_11_supervisor_exception_cockpit.png');
  await removeCallouts(page);

  // 12. SCREEN 12 - Factory Settings & Diagnostics
  console.log('Switching to Settings...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const setTab = btns.find(b => b.textContent && (b.textContent.includes('Settings') || b.textContent.includes('सेटिङ')));
    if (setTab) setTab.click();
  });
  await delay(2000);

  await injectCallouts(page, [
    { selector: 'div', textMatch: 'Company Profile & Legal Entity', label: '1', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'span', textMatch: 'IRD VERIFIED', label: '2', position: 'top-left', offsetX: -5, offsetY: -5 },
    { selector: 'div', textMatch: 'Offline Storage & Local Cache', label: '3', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'div', textMatch: 'Automated Database Backup Verification', label: '4', position: 'top-left', offsetX: 10, offsetY: 5 },
    { selector: 'button', textMatch: 'Run Full Diagnostic', label: '5', position: 'top-left', offsetX: 10, offsetY: 5 }
  ]);
  await saveScreen(page, 'screen_12_settings_and_diagnostics.png');
  await removeCallouts(page);

  // 13. SCREEN 13 - Auditor Viewer (Read-Only Mode)
  console.log('Logging out to capture Auditor Viewer mode...');
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const logoutBtn = btns.find(b => b.textContent && (b.textContent.includes('Sign Out') || b.textContent.includes('Logout')));
    if (logoutBtn) logoutBtn.click();
  });
  await delay(1500);

  // Click Auditor Viewer demo button
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const viewerBtn = btns.find(b => b.textContent && b.textContent.includes('Auditor Viewer'));
    if (viewerBtn) viewerBtn.click();
  });
  await delay(400);

  // Submit login
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const submitBtn = btns.find(b => b.textContent && b.textContent.includes('Sign In'));
    if (submitBtn) submitBtn.click();
  });
  await delay(3000);

  await injectCallouts(page, [
    { selector: 'span', textMatch: 'viewer', label: '1', position: 'top-left', offsetX: -5, offsetY: -5 },
    { selector: 'button', textMatch: 'Export CSV', label: '2', position: 'top-left', offsetX: 5, offsetY: 2 },
    { selector: 'table', label: '3', position: 'top-left', offsetX: 15, offsetY: 15 }
  ]);
  await saveScreen(page, 'screen_13_auditor_viewer_read_only.png');
  await removeCallouts(page);

  console.log('ALL SCREENSHOTS CAPTURED SUCCESSFULLY!');
  await browser.close();
})();
