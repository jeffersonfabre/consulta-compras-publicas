"""
Cliente da API Compras.gov.br

Cobre três módulos da API pública:

  • modulo-contratacoes  → Lei 14.133/2021 (seções 10.5, 10.6 e 10.7 do manual)
  • modulo-arp           → Atas de Registro de Preços (seções 11.1 e 11.2)
  • modulo-contratos     → Contratos firmados (seções 12.1 e 12.2)

Documentação oficial:
  https://dadosabertos.compras.gov.br/
"""
from __future__ import annotations

import time
from typing import Any

import requests

BASE_URL = "https://dadosabertos.compras.gov.br"

# Códigos de modalidade conforme manual seção 10.1
MODALIDADES: dict[str, int] = {
    "Convite": 1,
    "Tomada de Preços": 2,
    "Concorrência": 3,
    "Concorrência Internacional": 4,
    "Pregão": 5,
    "Dispensa de Licitação": 6,
    "Inexigibilidade de Licitação": 7,
    "Credenciamento": 12,
    "Concurso": 20,
    "Tomada de Preços por Técnica e Preço": 22,
    "Concorrência por Técnica e Preço": 33,
    "Concorrência Internacional por Técnica e Preço": 44,
    "Convênio": 57,
}

MAX_PAGE_SIZE = 500
DEFAULT_TIMEOUT = 60


class ApiError(Exception):
    """Erro genérico da API."""


def _get(modulo: str, endpoint: str, params: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Faz GET com tratamento de erros e parseia JSON."""
    url = f"{BASE_URL}/{modulo}/{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=timeout, headers={"accept": "*/*"})
    except requests.Timeout:
        raise ApiError(f"Tempo esgotado ao chamar {endpoint}. Tente novamente.")
    except requests.RequestException as e:
        raise ApiError(f"Erro de rede: {e}")

    if resp.status_code == 204:
        return {"resultado": [], "totalRegistros": 0, "totalPaginas": 0, "paginasRestantes": 0}

    if resp.status_code >= 400:
        raise ApiError(
            f"Erro HTTP {resp.status_code} em {endpoint}. "
            f"Resposta: {resp.text[:200]}"
        )

    try:
        return resp.json()
    except ValueError:
        raise ApiError(f"Resposta inválida de {endpoint}: {resp.text[:200]}")


def _paginar(modulo: str, endpoint: str, params: dict[str, Any], max_paginas: int = 20) -> list[dict]:
    """Itera sobre todas as páginas de um endpoint."""
    todos: list[dict] = []
    pagina = 1
    while pagina <= max_paginas:
        params_pag = {**params, "pagina": pagina, "tamanhoPagina": MAX_PAGE_SIZE}
        data = _get(modulo, endpoint, params_pag)
        resultado = data.get("resultado") or []
        todos.extend(resultado)
        paginas_restantes = data.get("paginasRestantes", 0) or 0
        if paginas_restantes <= 0 or not resultado:
            break
        pagina += 1
        time.sleep(0.1)  # cortesia para o servidor
    return todos


# =============================================================================
# Helpers de filtragem local
# =============================================================================

def _so_digitos(s: str) -> str:
    return "".join(c for c in str(s) if c.isdigit())


def _numero_da_compra(numero_compra: str) -> str:
    """
    Extrai a parte sequencial de um número formatado tipo `"00090/2025"`,
    devolvendo `"90"`. Tolera variações como `"90"`, `"0090"`, etc.
    """
    if not numero_compra:
        return ""
    parte_antes_barra = str(numero_compra).split("/")[0]
    digitos = _so_digitos(parte_antes_barra)
    return digitos.lstrip("0") or ("0" if digitos else "")


def _match_numero(api_value: str, busca_value: str) -> bool:
    """Compara dois números (licitação/ata/contrato) tolerando formatações."""
    return _numero_da_compra(api_value) == _numero_da_compra(busca_value) and bool(
        _numero_da_compra(busca_value)
    )


# =============================================================================
# Módulo Contratações — Lei 14.133/2021 (seções 10.5/10.6/10.7)
# =============================================================================

def buscar_contratacoes(
    uasg: str,
    codigo_modalidade: int,
    ano: int,
) -> list[dict]:
    """10.5 — Lista contratações de uma UASG / modalidade dentro do ano informado."""
    params = {
        "unidadeOrgaoCodigoUnidade": str(uasg),
        "codigoModalidade": int(codigo_modalidade),
        "dataPublicacaoPncpInicial": f"{ano}-01-01",
        "dataPublicacaoPncpFinal": f"{ano}-12-31",
    }
    return _paginar(
        "modulo-contratacoes", "1_consultarContratacoes_PNCP_14133", params, max_paginas=10
    )


def buscar_itens(
    uasg: str,
    ano: int,
    orgao_cnpj: str | None = None,
) -> list[dict]:
    """10.6 — Lista itens de contratações da UASG no período."""
    params: dict[str, Any] = {
        "unidadeOrgaoCodigoUnidade": str(uasg),
        "dataInclusaoPncpInicial": f"{ano}-01-01",
        "dataInclusaoPncpFinal": f"{ano + 1}-03-31",
    }
    if orgao_cnpj:
        params["orgaoEntidadeCnpj"] = orgao_cnpj
    return _paginar(
        "modulo-contratacoes", "2_consultarItensContratacoes_PNCP_14133", params, max_paginas=20
    )


def buscar_resultados(
    uasg: str,
    ano: int,
    orgao_cnpj: str | None = None,
) -> list[dict]:
    """10.7 — Lista resultados (fornecedor + valor homologado) dos itens."""
    params: dict[str, Any] = {
        "unidadeOrgaoCodigoUnidade": str(uasg),
        "dataResultadoPncpInicial": f"{ano}-01-01",
        "dataResultadoPncpFinal": f"{ano + 1}-06-30",
    }
    if orgao_cnpj:
        params["orgaoEntidadeCnpj"] = orgao_cnpj
    return _paginar(
        "modulo-contratacoes",
        "3_consultarResultadoItensContratacoes_PNCP_14133",
        params,
        max_paginas=20,
    )


def encontrar_contratacao(contratacoes: list[dict], numero_alvo: str) -> dict | None:
    """Procura a contratação pelo numeroCompra."""
    for c in contratacoes:
        if _match_numero(c.get("numeroCompra", ""), numero_alvo):
            return c
    return None


def filtrar_itens_da_contratacao(itens: list[dict], id_compra: str) -> list[dict]:
    return [i for i in itens if i.get("idCompra") == id_compra]


def filtrar_resultados_da_contratacao(resultados: list[dict], id_compra: str) -> list[dict]:
    return [r for r in resultados if r.get("idCompra") == id_compra]


# =============================================================================
# Módulo ARP — Atas de Registro de Preços (seções 11.1 e 11.2)
# =============================================================================

def buscar_arps(
    uasg_gerenciadora: str,
    ano: int,
    codigo_modalidade: str | None = None,
) -> list[dict]:
    """11.1 — Lista ARPs de uma unidade gerenciadora com vigência iniciada no ano."""
    params: dict[str, Any] = {
        "codigoUnidadeGerenciadora": int(uasg_gerenciadora),
        "dataVigenciaInicialMin": f"{ano}-01-01",
        "dataVigenciaInicialMax": f"{ano}-12-31",
    }
    if codigo_modalidade:
        params["codigoModalidadeCompra"] = str(codigo_modalidade)
    return _paginar("modulo-arp", "1_consultarARP", params, max_paginas=10)


def buscar_arp_itens(
    uasg_gerenciadora: str,
    ano: int,
    codigo_modalidade: str | None = None,
) -> list[dict]:
    """11.2 — Lista itens de ARPs da unidade gerenciadora."""
    params: dict[str, Any] = {
        "codigoUnidadeGerenciadora": int(uasg_gerenciadora),
        "dataVigenciaInicialMin": f"{ano}-01-01",
        "dataVigenciaInicialMax": f"{ano}-12-31",
    }
    if codigo_modalidade:
        params["codigoModalidadeCompra"] = str(codigo_modalidade)
    return _paginar("modulo-arp", "2_consultarARPItem", params, max_paginas=20)


def encontrar_arp(arps: list[dict], numero_ata_alvo: str) -> dict | None:
    """Procura ARP pelo numeroAtaRegistroPreco."""
    for a in arps:
        if _match_numero(a.get("numeroAtaRegistroPreco", ""), numero_ata_alvo):
            return a
    return None


def filtrar_itens_da_arp(
    itens: list[dict], numero_ata: str, uasg_gerenciadora: str
) -> list[dict]:
    """Filtra itens cujo numeroAtaRegistroPreco bate com a ARP alvo."""
    alvo = _numero_da_compra(numero_ata)
    uasg = str(uasg_gerenciadora)
    return [
        i
        for i in itens
        if _numero_da_compra(i.get("numeroAtaRegistroPreco", "")) == alvo
        and str(i.get("codigoUnidadeGerenciadora", "")) == uasg
    ]


# =============================================================================
# Módulo Contratos (seções 12.1 e 12.2)
# =============================================================================

def buscar_contratos(
    uasg_gestora: str,
    ano: int,
    numero_contrato: str | None = None,
) -> list[dict]:
    """12.1 — Lista contratos de uma unidade gestora com vigência iniciada no ano."""
    params: dict[str, Any] = {
        "codigoUnidadeGestora": int(uasg_gestora),
        "dataVigenciaInicialMin": f"{ano}-01-01",
        "dataVigenciaInicialMax": f"{ano}-12-31",
    }
    if numero_contrato:
        params["numeroContrato"] = str(numero_contrato)
    return _paginar("modulo-contratos", "1_consultarContratos", params, max_paginas=10)


def buscar_itens_contrato(
    uasg_gestora: str,
    ano: int,
    numero_contrato: str | None = None,
) -> list[dict]:
    """12.2 — Lista itens de contratos da unidade gestora no período."""
    params: dict[str, Any] = {
        "codigoUnidadeGestora": int(uasg_gestora),
        "dataVigenciaInicialMin": f"{ano}-01-01",
        "dataVigenciaInicialMax": f"{ano}-12-31",
    }
    if numero_contrato:
        params["numeroContrato"] = str(numero_contrato)
    return _paginar("modulo-contratos", "2_consultarContratosItem", params, max_paginas=20)


def encontrar_contrato(contratos: list[dict], numero_alvo: str) -> dict | None:
    """Procura contrato pelo numeroContrato."""
    for c in contratos:
        if _match_numero(c.get("numeroContrato", ""), numero_alvo):
            return c
    return None


def filtrar_itens_do_contrato(
    itens: list[dict], numero_contrato: str, uasg_gestora: str
) -> list[dict]:
    """Filtra itens cujo numeroContrato bate com o contrato alvo."""
    alvo = _numero_da_compra(numero_contrato)
    uasg = str(uasg_gestora)
    return [
        i
        for i in itens
        if _numero_da_compra(i.get("numeroContrato", "")) == alvo
        and str(i.get("codigoUnidadeGestora", "")) == uasg
    ]
