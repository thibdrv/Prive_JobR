"""Reading a job posting: years of experience and languages it asks for, contract, work mode, salary, skills."""
import re

JUNIOR_WORDS = ["junior", "jr", "graduate", "entry level", "entry-level", "intern", "internship",
                "trainee", "apprentice"]

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_NUMBER = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"
# "3+ years", "3-5 years", "three years", "5 yrs", and in Greek "3 χρόνια", "3 έτη"
_YEARS = re.compile(
    rf"\b{_NUMBER}\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*\d{{1,2}}\s*\+?\s*)?(?:years?|yrs?)\b"
    r"|(\d{1,2})\s*\+?\s*(?:(?:-|–)\s*\d{1,2}\s*)?(?:χρόνια|χρόνων|έτη|ετών)",
    re.IGNORECASE)
_ABOUT_EXPERIENCE = re.compile(r"experience|εμπειρ", re.IGNORECASE)
# "our company has 20 years of experience" is about the employer, not about you
_ABOUT_EMPLOYER = re.compile(r"\b(we|we've|our|company|founded|since|history|track record)\b", re.IGNORECASE)
# "a 3 years contract", "2 years ago", "5 years old": a length of time, not experience
_NOT_EXPERIENCE = re.compile(r"^\W*(contract|fixed|ago|old|warranty|guarantee|lease)\b", re.IGNORECASE)


def years_required(text: str) -> int | None:
    """The most experience the text asks for, in years; None when it doesn't say."""
    found = []
    for match in _YEARS.finditer(text):
        around = text[max(0, match.start() - 60):match.end() + 60]
        before = text[max(0, match.start() - 40):match.start()]
        if (not _ABOUT_EXPERIENCE.search(around) or _ABOUT_EMPLOYER.search(before)
                or _NOT_EXPERIENCE.search(text[match.end():match.end() + 20])):
            continue
        number = match.group(1) or match.group(2)
        years = int(number) if number.isdigit() else _NUMBER_WORDS[number.lower()]
        if years <= 15:  # larger numbers are company ages, not requirements
            found.append(years)
    return max(found) if found else None


# Alphabets: a posting written in one of these is for people who read that language.
_ALPHABETS = {"greek": r"[\u0370-\u03ff\u1f00-\u1fff]", "russian": r"[\u0400-\u04ff]",
              "ukrainian": r"[\u0400-\u04ff]", "bulgarian": r"[\u0400-\u04ff]",
              "arabic": r"[\u0600-\u06ff]", "hebrew": r"[\u0590-\u05ff]"}
# Words right next to a language name that show it is about speaking it ("fluent Greek", "Greek and English")
_ABOUT_LANGUAGE = re.compile(r"language|speak|spoken|fluen|native|proficien|knowledge|written|verbal|command"
                             r"|mother tongue|bilingual|english|french|excellent|level|c1|c2|b2", re.IGNORECASE)
_OPTIONAL = re.compile(r"advantage|a plus|\bplus\b|asset|preferred|preferabl|desirable|beneficial|nice to have"
                       r"|bonus|ideally|considered|optional|not required|not mandatory|not essential"
                       r"|class|course|lesson|tuition", re.IGNORECASE)  # "Greek language classes" is a perk
# "Greek market", "Greek-speaking customers": about the clients, not about you
_ABOUT_OTHERS = re.compile(r"[\s-]*(?:speaking\s+)?(?:market|customer|client|communit|audience|partner|team"
                           r"|government|company|companies|subsidiar)", re.IGNORECASE)
_SENTENCE_END = r"[.!?;•·]"


def requires_language(title: str, text: str, language: str) -> bool:
    """True when the posting asks for the language (and not just as a plus)."""
    language = language.strip().lower()
    alphabet = _ALPHABETS.get(language)
    if alphabet:
        if re.search(alphabet, title):
            return True
        letters = len(re.findall(r"[^\W\d_]", text))
        if letters and len(re.findall(alphabet, text)) / letters > 0.3:
            return True
    if re.search(rf"\b{re.escape(language)}\b", title, re.IGNORECASE):
        return True
    for match in re.finditer(rf"\b{re.escape(language)}\b", text, re.IGNORECASE):
        before = re.split(_SENTENCE_END, text[max(0, match.start() - 40):match.start()])[-1]
        after = re.split(_SENTENCE_END, text[match.end():match.end() + 120])[0]
        if _ABOUT_OTHERS.match(after):
            continue
        if _ABOUT_LANGUAGE.search(before + match.group() + after[:40]) and not _OPTIONAL.search(after):
            return True
    return False


# Contract and work mode, in the order they are checked: the first that fits wins.
_CONTRACTS = [
    ("Stage", r"intern(ship)?|trainee(ship)?|apprentice(ship)?|placement"),
    ("Temps partiel", r"part[\s-]?time"),
    ("Contrat / freelance", r"freelance|contractor|fixed[\s-]term|temporary|contract basis|\d+[\s-]months? contract"),
    ("Temps plein", r"full[\s-]?time|permanent"),
]
_WORK_MODES = [
    ("Hybride", r"hybrid"),
    ("Télétravail", r"fully remote|100% remote|remote[\s-](position|role|job|first|only)|work from home|wfh"
                    r"|remote working is possible"),
    ("Sur place", r"on[\s-]?site|office[\s-]based|in the office|from the office|in-office"),
]


def contract_type(title: str, text: str) -> str:
    """"Temps plein", "Stage"...; the title is trusted first, "" when nothing says."""
    for words in (title, text):
        for name, pattern in _CONTRACTS:
            if re.search(rf"\b(?:{pattern})\b", words, re.IGNORECASE):
                return name
    return ""


def work_mode(location: str, text: str) -> str:
    """"Sur place", "Hybride" or "Télétravail"; "" when nothing says."""
    for words in (location, text):
        for name, pattern in _WORK_MODES:
            if re.search(rf"\b(?:{pattern})\b", words, re.IGNORECASE):
                return name
    if re.fullmatch(r"(?i)\s*remote\s*", location or ""):
        return "Télétravail"
    return ""


_CURRENCY = r"€|eur(?:os?)?\b|\$|usd\b|£|gbp\b"
_NUMBER_AMOUNT = r"\d{1,3}(?:[,.\s]\d{3})+(?:[.,]\d{2})?|\d+(?:[.,]\d+)?"
# "€1,500 - €2,000", "EUR 25k-30k", "1.800€", "€ 30,000", "$60,000 to $80,000"
_SALARY = re.compile(
    rf"(?P<c1>{_CURRENCY})?\s*(?P<a>{_NUMBER_AMOUNT})\s*(?P<ak>k\b)?\s*(?P<c2>{_CURRENCY})?"
    rf"(?:\s*(?:-|–|—|to)\s*(?P<c3>{_CURRENCY})?\s*(?P<b>{_NUMBER_AMOUNT})\s*(?P<bk>k\b)?\s*(?P<c4>{_CURRENCY})?)?",
    re.IGNORECASE)
_ABOUT_SALARY = re.compile(r"salar|remunerat|gross|\bnet\b|per month|monthly|/month|per annum|p\.a\.|annual"
                           r"|yearly|per year|package|compensation|\bpay\b|wage", re.IGNORECASE)
_PER_YEAR = re.compile(r"per annum|p\.a\.|annual|yearly|per year|/year|a year", re.IGNORECASE)
_PER_MONTH = re.compile(r"per month|monthly|/month|a month|p\.m\.|/mo\b|μηνιαίως", re.IGNORECASE)
_PER_HOUR_OR_DAY = re.compile(r"^\W*(per|an|a|/)\s*(hour|hr|day)|^\W*(hourly|daily)", re.IGNORECASE)
# "$200 million in annual revenue", "raised €5M": money about the company, not your pay
_NOT_PAY = re.compile(r"^\s*\+?\s*(million|billion|bn|mn|m\b)|revenue|turnover|funding|raised|valuation|investment",
                      re.IGNORECASE)


def _to_number(amount: str, thousands: bool) -> float:
    amount = re.sub(r"[.,]\d{2}$", "", amount.strip())  # "1,500.00" -> "1,500"
    if re.search(r"[,.\s]\d{3}$", amount):
        value = float(re.sub(r"[,.\s]", "", amount))
    else:
        value = float(amount.replace(",", "."))
    return value * 1000 if thousands else value


def salary_range(text: str) -> tuple[int, int, str] | None:
    """(lowest, highest, currency) in gross per month, when the posting states a salary."""
    for match in _SALARY.finditer(text):
        currency = next((match.group(g) for g in ("c1", "c2", "c3", "c4") if match.group(g)), None)
        if not currency:
            continue
        around = text[max(0, match.start() - 60):match.end() + 40]
        after = text[match.end():match.end() + 30]
        before = re.split(r"[.!?;:]\s", text[max(0, match.start() - 30):match.start()])[-1]  # same sentence only
        if (not _ABOUT_SALARY.search(around) or _PER_HOUR_OR_DAY.search(after)
                or _NOT_PAY.search(after) or _NOT_PAY.search(before)):
            continue
        currency = currency.lower()
        currency = "$" if currency in ("$", "usd") else "£" if currency in ("£", "gbp") else "€"
        thousands = bool(match.group("ak") or match.group("bk"))  # "25k-30k" and "25-30k"
        low = _to_number(match.group("a"), thousands)
        high = _to_number(match.group("b"), thousands) if match.group("b") else low
        # the period written right after the amount wins: "8,000 gross per month. Annual bonus" is monthly
        monthly = _PER_MONTH.search(after)
        if low >= 12000 or (not monthly and _PER_YEAR.search(around)):
            low, high = low / 12, high / 12
        if not 300 <= low <= high <= 50000:  # hourly rates, bonuses, typos
            continue
        return round(low), round(high), currency
    return None


def salary_text(salary: tuple[int, int, str] | None) -> str:
    """"1 500–2 000 €/mois" for the results file."""
    if not salary:
        return ""
    low, high, currency = salary
    amount = f"{low:,}" if low == high else f"{low:,}–{high:,}"
    return f"{amount.replace(',', ' ')} {currency}/mois"


def skills_found(text: str, skills: list[str]) -> list[str]:
    """The skills the posting mentions, in the order of the list."""
    return [skill for skill in skills
            if skill.strip() and re.search(rf"(?<![\w]){re.escape(skill.strip())}(?![\w])", text, re.IGNORECASE)]
