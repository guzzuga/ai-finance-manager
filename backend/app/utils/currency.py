"""Indonesian currency string parsing utilities."""
import re


def parse_indonesian_currency(text: str) -> int:
    """Parse Indonesian currency strings into integer amounts.

    Handles formats like:
        '20 ribu' -> 20000
        '1,5 juta' -> 1500000
        '50rb' -> 50000
        '2jt' -> 2000000
        '150.000' -> 150000
        'Rp 25.000' -> 25000
        '35000' -> 35000
    """
    if not text:
        return 0

    s = text.strip().lower()
    s = re.sub(r'^(rp\.?|idr)\s*', '', s)

    multipliers = {
        'jt': 1_000_000, 'juta': 1_000_000,
        'rb': 1_000, 'ribu': 1_000,
        'k': 1_000, 'm': 1_000_000,
    }

    mult_pattern = r'([\d]+[.,]?\d*)\s*(jt|juta|rb|ribu|m)\b'
    m = re.search(mult_pattern, s)
    if m:
        num_str = m.group(1).replace(',', '.')
        mult_key = m.group(2)
        parts = num_str.split('.')
        if len(parts) > 2:
            num_str = ''.join(parts[:-1]) + '.' + parts[-1]
        elif len(parts) == 2 and len(parts[1]) == 3:
            num_str = parts[0] + parts[1]
        try:
            value = float(num_str) * multipliers[mult_key]
            return int(value)
        except (ValueError, KeyError):
            pass

    s_clean = re.sub(r'[^\d.,]', '', s)
    if not s_clean:
        return 0

    if re.match(r'^\d+,\d{1,2}$', s_clean):
        return int(float(s_clean.replace(',', '.')))

    s_digits = re.sub(r'[.,]', '', s_clean)
    try:
        value = int(s_digits)
    except ValueError:
        return 0

    if value < 1000 and '.' not in s_clean and ',' not in s_clean:
        if value >= 10:
            value *= 1000

    return value
