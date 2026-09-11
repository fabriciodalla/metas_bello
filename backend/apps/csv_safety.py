_FORMULA_PREFIXES = ("=", "+", "-", "@")


def csv_safe(value):
    """Neutraliza injeção de fórmula (CSV injection): Excel/LibreOffice interpretam uma célula
    começando por =, +, - ou @ como fórmula ao abrir o arquivo. Usado nas exportações CSV cujos
    nomes vêm do ERP externo (histórico de vendas) ou da hierarquia interna."""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text
