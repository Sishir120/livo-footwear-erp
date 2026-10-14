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

def calculate_vat_paisa(
    taxable_amount_paisa: int,
    vat_rate: Union[Decimal, float, int, str] = Decimal("13.0")
) -> tuple[int, int, int]:
    """
    Computes statutory Nepal 13% VAT with strict integer-paisa financial arithmetic:
    vat_amount_paisa = round(taxable_amount_paisa * 0.13)
    total_amount_paisa = taxable_amount_paisa + vat_amount_paisa
    Returns (taxable_amount_paisa, vat_amount_paisa, total_amount_paisa).
    """
    if not isinstance(vat_rate, Decimal):
        vat_rate = Decimal(str(vat_rate))
    rate_fraction = vat_rate / Decimal("100") if vat_rate > Decimal("1.0") else vat_rate
    vat_amount_paisa = int(round(Decimal(taxable_amount_paisa) * rate_fraction))
    total_amount_paisa = taxable_amount_paisa + vat_amount_paisa
    return taxable_amount_paisa, vat_amount_paisa, total_amount_paisa

def calculate_vat(
    taxable_subtotal: Union[Decimal, float, int, str],
    vat_enabled: bool = True,
    custom_rate: Union[Decimal, float, int, str] = Decimal("13.0")
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Computes statutory Nepal 13% VAT with strict integer-paisa arithmetic:
    Returns (taxable_subtotal, vat_amount, grand_total).
    """
    taxable_paisa = to_paisa(taxable_subtotal)
    if not vat_enabled:
        return quantize_npr(taxable_subtotal), Decimal("0.00"), quantize_npr(taxable_subtotal)

    _, vat_paisa, total_paisa = calculate_vat_paisa(taxable_paisa, vat_rate=custom_rate)
    return from_paisa(taxable_paisa), from_paisa(vat_paisa), from_paisa(total_paisa)

ONES_EN = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
           "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
           "Seventeen", "Eighteen", "Nineteen"]
TENS_EN = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

def _two_digits_to_words_en(n: int) -> str:
    if n < 20:
        return ONES_EN[n]
    tens = TENS_EN[n // 10]
    unit = ONES_EN[n % 10]
    return f"{tens} {unit}".strip()

def _three_digits_to_words_en(n: int) -> str:
    hundred = n // 100
    rem = n % 100
    res = ""
    if hundred > 0:
        res = f"{ONES_EN[hundred]} Hundred"
    if rem > 0:
        res = f"{res} {_two_digits_to_words_en(rem)}".strip()
    return res

def amount_to_words_en(amount_npr: Union[Decimal, float, int, str]) -> str:
    dec = quantize_npr(amount_npr)
    paisa_total = to_paisa(dec)
    rupees = paisa_total // 100
    paisa = paisa_total % 100

    if rupees == 0 and paisa == 0:
        return "Zero Rupees Only"

    parts = []
    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000
    hundreds = rupees

    if crore > 0:
        parts.append(f"{_two_digits_to_words_en(crore)} Crore")
    if lakh > 0:
        parts.append(f"{_two_digits_to_words_en(lakh)} Lakh")
    if thousand > 0:
        parts.append(f"{_two_digits_to_words_en(thousand)} Thousand")
    if hundreds > 0:
        parts.append(_three_digits_to_words_en(hundreds))

    rupees_str = " ".join(parts).strip()
    res = f"{rupees_str} Rupees" if rupees_str else ""
    if paisa > 0:
        paisa_str = f"{_two_digits_to_words_en(paisa)} Paisa"
        res = f"{res} and {paisa_str}" if res else f"{paisa_str}"

    return f"{res.strip()} Only"

NEP_DIGITS = [
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
]

def _two_digits_to_words_np(n: int) -> str:
    if 0 <= n < len(NEP_DIGITS):
        return NEP_DIGITS[n]
    return str(n)

def amount_to_words_np(amount_npr: Union[Decimal, float, int, str]) -> str:
    dec = quantize_npr(amount_npr)
    paisa_total = to_paisa(dec)
    rupees = paisa_total // 100
    paisa = paisa_total % 100

    if rupees == 0 and paisa == 0:
        return "शून्य रुपैयाँ मात्र"

    parts = []
    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000
    hundred = rupees // 100
    rem = rupees % 100

    if crore > 0:
        parts.append(f"{_two_digits_to_words_np(crore)} करोड")
    if lakh > 0:
        parts.append(f"{_two_digits_to_words_np(lakh)} लाख")
    if thousand > 0:
        parts.append(f"{_two_digits_to_words_np(thousand)} हजार")
    if hundred > 0:
        parts.append(f"{_two_digits_to_words_np(hundred)} सय")
    if rem > 0:
        parts.append(_two_digits_to_words_np(rem))

    rupees_str = " ".join(parts).strip()
    res = f"{rupees_str} रुपैयाँ" if rupees_str else ""
    if paisa > 0:
        paisa_str = f"{_two_digits_to_words_np(paisa)} पैसा"
        res = f"{res} र {paisa_str}" if res else f"{paisa_str}"

    return f"{res.strip()} मात्र"
