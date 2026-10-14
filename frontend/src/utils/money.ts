/**
 * LIVO Footwear ERP - Financial Operations
 * Ensures IEEE-754 precision compliance across the frontend by treating API monetary 
 * values as integer-cents (paisa) during calculation or safely parsing string decimals.
 */

export class Money {
  /** Internal representation: Integer minor units (Paisa / Cents) */
  private readonly paisa: number;

  private constructor(paisa: number) {
    if (!Number.isInteger(paisa)) {
      throw new Error(`Money must be initialized with an integer paisa value. Received: ${paisa}`);
    }
    this.paisa = paisa;
  }

  /**
   * Instantiates Money from a backend JSON Decimal string (e.g., "12.50").
   * Rounds strictly to avoid floating-point drift during the multiplication.
   */
  static fromDecimalString(str: string | number | undefined): Money {
    if (str === undefined || str === null || str === "") {
      return new Money(0);
    }
    
    // Convert to float safely, then to minor units, rounding to nearest integer
    const floatVal = typeof str === 'string' ? parseFloat(str) : str;
    if (isNaN(floatVal)) return new Money(0);
    
    return new Money(Math.round(floatVal * 100));
  }

  /**
   * Instantiates Money directly from minor units.
   */
  static fromPaisa(paisa: number): Money {
    return new Money(Math.round(paisa));
  }

  /**
   * Adds another Money instance.
   */
  add(other: Money): Money {
    return new Money(this.paisa + other.paisa);
  }

  /**
   * Subtracts another Money instance.
   */
  subtract(other: Money): Money {
    return new Money(this.paisa - other.paisa);
  }

  /**
   * Multiplies by a float scalar (e.g., quantity).
   */
  multiply(factor: number): Money {
    return new Money(Math.round(this.paisa * factor));
  }

  /**
   * Exports as a Decimal String compatible with backend API payloads.
   */
  toDecimalString(): string {
    return (this.paisa / 100).toFixed(2);
  }

  /**
   * Exports as a primitive float number (Use ONLY for UI formatting engines that strictly require numbers).
   * Do NOT use for further arithmetic.
   */
  toNumberUnsafe(): number {
    return this.paisa / 100;
  }

  /**
   * Returns a formatted NPR currency string.
   */
  format(): string {
    return (this.paisa / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
}
