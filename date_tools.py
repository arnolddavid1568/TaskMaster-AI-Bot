"""
Date utilities: age calculation, difference between two dates, and
countdowns to a future date. Accepts a handful of common date formats.
"""
from datetime import date, datetime

_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"]


def parse_date(text: str) -> date:
    text = text.strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Couldn't parse date '{text}'. Try formats like 2000-05-20 or 20/05/2000.")


def calculate_age(birth_date_str: str, as_of: date = None) -> dict:
    birth = parse_date(birth_date_str)
    today = as_of or date.today()
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    # next birthday
    try:
        next_bday = birth.replace(year=today.year)
    except ValueError:  # Feb 29 on non-leap year
        next_bday = birth.replace(year=today.year, day=28, month=3)
    if next_bday < today:
        next_bday = next_bday.replace(year=today.year + 1)
    days_to_next = (next_bday - today).days

    total_days = (today - birth).days
    return {
        "years": years,
        "total_days": total_days,
        "days_to_next_birthday": days_to_next,
        "birth_date": birth.isoformat(),
    }


def date_difference(date1_str: str, date2_str: str) -> dict:
    d1 = parse_date(date1_str)
    d2 = parse_date(date2_str)
    delta = abs((d2 - d1).days)
    years = delta // 365
    months = (delta % 365) // 30
    days = (delta % 365) % 30
    return {"total_days": delta, "approx_years": years, "approx_months": months, "approx_days": days}


def countdown(target_date_str: str) -> dict:
    target = parse_date(target_date_str)
    today = date.today()
    delta = (target - today).days
    if delta >= 0:
        return {"days_remaining": delta, "status": "upcoming", "target_date": target.isoformat()}
    else:
        return {"days_remaining": abs(delta), "status": "past", "target_date": target.isoformat()}
