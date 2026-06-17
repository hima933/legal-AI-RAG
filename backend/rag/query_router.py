def detect_query_domain(query: str):

    q = query.lower()

    if "ipc" in q or "section" in q or "punishment" in q:
        return "IPC"

    elif "article" in q or "constitution" in q:
        return "CONSTITUTION"

    elif "contract" in q or "agreement" in q:
        return "CONTRACT_ACT"

    elif "case" in q or "judgment" in q:
        return "CASE_LAW"

    elif "law" in q or "legal" in q:
        return "LEGAL_QA"

    else:
        return "GENERAL"