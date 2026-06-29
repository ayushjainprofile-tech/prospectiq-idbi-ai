import re

def score_prospect(info: dict) -> int:
    """Scores a lead out of 99 based on provided information."""
    score = 40
    
    income_val = info.get("income", 0)
    if isinstance(income_val, (int, float)):
        income = int(income_val)
    else:
        try:
            # Remove any non-digit characters (currency symbols, commas, spaces)
            cleaned_income = re.sub(r'[^\d]', '', str(income_val))
            income = int(cleaned_income) if cleaned_income else 0
        except ValueError:
            income = 0

    if income > 100000:
        score += 25
    elif income > 60000:
        score += 18
    elif income > 30000:
        score += 10

    intent_map = {
        "home_loan": 20, 
        "car_loan": 18, 
        "fd": 14, 
        "savings": 10, 
        "insurance": 12,
        "credit_card": 15,
        "nri_account": 22,
        "demat": 16
    }
    score += intent_map.get(info.get("product", ""), 8)

    employed = info.get("employed", "")
    if employed is True or str(employed).lower() in ("yes", "true"):
        score += 10

    existing_customer = info.get("existing_customer", "")
    if existing_customer is True or str(existing_customer).lower() in ("yes", "true"):
        score += 5

    return min(score, 99)

def get_tag(score: int) -> str:
    """Returns a tag (HOT, WARM, NEW) based on the score."""
    if score >= 85:
        return "HOT"
    if score >= 65:
        return "WARM"
    return "NEW"

def get_product_label(product: str) -> str:
    labels = {
        "home_loan": "Home Loan",
        "car_loan": "Car Loan",
        "fd": "Fixed Deposit",
        "savings": "Savings Account",
        "insurance": "Insurance",
        "credit_card": "Credit Card",
        "nri_account": "NRI Account",
        "demat": "Demat Account"
    }
    return labels.get(product, product.replace("_", " ").title())
