import re

def parse_receipt_data(text, date_jour):
    data = {
        "Date": date_jour,
        "Espece": 0.0,
        "T.Resto": 0.0,
        "CB": 0.0,
        "Total": 0.0,
        "Alcols": 0.0
    }
    
    patterns = {
        "Espece": r"Espece\s*[:\-]?\s*(\d+[.,]\d{2})",
        "T.Resto": r"T\.Resto\s*[:\-]?\s*(\d+[.,]\d{2})",
        "CB": r"CB\s*[:\-]?\s*(\d+[.,]\d{2})",
        "Total": r"Total\s*[:\-]?\s*(\d+[.,]\d{2})",
        "Alcols": r"Alcols\s*[:\-]?\s*(\d+[.,]\d{2})"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(',', '.')
            data[key] = float(value)
            
    return data
