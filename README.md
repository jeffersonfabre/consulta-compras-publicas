# Consulta Compras Públicas

App web em Streamlit que consulta a API pública do **Compras.gov.br** / PNCP e
permite baixar o resultado em planilha `.xlsx`. Cobre três módulos:

| Aba | O que consulta | Endpoints (manual) |
|---|---|---|
| 📋 **Licitações** | Itens, fornecedores e valores de licitações da Lei 14.133/2021 | 10.5 / 10.6 / 10.7 |
| 📑 **Atas de Registro de Preços** | Itens, fornecedores e quantidades homologadas em ARPs | 11.1 / 11.2 |
| 📝 **Contratos** | Vigência, fornecedor e itens de contratos firmados | 12.1 / 12.2 |

Você informa UASG + número (e modalidade, quando aplicável) e o app:
1. Localiza o registro na API,
2. Lista os itens com fornecedor (CNPJ + nome), quantidade, valor unitário e total,
3. Permite baixar tudo em uma planilha `.xlsx` formatada com totalizador.

---

## 📦 Estrutura do projeto

```
licitacoes-14133/
├── app.py                  # Roteamento das tabs + CSS global
├── api_client.py           # Cliente da API (3 módulos: contratacoes/arp/contratos)
├── paginas/
│   ├── __init__.py
│   ├── comum.py            # Helpers + wrappers com cache + gerador de XLSX
│   ├── licitacoes.py       # Página de licitações 14.133
│   ├── arp.py              # Página de atas
│   └── contratos.py        # Página de contratos
├── requirements.txt
└── README.md
```

---

## 🚀 Como rodar localmente

### 1. Instale o Python 3.10+

Verifique com `python --version`. Se precisar, baixe em [python.org/downloads](https://www.python.org/downloads/).

### 2. Crie um ambiente virtual

Dentro da pasta do projeto:

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Rode o app

```bash
streamlit run app.py
```

Abre em `http://localhost:8501`.

---

## 🧭 Como usar cada aba

### 📋 Licitações (Lei 14.133)

| Campo | Exemplo | Observação |
|---|---|---|
| UASG | `120195` | Código da unidade |
| Modalidade | `Pregão` | Selecione no menu |
| Número da licitação | `90109` | Sem o ano |
| Ano | `2025` | |

### 📑 Atas de Registro de Preços

| Campo | Exemplo | Observação |
|---|---|---|
| UASG Gerenciadora | `120195` | Unidade gerenciadora da ata |
| Modalidade da compra | `Pregão` | **Opcional** — deixe "Todas" se não souber |
| Número da Ata | `00012/2025` | Pode usar com ou sem ano |
| Ano da vigência | `2025` | Ano em que a vigência da ata começa |

### 📝 Contratos

| Campo | Exemplo | Observação |
|---|---|---|
| UASG Gestora | `120195` | Unidade gestora do contrato |
| Número do contrato | `00045/2025` | |
| Ano da vigência | `2025` | Ano em que a vigência começa |

---

## ⚡ Cache de 1 hora

Todas as chamadas à API usam `@st.cache_data(ttl=3600)`. Isso significa que,
**dentro da mesma sessão**, consultas repetidas (mesma UASG/modalidade/ano)
voltam instantaneamente do cache, sem bater na API novamente.

O cache expira automaticamente em 1 hora. Para limpar manualmente:

- No menu do Streamlit (canto superior direito) → **"Clear cache"**
- Ou, no código, ajuste `CACHE_TTL` em `paginas/comum.py`.

Por que isso importa: a API do Compras.gov.br pode ser lenta em horário de pico
(20–60s para uma UASG com muitos registros). Com cache, você pode **alternar
entre as abas** ou **revisitar a mesma licitação** sem esperar de novo.

---

## ☁️ Deploy gratuito no Streamlit Community Cloud

O Streamlit oferece hospedagem gratuita para apps públicos. Vai do zero ao
ar em ~5 minutos.

### Pré-requisitos

- Conta no [GitHub](https://github.com/signup) (gratuita)
- O código deste projeto

### Passo a passo

#### 1. Suba o projeto para o GitHub

Se você ainda não tem o projeto em um repositório:

```bash
cd licitacoes-14133

# inicializa o git
git init
git add .
git commit -m "Versão inicial"

# cria branch main e conecta ao seu repositório do GitHub
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/licitacoes-14133.git
git push -u origin main
```

> 💡 Se preferir não usar a linha de comando, dá para criar o repo direto no
> site do GitHub e arrastar os arquivos pela interface web.

#### 2. Crie a conta no Streamlit Cloud

Acesse [share.streamlit.io](https://share.streamlit.io) e clique em
**"Sign up"** — faça login com a mesma conta do GitHub. O Streamlit pede
permissão para ler seus repositórios, autorize.

#### 3. Crie o app

No painel do Streamlit Cloud:

1. Clique em **"Create app"**
2. Escolha **"Deploy a public app from GitHub"**
3. Preencha:
   - **Repository:** `SEU_USUARIO/licitacoes-14133`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL** (opcional): customize, ex.: `compras-publicas`
4. Clique em **"Deploy!"**

O Streamlit lê automaticamente o `requirements.txt`, instala as dependências
e roda. Em 1–2 minutos seu app está em `https://compras-publicas.streamlit.app`
(ou a URL que você escolheu).

#### 4. Atualizações automáticas

Depois do deploy inicial, **todo `git push` para a branch `main`** atualiza o
app automaticamente. Você nunca mais mexe no painel.

```bash
# fluxo típico de atualização
git add .
git commit -m "Adiciona filtro X"
git push
# → Streamlit Cloud detecta o push e redeploya em ~30 segundos
```

#### 5. Limites do plano gratuito

O plano "Community" (gratuito) suporta:

- Apps públicos (qualquer pessoa com o link acessa)
- 1 GB de RAM por app
- Hibernação após inatividade prolongada — quando alguém volta a acessar,
  o app sobe em ~10 segundos

Para apps privados ou mais recursos, existe o plano pago ([detalhes](https://streamlit.io/cloud)).

#### 6. Cuidados especiais (importante!)

⚠️ **O Streamlit Cloud roda em servidores nos EUA.** A API do Compras.gov.br é
pública e aberta, então isso funciona, mas chamadas ficam mais lentas que do
Brasil. O cache de 1 hora minimiza esse impacto.

⚠️ **Não suba arquivos sensíveis para o GitHub.** Este projeto não usa
chaves/tokens (a API é pública), mas se você adicionar algum no futuro, use
[Secrets do Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
em vez de hardcodar no código.

⚠️ **Mantenha o `requirements.txt` enxuto.** Apps no plano gratuito têm RAM
limitada — instalar bibliotecas pesadas (TensorFlow, PyTorch) pode estourar o
limite e travar o boot.

---

## 🧠 Como funciona por dentro

O app usa **três módulos da API do Compras.gov.br**, cada um com sua URL base:

```
https://dadosabertos.compras.gov.br
├── /modulo-contratacoes      → Lei 14.133 (3 endpoints)
├── /modulo-arp               → Atas (2 endpoints usados)
└── /modulo-contratos         → Contratos (2 endpoints usados)
```

O fluxo de cada aba é semelhante:

```
[inputs do usuário]
        │
        ▼
buscar lista (com filtros de data + UASG)   ← cached por 1h
        │
        ▼
encontrar pelo número informado (matching tolerante a formatação)
        │
        ▼
buscar itens dessa lista                    ← cached por 1h
        │
        ▼
filtrar itens locamente pelo idCompra/numeroAta/numeroContrato
        │
        ▼
construir DataFrame + gerar XLSX formatado
```

A paginação da API (até 500 registros por página) é feita automaticamente
pelo `_paginar()` em `api_client.py`.

---

## ⚠️ Limitações conhecidas

- **Apenas Lei 14.133** na aba de Licitações. Para licitações da Lei 8.666 antiga,
  a API tem o módulo "Legado" — fácil adicionar uma 4ª aba se precisar.
- **Latência variável.** A API é gratuita; em horário de pico pode levar
  10–60 segundos. O timeout interno é de 60s e o cache mitiga repetições.
- **Registros muito recentes** podem não ter resultados publicados ainda
  (no caso de licitações) ou itens detalhados (no caso de contratos). O app
  exibe um aviso quando isso acontece.
- **Datas obrigatórias.** Os endpoints exigem janelas de data — o app cobre
  o ano inteiro. Para UASGs com volume muito alto, isso pode levar alguns
  segundos a mais.

---

## 📚 Referências

- Manual oficial da API: `manual-api-compras.pdf` (gov.br/compras)
- Portal Nacional de Contratações Públicas (PNCP): https://pncp.gov.br
- Lei nº 14.133/2021: https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm
- Documentação Streamlit: https://docs.streamlit.io
