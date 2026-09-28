from decimal import Decimal, ROUND_HALF_UP
from typing import Union

TWO_PLACES = Decimal("0.01")
VAT_RATE = Decimal("0.13")

def quantize_npr(amount: Union[Decimal, float, int, str]) -> Decimal:
    """
    Enforces strict two-decimal currency precision with banker's/commercial
    ROUND_HALF_UP rounding on all Nepalese Rupee (NPR) transactions.
    Eliminates IEEE-754 floating-point drift across accounting records.
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

def to_paisa(amount: Union[Decimal, float, int, str]) -> int:
    """Converts NPR to integer paisa (1 NPR = 100 paisa) for drift-free integer arithmetic."""
    dec = quantize_npr(amount)
    return int((dec * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))

def from_paisa(paisa: int) -> Decimal:
    """Converts integer paisa back to quantized Decimal NPR."""
    return quantize_npr(Decimal(paisa) / Decimal("100"))

def calculate_vat(
    taxable_subtotal: Union[Decimal, float, int, str],
    vat_enabled: bool = False,
    custom_rate: Union[Decimal, float, int, str] = VAT_RATE
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Computes statutory Nepal 13% VAT with strict Decimal arithmetic:
    Returns (taxable_subtotal, vat_amount, grand_total).
    """
    subtotal = quantize_npr(taxable_subtotal)
    if not vat_enabled:
        return subtotal, Decimal("0.00"), subtotal

    if not isinstance(custom_rate, Decimal):
        custom_rate = Decimal(str(custom_rate))

    # Support rate as percentage (13.0) or fraction (0.13)
    rate = custom_rate / Decimal("100") if custom_rate > Decimal("1.0") else custom_rate
    vat_amount = quantize_npr(subtotal * rate)
    grand_total = quantize_npr(subtotal + vat_amount)
    return subtotal, vat_amount, grand_total
