%%writefile app.py
import os
import re
import shutil
import subprocess
import streamlit as st


class EMUnitsSession:

    def __init__(self):
        self.historico = []

    def _obter_comando_units(self):
        if shutil.which("units"):
            return "units"
        elif os.path.exists("units.exe"):
            return "./units.exe"
        else:
            return "units"

    def _format_token(self, tok, is_denom=False):
        tok = tok.strip()
        if not tok:
            return ""

        # Garante barras duplas em comandos LaTeX (ex: \\Theta) para o Markdown do Streamlit
        if tok.startswith("\\"):
            if tok.startswith("\\\\"):
                base = tok
            else:
                base = "\\" + tok
        else:
            base = f"\\text{{{tok}}}"

        if "^" in tok:
            partes = tok.split("^", 1)
            b = partes[0].strip()
            exp = partes[1].strip()

            if b.startswith("\\"):
                base_fmt = b if b.startswith("\\\\") else "\\" + b
            else:
                base_fmt = f"\\text{{{b}}}"

            try:
                exp_num = int(exp)
                if is_denom:
                    exp_num = -exp_num
                return f"{base_fmt}^{{{exp_num}}}"
            except ValueError:
                if is_denom:
                    return f"{base_fmt}^{{-({exp})}}"
                return f"{base_fmt}^{{{exp}}}"
        else:
            if is_denom:
                return f"{base}^{{{-1}}}"
            return f"{base}"

    def formatar_estilo_livro(self, expr):
        s = expr.strip()
        if "=" in s:
            s = s.split("=")[-1].strip()

        match = re.match(r"^([\d\.\+eE\-]+)\s*(.*)$", s)
        if match and match.group(1):
            num_part = match.group(1).strip()
            unit_part = match.group(2).strip()
        else:
            num_part = ""
            unit_part = s.strip()

        if num_part:
            if num_part == "1" and unit_part:
                num_fmt = ""
            else:
                if "e" in num_part or "E" in num_part:
                    base, exp = re.split(r"[eE]", num_part)
                    num_fmt = f"{base} \\times 10^{{{int(exp)}}}"
                else:
                    num_fmt = num_part
        else:
            num_fmt = ""

        if unit_part:
            if "/" in unit_part:
                num_str, den_str = unit_part.split("/", 1)
                num_tokens = num_str.strip().split()
                den_tokens = den_str.strip().split()

                fmt_tokens = [
                    self._format_token(t, is_denom=False)
                    for t in num_tokens
                    if t
                ]
                fmt_tokens += [
                    self._format_token(t, is_denom=True)
                    for t in den_tokens
                    if t
                ]
                unit_fmt = "\\ ".join(fmt_tokens)
            else:
                tokens = unit_part.split()
                unit_fmt = "\\ ".join(
                    [self._format_token(t, is_denom=False) for t in tokens if t]
                )
        else:
            unit_fmt = ""

        if num_fmt and unit_fmt:
            return f"${num_fmt}\\ {unit_fmt}$"
        elif num_fmt:
            return f"${num_fmt}$"
        elif unit_fmt:
            return f"${unit_fmt}$"
        else:
            return ""

    def calc(self, entrada, destino=""):
        cmd = [self._obter_comando_units(), "-t", entrada]
        if destino:
            cmd.append(destino)

        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            saida_raw = res.stdout.strip()
            resultado_fmt = self.formatar_estilo_livro(saida_raw)

            registro = {
                "entrada": entrada,
                "destino": destino if destino else "SI Base / Definição",
                "resultado": resultado_fmt,
            }
            self.historico.append(registro)
            return resultado_fmt, None
        except FileNotFoundError:
            return (
                None,
                "⚠️ **Erro:** O GNU Units não foi encontrado no sistema.",
            )
        except subprocess.CalledProcessError:
            return None, "❌ **Erro:** Expressão ou unidade incompatível."

    def dim(self, expressao):
        alias_dimensoes = {
            "M": "kg",
            "L": "m",
            "T": "s",
            "I": "A",
            "THETA": "K",
            "TETA": "K",
            "\\THETA": "K",
            "Θ": "K",
            "MASSA": "kg",
            "COMPRIMENTO": "m",
            "TEMPO": "s",
            "CORRENTE": "A",
            "CORRENTE ELETRICA": "A",
            "TEMPERATURA": "K",
            "KELVIN": "K",
            "AMPERE": "A",
            "SEGUNDO": "s",
            "METRO": "m",
            "QUILOGRAMA": "kg",
        }

        expr_clean = expressao.strip()
        expr_upper = expr_clean.upper()

        if expr_upper in alias_dimensoes:
            termo_units = alias_dimensoes[expr_upper]
        else:
            termo_units = expr_clean

        try:
            res = subprocess.run(
                [self._obter_comando_units(), "-t", termo_units],
                capture_output=True,
                text=True,
                check=True,
            )
            saida = res.stdout.strip()

            unidades_str = re.sub(r"^[+\-]?[\d\.\+eE\-]+\s*", "", saida)

            mapeamento = [
                (r"\bkg\b", "M"),
                (r"\bm\b", "L"),
                (r"\bs\b", "T"),
                (r"\bA\b", "I"),
                (r"\bK\b", r"\Theta"),
                (r"\bmol\b", "N"),
                (r"\bcd\b", "J"),
            ]

            dimensao = unidades_str
            for padrao, simbolo in mapeamento:
                dimensao = re.sub(padrao, lambda m, s=simbolo: s, dimensao)

            dim_fmt = self.formatar_estilo_livro(dimensao)
            return dim_fmt, None
        except Exception:
            return (
                None,
                f"❌ **Erro:** Não foi possível determinar a dimensão de `{expressao}`. "
                "Tente usar o nome da unidade (ex: `tesla`, `kelvin`, `volt`, `Joule`) ou constantes (ex: `G`, `k`, `c`).",
            )

    def constantes(self):
        lista = [
            ("c", "speedoflight", "Velocidade da luz no vácuo", "$c$"),
            ("h", "planck", "Constante de Planck", "$h$"),
            ("hbar", "hbar", "Constante reduzida de Planck ($h / 2\\pi$)", "$\\hbar$"),
            ("G", "gravitationalconstant", "Constante gravitacional de Newton", "$G$"),
            ("e", "elementarycharge", "Carga elemental do elétron", "$e$"),
            ("electronmass", "m_e", "Massa do elétron", "$m_e$"),
            ("epsilon0", "vacuumpermittivity", "Permissividade elétrica do vácuo ($\\varepsilon_0$)", "$\\varepsilon_0$"),
            ("mu0", "vacuumpermeability", "Permeabilidade magnética do vácuo ($\\mu_0$)", "$\\mu_0$"),
            ("k", "boltzmann", "Constante de Boltzmann", "$k_B$"),
            ("stefan", "stefanboltzmann", "Constante de Stefan-Boltzmann", "$\\sigma$"),
        ]

        tabela_dados = []
        for cmd_name, alias, desc, latex_sym in lista:
            try:
                res = subprocess.run(
                    [self._obter_comando_units(), "-t", cmd_name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                val = res.stdout.strip()
                val_fmt = self.formatar_estilo_livro(val)
                tabela_dados.append((cmd_name, alias, latex_sym, desc, val_fmt))
            except Exception:
                pass
        return tabela_dados



st.set_page_config(
    page_title="Plataforma E&M — GNU Units", page_icon="⚡", layout="centered"
)

if "em_session" not in st.session_state:
    st.session_state.em_session = EMUnitsSession()

em = st.session_state.em_session

st.title("⚡ Plataforma de Conversão e Análise E&M")
st.markdown(
    "**Backend:** [GNU Units](https://www.gnu.org/software/units/) | "
    "**Padrão de Formatação:** [IUPAC / E. Richard Cohen](https://iupac.org/what-we-do/books/greenbook/)"
)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🔄 Conversão",
        "📐 Análise Dimensional",
        "🌌 Constantes",
        "📜 Histórico da Sessão",
    ]
)

with tab1:
    st.subheader("Conversão e Decomposição de Unidades")
    col1, col2 = st.columns(2)
    with col1:
        entrada = st.text_input("Unidade / Expressão de Origem", "20 gauss")
    with col2:
        destino = st.text_input("Unidade de Destino (Opcional)", "tesla")

    if st.button("Calcular / Converter"):
        res, erro = em.calc(entrada, destino)
        if erro:
            st.error(erro)
        else:
            st.success("Resultado Formatado:")
            st.markdown(f"### {res}")

with tab2:
    st.subheader("Análise Dimensional Formal $[X] = M^a L^b T^c I^d \\Theta^e$")

    st.info(
        "**Convenção de Dimensões Fundamentais:**\n"
        "- **$M$**: Massa | **$L$**: Comprimento | **$T$**: Tempo | "
        "**$I$**: Corrente Elétrica | **$\\Theta$**: Temperatura"
    )

    expr_dim = st.text_input("Grandeza ou Expressão", "G")

    if st.button("Analisar Dimensão"):
        res_dim, erro = em.dim(expr_dim)
        if erro:
            st.error(erro)
        else:
            st.markdown(f"### **`[{expr_dim}]`** = {res_dim}")

with tab3:
    st.subheader("Constantes Fundamentais da Física")
    if st.button("Carregar Tabela de Constantes"):
        dados = em.constantes()
        md_table = (
            "| Símbolo (GNU Units) | Aliases / Nomes | Símbolo (LaTeX) | Descrição | Valor Formatado (IUPAC) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
        )
        for cmd_name, alias, latex_sym, desc, val in dados:
            md_table += f"| `{cmd_name}` | `{alias}` | {latex_sym} | {desc} | {val} |\n"
        st.markdown(md_table)

with tab4:
    st.subheader("Histórico de Operações da Sessão")
    if em.historico:
        md_hist = "| Entrada | Destino | Resultado |\n| :--- | :--- | :--- |\n"
        for item in em.historico:
            md_hist += f"| `{item['entrada']}` | `{item['destino']}` | {item['resultado']} |\n"
        st.markdown(md_hist)
    else:
        st.info("Nenhuma operação realizada nesta sessão ainda.")