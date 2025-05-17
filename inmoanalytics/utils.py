import re

def parse_year_range(year_str):
    if not year_str:
        return None, None
    year_str = year_str.strip()
    match = re.match(r'(\d{4})\s*-\s*(\d{4})', year_str)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.match(r'>\s*(\d{4})', year_str)
    if match:
        return int(match.group(1)), None
    match = re.match(r'<\s*(\d{4})', year_str)
    if match:
        return None, int(match.group(1))
    match = re.match(r'(\d{4})', year_str)
    if match:
        year = int(match.group(1))
        return year, year
    return None, None