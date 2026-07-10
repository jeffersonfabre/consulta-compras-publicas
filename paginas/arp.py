"""Página: Atas de Registro de Preços (ARP) — módulo 11 do manual."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import api_client
from paginas.comum import (
    cache_buscar_arp_itens,
    cache_buscar_arps,
    formatar_brl,
    formatar_cnpj,
    formatar_data,
    gerar_xlsx,
    to_float,
)


def _construir_dataframe(itens_arp: list[dict]) -> pd.DataFrame:
    """Monta o DataFrame de itens de uma ARP."""
    linhas = []
    for it in itens_arp:
        linhas.append(
            {
                "Nº Item": it.get("numeroItem") or "",
                "Descrição": it.get("descricaoItem") or "",
                "Tipo": it.get("tipoItem") or "",
                "CNPJ Fornecedor": formatar_cnpj(it.get("niFornecedor", "")),
                "Nome do Fornecedor": it.get("nomeRazaoSocialFornecedor") or "",
                "Classificação": it.get("classificacaoFornecedor") or "",
                "Quantidade Homologada": to_float(it.get("quantidadeHomologadaItem")),
                "Quantidade Empenhada": to_float(it.get("quantidadeEmpenhada")),
                "Valor Unitário (R$)": to_float(it.get("valorUnitario")),
                "Valor Total (R$)": to_float(it.get("valorTotal")),
                "Máx. Adesão": to_float(it.get("maximoAdesao")),
            }
        )
    df = pd.DataFrame(linhas)
    if not df.empty:
        df["__ord"] = pd.to_numeric(df["Nº Item"], errors="coerce").fillna(9999)
        df = df.sort_values("__ord").drop(columns="__ord").reset_index(drop=True)
    return df


def render():
    """Renderiza a página de ARPs."""
    st.markdown(
        '<div class="page-intro">Atas de Registro de Preços vigentes — itens, fornecedores '
        "e quantidades homologadas.</div>",
        unsafe_allow_html=True,
    )

    with st.form("arp_form"):
        col1, col2, col3, col4 = st.columns([1.2, 1.6, 1.2, 1])
        with col1:
            uasg = st.text_input(
                "UASG Gerenciadora",
                placeholder="120195",
                key="arp_uasg",
                help="Código da unidade gerenciadora da Ata.",
            )
        with col2:
            modalidade_nome = st.selectbox(
                "Modalidade da compra (opcional)",
                options=["Todas"] + list(api_client.MODALIDADES.keys()),
                index=0,
                key="arp_modalidade",
            )
        with col3:
            numero_ata = st.text_input(
                "Número da Ata", placeholder="00012/2025", key="arp_numero"
            )
        with col4:
            ano = st.number_input(
                "Ano da vigência",
                min_value=2021,
                max_value=datetime.now().year + 1,
                value=datetime.now().year,
                step=1,
                key="arp_ano",
            )

        submitted = st.form_submit_button("Consultar ata")

    if not submitted:
        return

    if not uasg or not uasg.strip().isdigit():
        st.error("Informe a UASG Gerenciadora (apenas dígitos).")
        return
    if not numero_ata or not numero_ata.strip():
        st.error("Informe o número da ata.")
        return

    uasg = uasg.strip()
    numero_ata = numero_ata.strip()
    cod_modalidade: str | None = None
    if modalidade_nome != "Todas":
        cod_modalidade = str(api_client.MODALIDADES[modalidade_nome])

    progress = st.progress(0, text="Buscando atas…")

    try:
        arps = cache_buscar_arps(uasg, int(ano), codigo_modalidade=cod_modalidade)
        progress.progress(40, text=f"{len(arps)} atas encontradas — localizando…")

        ata = api_client.encontrar_arp(arps, numero_ata)
        if not ata:
            progress.empty()
            st.warning(
                f"Não encontrei a ata nº **{numero_ata}** na UASG **{uasg}** com "
                f"vigência iniciada em {ano}."
            )
            with st.expander(f"Ver {len(arps)} atas encontradas"):
                if arps:
                    df_disp = pd.DataFrame(
                        [
                            {
                                "Nº Ata": a.get("numeroAtaRegistroPreco", ""),
                                "Modalidade": a.get("nomeModalidadeCompra", ""),
                                "Vigência": (
                                    f"{formatar_data(a.get('dataVigenciaInicial'))} → "
                                    f"{formatar_data(a.get('dataVigenciaFinal'))}"
                                ),
                                "Status": a.get("statusAta", ""),
                                "Objeto": (a.get("objeto") or "")[:80],
                            }
                            for a in arps
                        ]
                    )
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma ata encontrada para esses filtros.")
            return

        progress.progress(75, text="Buscando itens da ata…")
        todos_itens = cache_buscar_arp_itens(uasg, int(ano), codigo_modalidade=cod_modalidade)
        itens = api_client.filtrar_itens_da_arp(
            todos_itens, ata.get("numeroAtaRegistroPreco", ""), uasg
        )
        progress.progress(100, text="Pronto!")
        progress.empty()

        # === Resumo ===
        st.markdown("### Ata encontrada")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Itens", len(itens))
        col_b.metric("Valor Total", formatar_brl(to_float(ata.get("valorTotal"))))
        col_c.metric("Status", ata.get("statusAta") or "—")
        col_d.metric(
            "Vigência até",
            formatar_data(ata.get("dataVigenciaFinal")) or "—",
        )

        with st.expander("Ver detalhes da ata"):
            colx, coly = st.columns(2)
            with colx:
                st.markdown(f"**Órgão:** {ata.get('nomeOrgao', '—')}")
                st.markdown(f"**Unidade Gerenciadora:** {ata.get('nomeUnidadeGerenciadora', '—')}")
                st.markdown(f"**Modalidade:** {ata.get('nomeModalidadeCompra', '—')}")
                st.markdown(f"**Compra associada:** {ata.get('numeroCompra', '—')}/{ata.get('anoCompra', '—')}")
            with coly:
                st.markdown(f"**Assinatura:** {formatar_data(ata.get('dataAssinatura'))}")
                st.markdown(
                    f"**Vigência:** {formatar_data(ata.get('dataVigenciaInicial'))} a "
                    f"{formatar_data(ata.get('dataVigenciaFinal'))}"
                )
                st.markdown(f"**Nº Controle PNCP:** `{ata.get('numeroControlePncpAta', '—')}`")
                if ata.get("linkAtaPNCP"):
                    st.markdown(f"**Link PNCP:** [Abrir ata]({ata['linkAtaPNCP']})")
            st.markdown(f"**Objeto:** {ata.get('objeto', '—')}")

        st.markdown(
            '<div class="section-title">Itens da Ata</div>', unsafe_allow_html=True
        )

        if not itens:
            st.info("Esta ata foi localizada, mas não tem itens publicados na API.")
            return

        df = _construir_dataframe(itens)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Quantidade Homologada": st.column_config.NumberColumn(format="%.2f"),
                "Quantidade Empenhada": st.column_config.NumberColumn(format="%.2f"),
                "Máx. Adesão": st.column_config.NumberColumn(format="%.2f"),
                "Valor Unitário (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor Total (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Descrição": st.column_config.TextColumn(width="large"),
            },
        )

        detalhes = [
            ("Número da Ata", ata.get("numeroAtaRegistroPreco", "")),
            ("Nº Controle PNCP", ata.get("numeroControlePncpAta", "")),
            ("Unidade Gerenciadora", ata.get("nomeUnidadeGerenciadora", "")),
            ("Órgão", ata.get("nomeOrgao", "")),
            ("Modalidade", ata.get("nomeModalidadeCompra", "")),
            ("Compra associada", f"{ata.get('numeroCompra', '')}/{ata.get('anoCompra', '')}"),
            ("Status", ata.get("statusAta", "")),
            ("Objeto", ata.get("objeto", "")),
            ("Valor Total", to_float(ata.get("valorTotal"))),
            ("Quantidade de Itens", ata.get("quantidadeItens", "")),
            ("Data de Assinatura", formatar_data(ata.get("dataAssinatura"))),
            ("Vigência Inicial", formatar_data(ata.get("dataVigenciaInicial"))),
            ("Vigência Final", formatar_data(ata.get("dataVigenciaFinal"))),
            ("Link PNCP", ata.get("linkAtaPNCP", "")),
        ]

        xlsx_bytes = gerar_xlsx(
            df=df,
            titulo="Consulta de Ata de Registro de Preços",
            subtitulo=(
                f"UASG Gerenciadora {ata.get('codigoUnidadeGerenciadora', '—')}  •  "
                f"Ata {ata.get('numeroAtaRegistroPreco', '—')}"
            ),
            descricao=(
                f"Órgão: {ata.get('nomeOrgao', '—')}  •  "
                f"Vigência até: {formatar_data(ata.get('dataVigenciaFinal'))}"
            ),
            detalhes=detalhes,
            nome_aba_detalhes="Ata",
            colunas_monetarias=("Valor Unitário (R$)", "Valor Total (R$)"),
            colunas_quantidade=("Quantidade Homologada", "Quantidade Empenhada", "Máx. Adesão"),
            larguras={
                "Nº Item": 8,
                "Descrição": 45,
                "Tipo": 10,
                "CNPJ Fornecedor": 22,
                "Nome do Fornecedor": 40,
                "Classificação": 16,
                "Quantidade Homologada": 18,
                "Quantidade Empenhada": 18,
                "Valor Unitário (R$)": 18,
                "Valor Total (R$)": 18,
                "Máx. Adesão": 14,
            },
        )

        nome_arquivo = f"ata_{uasg}_{numero_ata.replace('/', '-')}_{ano}.xlsx"
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
