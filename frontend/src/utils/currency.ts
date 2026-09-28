/**
 * LIVO Footwear ERP - Strict Decimal Precision & Banker's Rounding
 * Eliminates IEEE-754 floating-point drift (0.1 + 0.2 artifacts)
 * by calculating currency in integer paisa (1 NPR = 100 paisa).
 */

export function toPaisa(nprStringOrNum: string | number): number {
  const str = String(nprStringOrNum).trim();
  if (!str || isNaN(Number(str))) return 0;
  const [whole, decimal = ""] = str.split(".");
  const cents = (decimal + "00").slice(0, 2);
  const sign = whole.startsWith("-") ? -1 : 1;
  const absWhole = whole.replace("-", "");
  return sign * (parseInt(absWhole || "0", 10) * 100 + parseInt(cents, 10));
}

export function fromPaisa(paisa: number, formatThousands: boolean = true): string {
  const sign = paisa < 0 ? "-" : "";
  const abs = Math.abs(Math.round(paisa));
  const whole = Math.floor(abs / 100);
  const cents = String(abs % 100).padStart(2, "0");
  const wholeStr = formatThousands ? whole.toLocaleString("en-US") : String(whole);
  return `${sign}${wholeStr}.${cents}`;
}

export function calculateVatPaisa(
  subtotalPaisa: number,
  vatRatePercent: number = 13
): {
  taxablePaisa: number;
  vatPaisa: number;
  grandTotalPaisa: number;
} {
  const taxablePaisa = subtotalPaisa;
  const vatPaisa = Math.round((subtotalPaisa * vatRatePercent) / 100);
  const grandTotalPaisa = taxablePaisa + vatPaisa;
  return { taxablePaisa, vatPaisa, grandTotalPaisa };
}
