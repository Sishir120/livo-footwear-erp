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

