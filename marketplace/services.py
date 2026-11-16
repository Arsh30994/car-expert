"""Deterministic marketplace domain services; no model-generated specifications or scores."""

from decimal import Decimal, ROUND_HALF_UP


def _decimal(value, default=Decimal("0")):
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return default


def rank_cars(cars, profile):
    """Filter hard constraints, then rank eligible cars with explainable signals.

    The first release uses explicit, conservative weights. Missing fields do not
    receive a fabricated positive score; they contribute zero to that dimension.
    """
    budget = _decimal(profile.get("budget"))
    family_size = int(profile.get("family_size") or 1)
    preferred_fuels = {
        str(item).strip().casefold()
        for item in (profile.get("fuel_preferences") or [])
        if str(item).strip()
    }
    weights = {
        "budget_fit": Decimal("25"),
        "safety": Decimal("20"),
        "efficiency": Decimal("15"),
        "family_fit": Decimal("15"),
        "maintenance": Decimal("10"),
        "city_practicality": Decimal("10"),
        "fuel_preference": Decimal("5"),
    }
    ranked = []
    for car in cars:
        price = _decimal(car.get("price"))
        seats = int(car.get("seats") or 0)
        fuel = str(car.get("fuel_type") or "").casefold()
        if budget and price > budget:
            continue
        if family_size > seats:
            continue
        if preferred_fuels and fuel not in preferred_fuels:
            continue

        signals = {}
        signals["budget_fit"] = Decimal("100") if budget and price <= budget else Decimal("0")
        safety = _decimal(car.get("safety_score"))
        signals["safety"] = min(safety / Decimal("5") * 100, Decimal("100"))
        mileage = _decimal(car.get("mileage"))
        signals["efficiency"] = min(mileage / Decimal("25") * 100, Decimal("100"))
        signals["family_fit"] = min(Decimal(seats) / max(family_size, 1) * 100, Decimal("100"))
        maintenance = _decimal(car.get("maintenance_cost"))
        signals["maintenance"] = max(Decimal("0"), Decimal("100") - maintenance / Decimal("500"))
        clearance = _decimal(car.get("ground_clearance"))
        signals["city_practicality"] = min(clearance / Decimal("200") * 100, Decimal("100"))
        signals["fuel_preference"] = Decimal("100") if not preferred_fuels or fuel in preferred_fuels else Decimal("0")

        score = sum((signals[key] * weight / 100 for key, weight in weights.items()), Decimal("0"))
        reasons = []
        tradeoffs = []
        if budget and price <= budget:
            reasons.append("Within your stated budget")
        if safety:
            reasons.append(f"Published safety score: {safety}/5")
        if mileage:
            reasons.append(f"Listed efficiency: {mileage} km/l or km/kg equivalent as supplied")
        if seats >= family_size:
            reasons.append(f"Seats your stated family size ({seats} seats)")
        if maintenance:
            tradeoffs.append("Maintenance figure is an estimate and depends on variant, usage and service network")
        if not safety:
            tradeoffs.append("Safety rating is not available in the catalogue")
        ranked.append({
            "car": car,
            "score": float(score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "score_breakdown": {key: float(value.quantize(Decimal("0.1"))) for key, value in signals.items()},
            "reasons": reasons,
            "tradeoffs": tradeoffs,
        })
    return sorted(ranked, key=lambda item: (-item["score"], str(item["car"].get("name", ""))))


def calculate_emi(principal, annual_interest_rate, tenure_months):
    principal = _decimal(principal)
    annual_rate = _decimal(annual_interest_rate)
    if principal <= 0:
        raise ValueError("Principal must be greater than zero.")
    if annual_rate < 0:
        raise ValueError("Annual interest rate cannot be negative.")
    if isinstance(tenure_months, bool) or int(tenure_months) != tenure_months or int(tenure_months) <= 0:
        raise ValueError("Tenure must be a positive whole number of months.")
    months = int(tenure_months)
    monthly_rate = annual_rate / Decimal("1200")
    if monthly_rate == 0:
        emi = principal / months
    else:
        factor = (Decimal("1") + monthly_rate) ** months
        emi = principal * monthly_rate * factor / (factor - Decimal("1"))
    emi = emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_payment = (emi * months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "monthly_emi": float(emi),
        "total_payment": float(total_payment),
        "total_interest": float((total_payment - principal).quantize(Decimal("0.01"))),
    }
