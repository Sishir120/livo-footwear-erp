/**
 * LIVO Footwear ERP - Statutory Integer Paisa Math Engine
 * Eliminates IEEE-754 floating-point drift (0.1 + 0.2 artifacts)
 * by calculating all currency values in integer paisa (1 NPR = 100 paisa).
 */

export function toPaisa(npr: number | string): number {
  if (npr === null || npr === undefined) return 0;
  const str = String(npr).trim();
  if (!str || isNaN(Number(str))) return 0;

  const sign = str.startsWith("-") ? -1 : 1;
  const clean = str.replace("-", "");
  const [whole, decimal = ""] = clean.split(".");
  const cents = (decimal + "00").slice(0, 2);

  return sign * (parseInt(absWhole(whole), 10) * 100 + parseInt(cents, 10));
}

function absWhole(str: string): string {
  return str.replace(/[^0-9]/g, "") || "0";
}

export function fromPaisa(paisa: number, formatThousands: boolean = true): string {
  if (isNaN(paisa) || paisa === null || paisa === undefined) return "0.00";
  const sign = paisa < 0 ? "-" : "";
  const abs = Math.abs(Math.round(paisa));
  const whole = Math.floor(abs / 100);
  const cents = String(abs % 100).padStart(2, "0");
  const wholeStr = formatThousands ? whole.toLocaleString("en-US") : String(whole);
  return `${sign}${wholeStr}.${cents}`;
}

export function calculateVat(taxablePaisa: number): {
  vatPaisa: number;
  grandTotalPaisa: number;
} {
  const roundedTaxable = Math.round(taxablePaisa);
  const vatPaisa = Math.round(roundedTaxable * 0.13);
  const grandTotalPaisa = roundedTaxable + vatPaisa;
  return { vatPaisa, grandTotalPaisa };
}

// Global CSS & inline style helper enforcing tabular-nums formatting
export const TABULAR_NUMS_STYLE = {
  fontVariantNumeric: "tabular-nums",
  fontFamily: "'Fira Code', 'Roboto Mono', ui-monospace, monospace"
} as const;

// Alias maintaining full compatibility with calculateVatPaisa callers
export function calculateVatPaisa(subtotalPaisa: number, vatRatePercent: number = 13): {
  taxablePaisa: number;
  vatPaisa: number;
  grandTotalPaisa: number;
} {
  const roundedTaxable = Math.round(subtotalPaisa);
  const vatPaisa = vatRatePercent === 13 ? Math.round(roundedTaxable * 0.13) : Math.round((roundedTaxable * vatRatePercent) / 100);
  const grandTotalPaisa = roundedTaxable + vatPaisa;
  return { taxablePaisa: subtotalPaisa, vatPaisa, grandTotalPaisa };
}

const NEP_DIGITS = [
  "शून्य", "एक", "दुई", "तीन", "चार", "पाँच", "छ", "सात", "आठ", "नौ",
  "दश", "एघार", "बाह्र", "तेह्र", "चौध", "पन्ध्र", "सोह्र", "सत्र", "अठार", "उन्नाइस",
  "बीस", "एक्काइस", "बाइस", "तेइस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताइस", "अठ्ठाइस", "उनन्तीस",
  "तीस", "एकतीस", "बत्तीस", "तेत्तीस", "चौतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड्तीस", "उनन्चालीस",
  "चालीस", "एकचालीस", "बयालीस", "त्रिचालीस", "चवालीस", "पैंतालीस", "छयालीस", "सच्चालीस", "अठचालीस", "उनञ्चास",
  "पचास", "एकाउन्न", "बाउन्न", "त्रिपन्न", "चौवन्न", "पचपन्न", "छप्पन्न", "सन्ताउन्न", "अन्ठाउन्न", "उनन्साठी",
  "साठी", "एकसट्ठी", "बासट्ठी", "त्रिसट्ठी", "चौंसट्ठी", "पैंसट्ठी", "छयसट्ठी", "सत्सट्ठी", "अठसट्ठी", "उनन्सत्तरी",
  "सत्तरी", "एकहत्तर", "बहत्तर", "त्रिहत्तर", "चौहत्तर", "पचहत्तर", "छयहत्तर", "सतहत्तर", "अठहत्तर", "उनासी",
  "असी", "एकासी", "बयासी", "त्रियासी", "चौरासी", "पचासी", "छयासी", "सतासी", "अठासी", "उनान्नब्बे",
  "नब्बे", "एकान्नब्बे", "बयानब्बे", "त्रियान्नब्बे", "चौरानब्बे", "पञ्चानब्बे", "छयान्नब्बे", "सन्तानब्बे", "अन्ठानब्बे", "उनान्सय"
];

const ONES_EN = [
  "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
  "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
  "Seventeen", "Eighteen", "Nineteen"
];

const TENS_EN = [
  "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
];

function twoDigitsEn(n: number): string {
  if (n < 20) return ONES_EN[n];
  const tens = TENS_EN[Math.floor(n / 10)];
  const ones = ONES_EN[n % 10];
  return `${tens} ${ones}`.trim();
}

function threeDigitsEn(n: number): string {
  const hundred = Math.floor(n / 100);
  const rem = n % 100;
  let res = "";
  if (hundred > 0) res = `${ONES_EN[hundred]} Hundred`;
  if (rem > 0) res = `${res} ${twoDigitsEn(rem)}`.trim();
  return res;
}

export function amountToEnglishWords(amountNpr: number | string): string {
  const paisaTotal = toPaisa(amountNpr);
  let rupees = Math.floor(Math.abs(paisaTotal) / 100);
  const paisa = Math.abs(paisaTotal) % 100;

  if (rupees === 0 && paisa === 0) return "Zero Rupees Only";

  const parts: string[] = [];
  const crore = Math.floor(rupees / 10000000);
  rupees %= 10000000;
  const lakh = Math.floor(rupees / 100000);
  rupees %= 100000;
  const thousand = Math.floor(rupees / 1000);
  rupees %= 1000;
  const hundreds = rupees;

  if (crore > 0) parts.push(`${twoDigitsEn(crore)} Crore`);
  if (lakh > 0) parts.push(`${twoDigitsEn(lakh)} Lakh`);
  if (thousand > 0) parts.push(`${twoDigitsEn(thousand)} Thousand`);
  if (hundreds > 0) parts.push(threeDigitsEn(hundreds));

  const rupeesStr = parts.join(" ").trim();
  let res = rupeesStr ? `${rupeesStr} Rupees` : "";
  if (paisa > 0) {
    const paisaStr = `${twoDigitsEn(paisa)} Paisa`;
    res = res ? `${res} and ${paisaStr}` : paisaStr;
  }
  return `${res.trim()} Only`;
}

export function amountToNepaliWords(amountNpr: number | string): string {
  const paisaTotal = toPaisa(amountNpr);
  let rupees = Math.floor(Math.abs(paisaTotal) / 100);
  const paisa = Math.abs(paisaTotal) % 100;

  if (rupees === 0 && paisa === 0) return "शून्य रुपैयाँ मात्र";

  const parts: string[] = [];
  const crore = Math.floor(rupees / 10000000);
  rupees %= 10000000;
  const lakh = Math.floor(rupees / 100000);
  rupees %= 100000;
  const thousand = Math.floor(rupees / 1000);
  rupees %= 1000;
  const hundred = Math.floor(rupees / 100);
  const rem = rupees % 100;

  if (crore > 0) parts.push(`${NEP_DIGITS[crore] || crore} करोड`);
  if (lakh > 0) parts.push(`${NEP_DIGITS[lakh] || lakh} लाख`);
  if (thousand > 0) parts.push(`${NEP_DIGITS[thousand] || thousand} हजार`);
  if (hundred > 0) parts.push(`${NEP_DIGITS[hundred] || hundred} सय`);
  if (rem > 0) parts.push(NEP_DIGITS[rem] || String(rem));

  const rupeesStr = parts.join(" ").trim();
  let res = rupeesStr ? `${rupeesStr} रुपैयाँ` : "";
  if (paisa > 0) {
    const paisaStr = `${NEP_DIGITS[paisa] || paisa} पैसा`;
    res = res ? `${res} र ${paisaStr}` : paisaStr;
  }
  return `${res.trim()} मात्र`;
}


