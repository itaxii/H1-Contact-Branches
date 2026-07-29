from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def ratio(numerator, denominator):
    numerator_value = to_decimal(numerator)
    denominator_value = to_decimal(denominator)
    if numerator_value is None or denominator_value in (None, Decimal("0")):
        return None
    return numerator_value / denominator_value


def yoy_rate(current, previous):
    current_value = to_decimal(current)
    previous_value = to_decimal(previous)
    if current_value is None or previous_value in (None, Decimal("0")):
        return None
    return ratio(current_value - previous_value, previous_value)


def quantize_half_up(value, decimals=0):
    decimal_value = to_decimal(value)
    if decimal_value is None:
        return None
    quantum = Decimal("1").scaleb(-decimals)
    return decimal_value.quantize(quantum, rounding=ROUND_HALF_UP)


def format_percent(value, decimals=1):
    decimal_value = to_decimal(value)
    if decimal_value is None:
        return "N/A"
    displayed = quantize_half_up(decimal_value * Decimal("100"), decimals)
    return f"{displayed:.{decimals}f}%"


def format_money(value, compact=False):
    decimal_value = to_decimal(value)
    if decimal_value is None:
        decimal_value = Decimal("0")
    negative = decimal_value < 0
    absolute = abs(decimal_value)

    if compact:
        if absolute >= Decimal("1000000"):
            amount = quantize_half_up(absolute / Decimal("1000000"), 1)
            text = f"EGP {amount:.1f}M"
        elif absolute >= Decimal("1000"):
            amount = quantize_half_up(absolute / Decimal("1000"), 1)
            text = f"EGP {amount:.1f}K"
        else:
            amount = quantize_half_up(absolute, 0)
            text = f"EGP {amount:,.0f}"
    else:
        amount = quantize_half_up(absolute, 0)
        text = f"{amount:,.0f}"

    return f"({text})" if negative else text


def format_count(value):
    decimal_value = to_decimal(value)
    if decimal_value is None:
        return "0"
    return f"{quantize_half_up(decimal_value, 0):,.0f}"


def decimal_text(value):
    decimal_value = to_decimal(value)
    if decimal_value is None:
        return None
    text = format(decimal_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class MetricRegistry:
    def __init__(self):
        self._metrics = {}

    def register(
        self,
        metric_id,
        label,
        numerator,
        denominator,
        decimals=1,
        source_rate=None,
        report_area=None,
    ):
        numerator_value = to_decimal(numerator)
        denominator_value = to_decimal(denominator)
        result = ratio(numerator_value, denominator_value)
        source_value = to_decimal(source_rate)
        self._metrics[metric_id] = {
            "metric_id": metric_id,
            "label": label,
            "report_area": report_area or metric_id.split(".", 1)[0],
            "numerator": decimal_text(numerator_value),
            "denominator": decimal_text(denominator_value),
            "value": decimal_text(result),
            "display": format_percent(result, decimals),
            "decimals": decimals,
            "source_rate": decimal_text(source_value),
            "source_display": format_percent(source_value, decimals) if source_value is not None else None,
        }
        return result

    def to_json(self):
        result = {}
        for metric_id, metric in self._metrics.items():
            item = dict(metric)
            item["value_numeric"] = float(item["value"]) if item["value"] is not None else None
            result[metric_id] = item
        return result

    def validate(self):
        failures = []
        for metric_id, metric in self._metrics.items():
            expected_value = ratio(metric["numerator"], metric["denominator"])
            actual_value = to_decimal(metric["value"])
            expected_display = format_percent(expected_value, metric["decimals"])
            actual_display = metric["display"]
            if actual_value != expected_value or actual_display != expected_display:
                failures.append(
                    {
                        "metric_id": metric_id,
                        "label": metric["label"],
                        "numerator": metric["numerator"],
                        "denominator": metric["denominator"],
                        "expected_value": decimal_text(expected_value),
                        "actual_value": decimal_text(actual_value),
                        "expected_display": expected_display,
                        "actual_display": actual_display,
                    }
                )
        return failures

    def rounding_changes(self):
        changes = []
        for metric in self._metrics.values():
            previous_display = metric.get("source_display")
            corrected_display = metric["display"]
            if previous_display is None or previous_display == corrected_display:
                continue
            changes.append(
                {
                    "metric_id": metric["metric_id"],
                    "report_area": metric["report_area"],
                    "label": metric["label"],
                    "previous_display": previous_display,
                    "corrected_display": corrected_display,
                    "numerator": metric["numerator"],
                    "denominator": metric["denominator"],
                }
            )
        return sorted(changes, key=lambda item: (item["report_area"], item["label"]))
