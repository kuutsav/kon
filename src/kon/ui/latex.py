"""LaTeX math-to-Unicode converter.

Adapted from innomd by Innomatica GmbH (MIT License).
Source: https://github.com/Innomatica-GmbH/innomd
Commit: 35021c740a44d197cae4e8c0ab142e0b5e0cdaec
"""

import re

GREEK = {
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ε",
    r"\varepsilon": "ε",
    r"\zeta": "ζ",
    r"\eta": "η",
    r"\theta": "θ",
    r"\vartheta": "ϑ",
    r"\iota": "ι",
    r"\kappa": "κ",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\nu": "ν",
    r"\xi": "ξ",
    r"\pi": "π",
    r"\varpi": "ϖ",
    r"\rho": "ρ",
    r"\varrho": "ϱ",
    r"\sigma": "σ",
    r"\varsigma": "ς",
    r"\tau": "τ",
    r"\upsilon": "υ",
    r"\phi": "φ",
    r"\varphi": "ϕ",
    r"\chi": "χ",
    r"\psi": "ψ",
    r"\omega": "ω",
    r"\Gamma": "Γ",
    r"\Delta": "Δ",
    r"\Theta": "Θ",
    r"\Lambda": "Λ",
    r"\Xi": "Ξ",
    r"\Pi": "Π",
    r"\Sigma": "Σ",
    r"\Upsilon": "Υ",
    r"\Phi": "Φ",
    r"\Psi": "Ψ",
    r"\Omega": "Ω",
    r"\hbar": "ℏ",
    r"\ell": "ℓ",
    r"\Re": "ℜ",
    r"\Im": "ℑ",
}

OPERATORS = {
    r"\cdot": "·",
    r"\times": "×",
    r"\div": "÷",
    r"\pm": "±",
    r"\mp": "∓",
    r"\ast": "∗",
    r"\star": "⋆",
    r"\circ": "∘",
    r"\bullet": "•",
    r"\leq": "≤",
    r"\le": "≤",
    r"\geq": "≥",
    r"\ge": "≥",
    r"\neq": "≠",
    r"\ne": "≠",
    r"\approx": "≈",
    r"\equiv": "≡",
    r"\sim": "∼",
    r"\simeq": "≃",
    r"\cong": "≅",
    r"\propto": "∝",
    r"\ll": "≪",
    r"\gg": "≫",
    r"\infty": "∞",
    r"\partial": "∂",
    r"\nabla": "∇",
    r"\prime": "′",
    r"\sum": "∑",
    r"\prod": "∏",
    r"\coprod": "∐",
    r"\int": "∫",
    r"\iint": "∬",
    r"\iiint": "∭",
    r"\oint": "∮",
    r"\sqrt": "√",
    r"\rightarrow": "→",
    r"\to": "→",
    r"\leftarrow": "←",
    r"\gets": "←",
    r"\Rightarrow": "⇒",
    r"\Leftarrow": "⇐",
    r"\Leftrightarrow": "⇔",
    r"\leftrightarrow": "↔",
    r"\uparrow": "↑",
    r"\downarrow": "↓",
    r"\mapsto": "↦",
    r"\longrightarrow": "⟶",
    r"\longleftarrow": "⟵",
    r"\in": "∈",
    r"\notin": "∉",
    r"\ni": "∋",
    r"\subset": "⊂",
    r"\supset": "⊃",
    r"\subseteq": "⊆",
    r"\supseteq": "⊇",
    r"\cup": "∪",
    r"\cap": "∩",
    r"\setminus": "∖",
    r"\emptyset": "∅",
    r"\varnothing": "∅",
    r"\forall": "∀",
    r"\exists": "∃",
    r"\nexists": "∄",
    r"\neg": "¬",
    r"\land": "∧",
    r"\wedge": "∧",
    r"\lor": "∨",
    r"\vee": "∨",
    r"\therefore": "∴",
    r"\because": "∵",
    r"\ldots": "…",
    r"\cdots": "⋯",
    r"\vdots": "⋮",
    r"\ddots": "⋱",
    r"\dots": "…",
    r"\quad": " ",
    r"\qquad": " ",
    r"\,": " ",
    r"\;": " ",
    r"\:": " ",
    r"\!": "",
    r"\ ": " ",
    r"\%": "%",
    r"\$": "$",
    r"\&": "&",
    r"\#": "#",
    r"\_": "_",
    r"\{": "{",
    r"\}": "}",
    r"\deg": "°",
    r"\degree": "°",
    r"\langle": "⟨",
    r"\rangle": "⟩",
    r"\lfloor": "⌊",
    r"\rfloor": "⌋",
    r"\lceil": "⌈",
    r"\rceil": "⌉",
    r"\aleph": "ℵ",
    r"\Box": "□",
    r"\Diamond": "◇",
    r"\triangle": "△",
    r"\mathbb{R}": "ℝ",
    r"\mathbb{N}": "ℕ",
    r"\mathbb{Z}": "ℤ",
    r"\mathbb{Q}": "ℚ",
    r"\mathbb{C}": "ℂ",
    r"\mathbb{P}": "ℙ",
    r"\mathcal{L}": "ℒ",
    r"\mathcal{H}": "ℋ",
    r"\left": "",
    r"\right": "",
    r"\bigl": "",
    r"\bigr": "",
    r"\big": "",
    r"\Big": "",
    r"\Bigg": "",
    r"\displaystyle": "",
    r"\textstyle": "",
    r"\scriptstyle": "",
}

SUPERSCRIPT = str.maketrans(
    "0123456789+-=()nabcdefghijklmoprstuvwxyzABDEGHIJKLMNOPRTUVW",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿᵃᵇᶜᵈᵉᶠᵍʰᵢʲᵏˡᵐᵒʳˢᵗᵘᵛʷʸᵚᵜᵝᵞᵟᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁ",
)
SUBSCRIPT = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
_SYMBOL_ITEMS = sorted(list(GREEK.items()) + list(OPERATORS.items()), key=lambda x: -len(x[0]))
_SQRT_INDEX_RE = re.compile(r"\\sqrt\[([^\]]+)\]\{([^{}]+)\}")
_DISPLAY_DOLLAR_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_DISPLAY_BRACKET_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
_INLINE_DOLLAR_RE = re.compile(r"(?<!\$)\$(.+?)\$(?!\$)")
_INLINE_PAREN_RE = re.compile(r"\\\((.+?)\\\)")
_FENCE_RE = re.compile(r"(^```.*?^```)", re.DOTALL | re.MULTILINE)


def _to_super(s: str) -> str:
    if s and all(c in "0123456789+-=()nabcdefghijklmoprstuvwxyzABDEGHIJKLMNOPRTUVW" for c in s):
        return s.translate(SUPERSCRIPT)
    if len(s) == 1:
        return "^" + s
    return "^(" + s + ")"


def _to_sub(s: str) -> str:
    if s and all(c in "0123456789+-=()aehijklmnoprstuvx" for c in s):
        return s.translate(SUBSCRIPT)
    if len(s) == 1:
        return "_" + s
    return "_(" + s + ")"


def _balanced_groups(s: str, start: int) -> tuple[str, int] | None:
    if start >= len(s) or s[start] != "{":
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1 : i], i + 1
    return None


def _replace_command_with_groups(text: str, name: str, n_args: int, fn) -> str:
    out = []
    i = 0
    pattern = "\\" + name
    while i < len(text):
        if text.startswith(pattern, i):
            after = i + len(pattern)
            if after < len(text) and text[after].isalpha():
                out.append(text[i])
                i += 1
                continue
            args = []
            j = after
            while j < len(text) and text[j] == " ":
                j += 1
            ok = True
            for _ in range(n_args):
                grp = _balanced_groups(text, j)
                if grp is None:
                    ok = False
                    break
                args.append(grp[0])
                j = grp[1]
            if ok:
                out.append(fn(args))
                i = j
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _convert_math(tex: str) -> str:
    s = tex
    for _ in range(3):
        for cmd in (
            "text",
            "mathrm",
            "mathbf",
            "mathit",
            "mathsf",
            "mathtt",
            "operatorname",
            "textbf",
            "textit",
        ):
            s = _replace_command_with_groups(s, cmd, 1, lambda a: a[0])
    for _ in range(4):
        s = _replace_command_with_groups(
            s,
            "frac",
            2,
            lambda a: (
                f"({a[0]})/({a[1]})"
                if any(c in a[0] + a[1] for c in "+-**·× ")
                else f"{a[0]}/{a[1]}"
            ),
        )
        s = _replace_command_with_groups(
            s,
            "dfrac",
            2,
            lambda a: (
                f"({a[0]})/({a[1]})"
                if any(c in a[0] + a[1] for c in "+-**·× ")
                else f"{a[0]}/{a[1]}"
            ),
        )
        s = _replace_command_with_groups(
            s,
            "tfrac",
            2,
            lambda a: (
                f"({a[0]})/({a[1]})"
                if any(c in a[0] + a[1] for c in "+-**·× ")
                else f"{a[0]}/{a[1]}"
            ),
        )
    s = _SQRT_INDEX_RE.sub(lambda m: _to_super(m.group(1)) + "√(" + m.group(2) + ")", s)
    s = _replace_command_with_groups(s, "sqrt", 1, lambda a: "√(" + a[0] + ")")
    s = _replace_command_with_groups(s, "vec", 1, lambda a: a[0] + "⃗")
    s = _replace_command_with_groups(s, "hat", 1, lambda a: a[0] + "̂")
    s = _replace_command_with_groups(s, "bar", 1, lambda a: a[0] + "̄")
    s = _replace_command_with_groups(s, "dot", 1, lambda a: a[0] + "̇")
    for k, v in _SYMBOL_ITEMS:
        if k and k[-1].isalpha():
            s = re.sub(re.escape(k) + r"(?![A-Za-z])", v, s)
        else:
            s = s.replace(k, v)
    s = re.sub(r"\^\{([^{}]+)\}", lambda m: _to_super(m.group(1)), s)
    s = re.sub(r"_\{([^{}]+)\}", lambda m: _to_sub(m.group(1)), s)
    s = re.sub(r"\^(\\?[A-Za-z0-9+\-])", lambda m: _to_super(m.group(1).lstrip("\\")), s)
    s = re.sub(r"_(\\?[A-Za-z0-9+\-])", lambda m: _to_sub(m.group(1).lstrip("\\")), s)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def preprocess_latex(text: str) -> str:
    r"""Convert LaTeX math delimiters in *text* to Unicode, leaving code fences untouched.

    Handles inline ``$...$``, ``\(...\)``, display ``$$...$$``, and ``\[...\]``.
    Math inside fenced code blocks (`` ``` ``) is preserved verbatim.
    """
    if "$" not in text and "\\(" not in text and "\\[" not in text:
        return text

    def _process_part(part: str) -> str:
        part = _DISPLAY_DOLLAR_RE.sub(lambda m: "\n\n" + _convert_math(m.group(1)) + "\n\n", part)
        part = _DISPLAY_BRACKET_RE.sub(lambda m: "\n\n" + _convert_math(m.group(1)) + "\n\n", part)
        part = _INLINE_DOLLAR_RE.sub(lambda m: _convert_math(m.group(1)), part)
        return _INLINE_PAREN_RE.sub(lambda m: _convert_math(m.group(1)), part)

    if "```" not in text:
        return _process_part(text)

    parts = _FENCE_RE.split(text)
    out = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
            continue
        out.append(_process_part(part))
    return "".join(out)
