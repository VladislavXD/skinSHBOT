from decimal import Decimal, ROUND_HALF_UP


RATES_FROM_RUB: dict[str, Decimal] = {
    "rub": Decimal("1"),
    "usd": Decimal("0.0112"),
    "uzs": Decimal("145"),
}

CURRENCY_LABEL: dict[str, str] = {
    "rub": "RUB",
    "usd": "USD",
    "uzs": "UZS",
}


def convert_from_rub(amount_rub: Decimal, currency: str) -> Decimal:
    rate = RATES_FROM_RUB.get(currency, RATES_FROM_RUB["rub"])
    return (amount_rub * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money_from_rub(amount_rub: Decimal, currency: str) -> str:
    converted = convert_from_rub(amount_rub, currency)
    if currency == "uzs":
        converted = converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{converted} {CURRENCY_LABEL.get(currency, 'RUB')}"
