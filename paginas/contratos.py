"""Página: Contratos firmados — módulo 12 do manual."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import api_client
from paginas.comum import (
    cache_buscar_contratos,
    cache_buscar_itens_contrato,
    formatar_brl,
    formatar_cnpj,
    formatar_data,
    gerar_xlsx,
    to_float,
)


def _construir_dataframe(itens_contrato: list[dict]) -> pd.DataFrame:
    """Monta o DataFrame de itens de um contrato."""
    linhas = []
    for it in itens_contrato:
        linhas.append(
            {
                "Nº Item": it.get("numeroItem") or "",
                "Descrição": it.get("descricaoIitem") or "",  # campo grafado assim no manual
                "Tipo": it.get("tipoItem") or "",
                "CNPJ Fornecedor": formatar_cnpj(it.get("niFornecedor", "")),
                "Nome do Fornecedor": it.get("nomeRazaoSocialFornecedor") or "",
                "Quantidade": to_float(it.get("quantidadeItem")),
                "Valor Unitário (R$)": to_float(it.get("valorUnitarioItem")),
                "Valor Total (R$)": to_float(it.get("valorTotalItem")),
            }
        )
    df = pd.DataFrame(linhas)
    if not df.empty:
        df["__ord"] = pd.to_numeric(df["Nº Item"], errors="coerce").fillna(9999)
        df = df.sort_values("__ord").drop(columns="__ord").reset_index(drop=True)
    return df


def render():
    """Renderiza a página de Contratos."""
    st.markdown(
        '<div class="page-intro">Contratos firmados pelo órgão público — vigência, '
        "fornecedor, itens contratados e valores.</div>",
        unsafe_allow_html=True,
    )

    with st.form("contrato_form"):
        col1, col2, col3 = st.columns([1.4, 1.4, 1])
        with col1:
            uasg = st.text_input(
                "UASG Gestora",
                placeholder="120195",
                key="ct_uasg",
                help="Código da unidade gestora do contrato.",
            )
        with col2:
            numero_contrato = st.text_input(
                "Número do contrato",
                placeholder="00045/2025",
                key="ct_numero",
            )
        with col3:
            ano = st.number_input(
                "Ano da vigência",
                min_value=2021,
                max_value=datetime.now().year + 1,
                value=datetime.now().year,
                step=1,
                key="ct_ano",
            )

        submitted = st.form_submit_button("Consultar contrato")

    if not submitted:
        return

    if not uasg or not uasg.strip().isdigit():
        st.error("Informe a UASG Gestora (apenas dígitos).")
        return
    if not numero_contrato or not numero_contrato.strip():
        st.error("Informe o número do contrato.")
        return

    uasg = uasg.strip()
    numero_contrato = numero_contrato.strip()

    progress = st.progress(0, text="Buscando contratos…")

    try:
        contratos = cache_buscar_contratos(uasg, int(ano), numero_contrato=numero_contrato)
        progress.progress(40, text=f"{len(contratos)} contratos encontrados — localizando…")

        contrato = api_client.encontrar_contrato(contratos, numero_contrato)
        if not contrato:
            progress.empty()
            st.warning(
                f"Não encontrei o contrato nº **{numero_contrato}** na UASG **{uasg}** "
                f"com vigência iniciada em {ano}."
            )
            with st.expander(f"Ver {len(contratos)} contratos encontrados"):
                if contratos:
                    df_disp = pd.DataFrame(
                        [
                            {
                                "Nº Contrato": c.get("numeroContrato", ""),
                                "Fornecedor": c.get("nomeRazaoSocialFornecedor", ""),
                                "Vigência": (
                                    f"{formatar_data(c.get('dataVigenciaInicial'))} → "
                                    f"{formatar_data(c.get('dataVigenciaFinal'))}"
                                ),
                                "Valor Global": formatar_brl(to_float(c.get("valorGlobal"))),
                                "Objeto": (c.get("objeto") or "")[:80],
                            }
                            for c in contratos
                        ]
                    )
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum contrato encontrado para esses filtros.")
            return

        progress.progress(75, text="Buscando itens do contrato…")
        todos_itens = cache_buscar_itens_contrato(
            uasg, int(ano), numero_contrato=numero_contrato
        )
        itens = api_client.filtrar_itens_do_contrato(todos_itens, numero_contrato, uasg)
        progress.progress(100, text="Pronto!")
        progress.empty()

        # === Resumo ===
        st.markdown("### Contrato encontrado")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Itens", len(itens))
        col_b.metric("Valor Global", formatar_brl(to_float(contrato.get("valorGlobal"))))
        col_c.metric(
            "Valor Acumulado",
            formatar_brl(to_float(contrato.get("valorAcumulado"))),
        )
        col_d.metric(
            "Vigência até",
            formatar_data(contrato.get("dataVigenciaFinal")) or "—",
        )

        with st.expander("Ver detalhes do contrato"):
            colx, coly = st.columns(2)
            with colx:
                st.markdown(f"**Órgão:** {contrato.get('nomeOrgao', '—')}")
                st.markdown(f"**Unidade Gestora:** {contrato.get('nomeUnidadeGestora', '—')}")
                st.markdown(f"**Tipo:** {contrato.get('nomeTipo', '—')}")
                st.markdown(f"**Categoria:** {contrato.get('nomeCategoria', '—')}")
                st.markdown(
                    f"**Modalidade:** {contrato.get('nomeModalidadeCompra', '—')}  •  "
                    f"**Compra:** {contrato.get('numeroCompra', '—')}"
                )
            with coly:
                st.markdown(
                    f"**Fornecedor:** {contrato.get('nomeRazaoSocialFornecedor', '—')}  "
                    f"({formatar_cnpj(contrato.get('niFornecedor', ''))})"
                )
                st.markdown(f"**Processo:** {contrato.get('processo', '—')}")
                st.markdown(
                    f"**Vigência:** {formatar_data(contrato.get('dataVigenciaInicial'))} a "
                    f"{formatar_data(contrato.get('dataVigenciaFinal'))}"
                )
                st.markdown(
                    f"**Parcelas:** {contrato.get('numeroParcelas', '—')} de "
                    f"{formatar_brl(to_float(contrato.get('valorParcela')))}"
                )
                st.markdown(f"**Nº Controle PNCP:** `{contrato.get('numeroControlePncpContrato', '—')}`")
            st.markdown(f"**Objeto:** {contrato.get('objeto', '—')}")
            if contrato.get("informacoesComplementares"):
                st.markdown(f"**Informações complementares:** {contrato['informacoesComplementares']}")

        st.markdown(
            '<div class="section-title">Itens do Contrato</div>', unsafe_allow_html=True
        )

        if not itens:
            st.info(
                "O contrato foi localizado, mas não há itens detalhados na API. "
                "Alguns contratos (sobretudo de serviços contínuos) registram apenas o "
                "valor global, sem itens individualizados."
            )
            # Mesmo assim oferece download com os detalhes do contrato
            df = pd.DataFrame(columns=[
                "Nº Item", "Descrição", "Tipo", "CNPJ Fornecedor",
                "Nome do Fornecedor", "Quantidade",
                "Valor Unitário (R$)", "Valor Total (R$)",
            ])
        else:
            df = _construir_dataframe(itens)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Quantidade": st.column_config.NumberColumn(format="%.2f"),
                    "Valor Unitário (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Valor Total (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Descrição": st.column_config.TextColumn(width="large"),
                },
            )

        detalhes = [
            ("Número do Contrato", contrato.get("numeroContrato", "")),
            ("Nº Controle PNCP", contrato.get("numeroControlePncpContrato", "")),
            ("Órgão", contrato.get("nomeOrgao", "")),
            ("Unidade Gestora", contrato.get("nomeUnidadeGestora", "")),
            ("Tipo", contrato.get("nomeTipo", "")),
            ("Categoria", contrato.get("nomeCategoria", "")),
            ("Subcategoria", contrato.get("nomeSubcategoria", "")),
            ("Modalidade da Compra", contrato.get("nomeModalidadeCompra", "")),
            ("Número da Compra", contrato.get("numeroCompra", "")),
            ("Fornecedor (CNPJ/CPF)", formatar_cnpj(contrato.get("niFornecedor", ""))),
            ("Fornecedor (Nome)", contrato.get("nomeRazaoSocialFornecedor", "")),
            ("Processo", contrato.get("processo", "")),
            ("Objeto", contrato.get("objeto", "")),
            ("Informações Complementares", contrato.get("informacoesComplementares", "")),
            ("Receita/Despesa", contrato.get("receitaDespesa", "")),
            ("Valor Global", to_float(contrato.get("valorGlobal"))),
            ("Valor Acumulado", to_float(contrato.get("valorAcumulado"))),
            ("Despesas Acessórias", to_float(contrato.get("totalDespesasAcessorias"))),
            ("Nº de Parcelas", contrato.get("numeroParcelas", "")),
            ("Valor da Parcela", to_float(contrato.get("valorParcela"))),
            ("Vigência Inicial", formatar_data(contrato.get("dataVigenciaInicial"))),
            ("Vigência Final", formatar_data(contrato.get("dataVigenciaFinal"))),
            ("Data de Inclusão", formatar_data(contrato.get("dataHoraInclusao"))),
        ]

        xlsx_bytes = gerar_xlsx(
            df=df,
            titulo="Consulta de Contrato",
            subtitulo=(
                f"UASG Gestora {contrato.get('codigoUnidadeGestora', '—')}  •  "
                f"Contrato {contrato.get('numeroContrato', '—')}"
            ),
            descricao=(
                f"Fornecedor: {contrato.get('nomeRazaoSocialFornecedor', '—')}  •  "
                f"Vigência até: {formatar_data(contrato.get('dataVigenciaFinal'))}"
            ),
            detalhes=detalhes,
            nome_aba_detalhes="Contrato",
            colunas_monetarias=("Valor Unitário (R$)", "Valor Total (R$)"),
            colunas_quantidade=("Quantidade",),
            larguras={
                "Nº Item": 8,
                "Descrição": 50,
                "Tipo": 10,
                "CNPJ Fornecedor": 22,
                "Nome do Fornecedor": 40,
                "Quantidade": 14,
                "Valor Unitário (R$)": 18,
                "Valor Total (R$)": 18,
            },
        )

        nome_arquivo = f"contrato_{uasg}_{numero_contrato.replace('/', '-')}_{ano}.xlsx"
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

    except api_client.ApiError as e:
        progress.empty()
        st.error(f"Falha ao consultar a API: {e}")
    except Exception as e:
        progress.empty()
        st.error(f"Erro inesperado: {e}")
        st.exception(e)
