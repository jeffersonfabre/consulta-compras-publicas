"""Página: Licitações da Lei 14.133/2021."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import api_client
from paginas.comum import (
    cache_buscar_contratacoes,
    cache_buscar_itens,
    cache_buscar_resultados,
    formatar_brl,
    formatar_cnpj,
    formatar_data,
    gerar_xlsx,
    to_float,
)


def _construir_dataframe_itens(
    itens: list[dict], resultados: list[dict]
) -> pd.DataFrame:
    """
    Combina dados dos itens (10.6) com resultados (10.7) usando idCompraItem.
    Prefere valores HOMOLOGADOS quando disponíveis, com fallback para estimados.
    """
    resultados_por_item: dict[str, dict] = {}
    for r in resultados:
        chave = r.get("idCompraItem") or ""
        if chave:
            atual = resultados_por_item.get(chave)
            if not atual or (r.get("ordemClassificacaoSrp") or 999) < (
                atual.get("ordemClassificacaoSrp") or 999
            ):
                resultados_por_item[chave] = r

    linhas = []
    for it in itens:
        id_item = it.get("idCompraItem") or ""
        res = resultados_por_item.get(id_item, {})

        cnpj = res.get("niFornecedor") or it.get("codFornecedor") or ""
        nome = (
            res.get("nomeRazaoSocialFornecedor")
            or it.get("nomeFornecedor")
            or ""
        )
        valor_unit = (
            to_float(res.get("valorUnitarioHomologado"))
            or to_float(it.get("valorUnitarioResultado"))
            or to_float(it.get("valorUnitarioEstimado"))
        )
        valor_total = (
            to_float(res.get("valorTotalHomologado"))
            or to_float(it.get("valorTotalResultado"))
            or to_float(it.get("valorTotal"))
        )

        linhas.append(
            {
                "Nº Item": it.get("numeroItemCompra") or it.get("numeroItemPncp") or "",
                "Descrição": it.get("descricaoResumida") or "",
                "CNPJ Fornecedor": formatar_cnpj(cnpj),
                "Nome do Fornecedor": nome,
                "Quantidade Solicitada": to_float(it.get("quantidade")),
                "Valor Unitário (R$)": valor_unit,
                "Valor Total (R$)": valor_total,
                "Situação": it.get("situacaoCompraItemNome") or "",
            }
        )

    df = pd.DataFrame(linhas)
    if not df.empty:
        df["__ord"] = pd.to_numeric(df["Nº Item"], errors="coerce").fillna(9999)
        df = df.sort_values("__ord").drop(columns="__ord").reset_index(drop=True)
    return df


def render():
    """Renderiza a página de Licitações 14.133 dentro de uma tab."""
    st.markdown(
        '<div class="page-intro">Itens, fornecedores e valores de licitações '
        "regidas pela Nova Lei de Licitações.</div>",
        unsafe_allow_html=True,
    )

    with st.form("lic_form"):
        col1, col2, col3, col4 = st.columns([1.2, 1.6, 1.2, 1])
        with col1:
            uasg = st.text_input("UASG", placeholder="120195", key="lic_uasg")
        with col2:
            modalidade_nome = st.selectbox(
                "Modalidade",
                options=list(api_client.MODALIDADES.keys()),
                index=4,  # Pregão
                key="lic_modalidade",
            )
        with col3:
            numero_licitacao = st.text_input(
                "Número da licitação", placeholder="90109", key="lic_numero"
            )
        with col4:
            ano = st.number_input(
                "Ano",
                min_value=2021,
                max_value=datetime.now().year + 1,
                value=datetime.now().year,
                step=1,
                key="lic_ano",
            )

        submitted = st.form_submit_button("Consultar licitação")

    if not submitted:
        return

    # Validação
    if not uasg or not uasg.strip().isdigit():
        st.error("Informe a UASG (apenas dígitos).")
        return
    if not numero_licitacao or not numero_licitacao.strip().isdigit():
        st.error("Informe o número da licitação (apenas dígitos).")
        return

    uasg = uasg.strip()
    numero_licitacao = numero_licitacao.strip()
    codigo_modalidade = api_client.MODALIDADES[modalidade_nome]

    progress = st.progress(0, text="Buscando contratações…")

    try:
        contratacoes = cache_buscar_contratacoes(uasg, codigo_modalidade, int(ano))
        progress.progress(
            33,
            text=f"{len(contratacoes)} contratações encontradas — localizando a licitação…",
        )

        contratacao = api_client.encontrar_contratacao(contratacoes, numero_licitacao)
        if not contratacao:
            progress.empty()
            st.warning(
                f"Não encontrei {modalidade_nome.lower()} nº **{numero_licitacao}/{ano}** "
                f"para a UASG **{uasg}**. Verifique se a licitação foi mesmo publicada "
                "como Lei 14.133/2021."
            )
            with st.expander(
                f"Ver {len(contratacoes)} contratações encontradas para esta UASG/modalidade/ano"
            ):
                if contratacoes:
                    df_disp = pd.DataFrame(
                        [
                            {
                                "Nº Compra": c.get("numeroCompra", ""),
                                "Objeto": (c.get("objetoCompra") or "")[:100],
                                "Publicação": formatar_data(c.get("dataPublicacaoPncp")),
                                "Situação": c.get("situacaoCompraNomePncp", ""),
                            }
                            for c in contratacoes
                        ]
                    )
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma contratação encontrada para esses filtros.")
            return

        id_compra = contratacao.get("idCompra", "")
        orgao_cnpj = contratacao.get("orgaoEntidadeCnpj", "")

        progress.progress(50, text="Buscando itens da licitação…")
        todos_itens = cache_buscar_itens(uasg, int(ano), orgao_cnpj=orgao_cnpj)
        itens = api_client.filtrar_itens_da_contratacao(todos_itens, id_compra)

        progress.progress(75, text="Buscando resultados (fornecedores adjudicados)…")
        try:
            todos_resultados = cache_buscar_resultados(uasg, int(ano), orgao_cnpj=orgao_cnpj)
            resultados = api_client.filtrar_resultados_da_contratacao(
                todos_resultados, id_compra
            )
        except api_client.ApiError:
            resultados = []

        progress.progress(100, text="Pronto!")
        progress.empty()

        # === Resumo ===
        st.markdown("### Licitação encontrada")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Itens", len(itens))
        col_b.metric("Valor Estimado", formatar_brl(to_float(contratacao.get("valorTotalEstimado"))))
        col_c.metric("Valor Homologado", formatar_brl(to_float(contratacao.get("valorTotalHomologado"))))
        col_d.metric("Situação", contratacao.get("situacaoCompraNomePncp") or "—")

        with st.expander("Ver detalhes da contratação"):
            colx, coly = st.columns(2)
            with colx:
                st.markdown(f"**Órgão:** {contratacao.get('orgaoEntidadeRazaoSocial', '—')}")
                st.markdown(f"**Unidade:** {contratacao.get('unidadeOrgaoNomeUnidade', '—')}")
                st.markdown(
                    f"**Município/UF:** {contratacao.get('unidadeOrgaoMunicipioNome', '—')} / "
                    f"{contratacao.get('unidadeOrgaoUfSigla', '—')}"
                )
                st.markdown(f"**Modalidade:** {contratacao.get('modalidadeNome', '—')}")
                st.markdown(f"**Modo de Disputa:** {contratacao.get('modoDisputaNomePncp', '—')}")
            with coly:
                st.markdown(f"**Nº Compra:** {contratacao.get('numeroCompra', '—')}")
                st.markdown(f"**Processo:** {contratacao.get('processo', '—')}")
                st.markdown(f"**Amparo Legal:** {contratacao.get('amparoLegalNome', '—')}")
                st.markdown(f"**Publicação PNCP:** {formatar_data(contratacao.get('dataPublicacaoPncp'))}")
                st.markdown(f"**Nº Controle PNCP:** `{contratacao.get('numeroControlePNCP', '—')}`")
            st.markdown(f"**Objeto:** {contratacao.get('objetoCompra', '—')}")

        st.markdown(
            '<div class="section-title">Itens, fornecedores e valores</div>',
            unsafe_allow_html=True,
        )

        if not itens:
            st.info(
                "Esta contratação foi localizada, mas ainda não há itens publicados na API. "
                "Isso pode acontecer com licitações muito recentes — tente novamente em algumas horas."
            )
            return

        df = _construir_dataframe_itens(itens, resultados)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Quantidade Solicitada": st.column_config.NumberColumn(format="%.2f"),
                "Valor Unitário (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor Total (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Descrição": st.column_config.TextColumn(width="large"),
                "Nome do Fornecedor": st.column_config.TextColumn(width="medium"),
            },
        )

        # === Download ===
        detalhes = [
            ("Número de Controle PNCP", contratacao.get("numeroControlePNCP", "")),
            ("UASG", contratacao.get("unidadeOrgaoCodigoUnidade", "")),
            ("Unidade", contratacao.get("unidadeOrgaoNomeUnidade", "")),
            ("Modalidade", contratacao.get("modalidadeNome", "")),
            ("Modo de Disputa", contratacao.get("modoDisputaNomePncp", "")),
            ("Número da Compra", contratacao.get("numeroCompra", "")),
            ("Processo", contratacao.get("processo", "")),
            ("Objeto", contratacao.get("objetoCompra", "")),
            ("Órgão (CNPJ)", formatar_cnpj(contratacao.get("orgaoEntidadeCnpj", ""))),
            ("Órgão (Razão Social)", contratacao.get("orgaoEntidadeRazaoSocial", "")),
            ("UF", contratacao.get("unidadeOrgaoUfSigla", "")),
            ("Município", contratacao.get("unidadeOrgaoMunicipioNome", "")),
            ("Amparo Legal", contratacao.get("amparoLegalNome", "")),
            ("Situação", contratacao.get("situacaoCompraNomePncp", "")),
            ("Valor Estimado", to_float(contratacao.get("valorTotalEstimado"))),
            ("Valor Homologado", to_float(contratacao.get("valorTotalHomologado"))),
            ("Data Publicação PNCP", formatar_data(contratacao.get("dataPublicacaoPncp"))),
            ("Data Abertura Propostas", formatar_data(contratacao.get("dataAberturaPropostaPncp"))),
        ]

        xlsx_bytes = gerar_xlsx(
            df=df,
            titulo="Consulta de Licitação — Lei 14.133/2021",
            subtitulo=(
                f"UASG {contratacao.get('unidadeOrgaoCodigoUnidade', '—')}  •  "
                f"{contratacao.get('modalidadeNome', '—')}  •  "
                f"Nº {contratacao.get('numeroCompra', '—')}"
            ),
            descricao=(
                f"Órgão: {contratacao.get('orgaoEntidadeRazaoSocial', '—')}  •  "
                f"Publicado em: {formatar_data(contratacao.get('dataPublicacaoPncp'))}"
            ),
            detalhes=detalhes,
            nome_aba_detalhes="Contratação",
            colunas_monetarias=("Valor Unitário (R$)", "Valor Total (R$)"),
            colunas_quantidade=("Quantidade Solicitada",),
            larguras={
                "Nº Item": 10,
                "Descrição": 50,
                "CNPJ Fornecedor": 22,
                "Nome do Fornecedor": 40,
                "Quantidade Solicitada": 18,
                "Valor Unitário (R$)": 18,
                "Valor Total (R$)": 18,
                "Situação": 22,
            },
        )

        nome_arquivo = (
            f"licitacao_{uasg}_{modalidade_nome.replace(' ', '-').lower()}"
            f"_{numero_licitacao}_{ano}.xlsx"
        )
        st.markdown("&nbsp;")
        col_dl, _ = st.columns([1, 3])
        with col_dl:
            st.download_button(
                label="📥  Baixar planilha (.xlsx)",
                data=xlsx_bytes,
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        if not resultados:
            st.caption(
                "ℹ️ Esta licitação ainda não tem resultados homologados publicados — "
                "os valores exibidos são estimados."
            )

    except api_client.ApiError as e:
        progress.empty()
        st.error(f"Falha ao consultar a API: {e}")
    except Exception as e:
        progress.empty()
        st.error(f"Erro inesperado: {e}")
        st.exception(e)
