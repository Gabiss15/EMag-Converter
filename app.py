import re
import subprocess
import streamlit as st

#Classe de manipulação de unidades


class EMUnitsSession:

    def __init__(self):
        self.historico = []

    def _format_token(self, tok, is_denom=False):
        tok = tok.strip()
        if not tok:
            return ""
        if "^" in tok:
            base, exp = tok.split("^", 1)
            try:
                exp_num = int(exp)
                if is_denom:
                    exp_num = -exp_num
                return f"\\text{{{base}}}^{{{exp_num}}}"
            except ValueError:
                if is_denom:
                    return f"\\text{{{base}}}^{{-({exp})}}"
                return f"\\text{{{base}}}^{{{exp}}}"
        else:
            if is_denom:
                return f"\\text{{{tok}}}^{{{-1}}}"
            return f"\\text{{{tok}}}"

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
                    self._format_token(t, is_denom=True) for t in den_tokens if t
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
        cmd = ["units", "-t", entrada]
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
                "⚠️ **Erro:** O GNU Units não está instalado no sistema.",
            )
        except subprocess.CalledProcessError:
            return None, "❌ **Erro:** Expressão ou unidade incompatível."

    def dim(self, expressao):
        try:
            res = subprocess.run(
                ["units", "-t", expressao],
                capture_output=True,
                text=True,
                check=True,
            )
            saida = res.stdout.strip()
            unidades_str = re.sub(r"^[\d\.\+eE\-]+\s*", "", saida)

            mapeamento = [
                (r"\bkg\b", "M"),
                (r"\bm\b", "L"),
                (r"\bs\b", "T"),
                (r"\bA\b", "I"),
                (r"\bK\b", "Θ"),
                (r"\bmol\b", "N"),
                (r"\bcd\b", "J"),
            ]

            dimensao = unidades_str
            for padrao, simbolo in mapeamento:
                dimensao = re.sub(padrao, simbolo, dimensao)

            dim_fmt = self.formatar_estilo_livro(dimensao)
            return dim_fmt, None
        except Exception:
            return (
                None,
                f"❌ **Erro:** Não foi possível determinar a dimensão de `{expressao}`.",
            )

    def constantes(self):
        lista = [
            ("c", "Velocidade da luz no vácuo", ["units", "-t", "c"]),
            ("h", "Constante de Planck", ["units", "-t", "h", "kg m^2 / s"]),
            (
                "hbar",
                "Constante reduzida de Planck (h / 2π)",
                ["units", "-t", "hbar", "kg m^2 / s"],
            ),
            ("G", "Constante gravitacional de Newton", ["units", "-t", "G"]),
            ("e", "Carga elemental do elétron", ["units", "-t", "e", "A s"]),
            (
                "m_e",
                "Massa do elétron",
                ["units", "-t", "electronmass", "kg"],
            ),
            (
                "epsilon0",
                "Permissividade elétrica do vácuo (ε₀)",
                ["units", "-t", "epsilon0", "A^2 s^4 / kg m^3"],
            ),
            (
                "mu0",
                "Permeabilidade magnética do vácuo (μ₀)",
                ["units", "-t", "mu0", "kg m / A^2 s^2"],
            ),
        ]

        tabela_dados = []
        for sim, desc, cmd in lista:
            try:
                val = subprocess.run(
                    cmd, capture_output=True, text=True
                ).stdout.strip()
                val_fmt = self.formatar_estilo_livro(val)
                tabela_dados.append((sim, desc, val_fmt))
            except Exception:
                pass
        return tabela_dados


# --- FRONTEND COM STREAMLIT ---

st.set_page_config(
    page_title="Plataforma E&M — GNU Units", page_icon="⚡", layout="centered"
)

if "em_session" not in st.session_state:
    st.session_state.em_session = EMUnitsSession()

em = st.session_state.em_session

st.title("⚡ Plataforma de Conversão e Análise E&M")
st.caption(
    "Backend: GNU Units | Padrão de Formatação: IUPAC / E. Richard Cohen"
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
    st.subheader("Análise Dimensional Formal $[X] = M^a L^b T^c I^d$")
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
            "| Símbolo | Descrição | Valor (Padrão Livro) |\n| :--- | :--- | :--- |\n"
        )
        for sim, desc, val in dados:
            md_table += f"| `{sim}` | {desc} | {val} |\n"
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