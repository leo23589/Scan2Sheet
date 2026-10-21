import re

def parse_receipt_data(text):
    if "Rapport Mensuel" in text or "Ticket Z" in text:
        match_total = re.search(r"Total des ventes\s*(\d+[.,]\d{2})", text, re.IGNORECASE)
        if match_total:
            total_mensuel = float(match_total.group(1).replace(',', '.'))
            return {"type": "mensuel", "total_attendu": total_mensuel}
        return {"type": "mensuel", "total_attendu": 0.0}

    data = {
        "type": "journalier",
        "Date": 0,
        "Espece": 0.0,
        "T.Resto": 0.0,
        "CB": 0.0,
        "Total": 0.0,
        "Alcols": 0.0
    }

    match_date = re.search(r"Date du rapport\s*[:]?\s*(\d{2})", text, re.IGNORECASE)
    if match_date:
        data["Date"] = int(match_date.group(1))

    patterns = {
        "Espece": r"Total ventes esp[èe]ces\s*(\d+[.,]\d{2})",
        "CB": r"\bCB\s*(\d+[.,]\d{2})",
        "Total": r"Grand Total\s*(\d+[.,]\d{2})",
        "Alcols": r"20,00%.*?(\d+[.,]\d{2})",
        "T.Resto": r"\bTR\s*(\d+[.,]\d{2})"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).replace(',', '.')
            data[key] = float(value)

    return data