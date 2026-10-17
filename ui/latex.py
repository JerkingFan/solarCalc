"""Render formula cards for the UI.

Two rendering modes:
- ensure_formula_images(): static formulas from the FORMULAS dict.
- render_dynamic_formula(): arbitrary LaTeX with substituted values (steps).


If matplotlib is installed, formulas are rendered from LaTeX/mathtext. Otherwise
a Pillow fallback renders clean Unicode formula cards. Images are cached in
assets/formulas and displayed through HelloImGui textures.

All cards are rendered with dark text so they are readable on the light theme.
"""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FORMULA_DIR = BASE_DIR / "assets" / "formulas"

FORMULAS: dict[str, tuple[str, str, int]] = {
    "w_day": (
        r"W_{day}=\frac{W_{ac}/\eta_{inv}+W_{dc}}{7}",
        "W_day = (W_ac / eta_inv + W_dc) / 7",
        15,
    ),
    "c_req": (
        r"C_{req}=\frac{W_{day}\,n}{U_{sys}\,DoD\,k_t}",
        "C_req = W_day * n / (U_sys * DoD * k_t)",
        15,
    ),
    "p_pv": (
        r"P_{pv}=\frac{W_{day}}{PSH\,\eta_{sys}\,k_{relief}}",
        "P_pv = W_day / (PSH * eta_sys * k_relief)",
        15,
    ),
    "n_pv": (
        r"N_{pv}=\left\lceil\frac{P_{pv}}{P_{panel}}\right\rceil",
        "N_pv = ceil(P_pv / P_panel)",
        15,
    ),
    "voc_string": (
        r"V_{oc,string}(T_{min})=V_{oc}N_s\left(1+\frac{|k_{voc}|(25-T_{min})}{100}\right)",
        "V_oc,string(Tmin) = V_oc * N_s * (1 + |k_voc|*(25-Tmin)/100)",
        15,
    ),
    "inverter_surge": (
        r"P_{surge}=\max_i\left(P_{other}+P_i k_i\right)",
        "P_surge = max(P_other + P_i * k_i)",
        15,
    ),
    "cable": (
        r"S=\max\left(\frac{2\rho L I}{\Delta U_{max}},\,S_{I_{dd}}\right)",
        "S = max(2*rho*L*I / dU_max, S_Idd)",
        15,
    ),
    "w1_prof": (
        r"W_1=\frac{W_{ac}}{\eta_{inv}}",
        "W1 = W_ac / eta_inv",
        15,
    ),
    "e_sigma": (
        r"E_{\sigma}=\frac{W_{day}}{U_{sys}}",
        "E_sigma = W_day / U_sys",
        15,
    ),
    "i_charge": (
        r"I_{charge}=\frac{P_{pv}}{U_{sys}}",
        "I_charge = P_pv / U_sys",
        15,
    ),
    # --- Academic methodic formulas (BGUIR) ---
    "wi": (r"W_i = P_i \cdot t", "W_i = P_i * t", 15),
    "w0": (r"W_0 = \sum W_i", "W_0 = sum W_i", 15),
    "w1": (r"W_1 = W_0 \cdot 1.2", "W_1 = W_0 * 1.2", 15),
    "e_sut_acad": (
        r"E_{sut} = \frac{(W_1 / U_i) + (W_2 / U)}{7}",
        "E_sut = ((W_1 / U_i) + (W_2 / U)) / 7",
        15,
    ),
    "c_acad": (r"C = \frac{E_{sut} \cdot n}{0.2}", "C = E_sut * n / 0.2", 15),
    "c_poln_acad": (r"C_{poln} = C \cdot 1.2", "C_poln = C * 1.2", 15),
    "n_akb_acad": (r"N_{akb} = \frac{C_{poln}}{C_{nom}}", "N_akb = C_poln / C_nom", 15),
    "n_posl_acad": (r"N_{posl} = \frac{U}{U_{akb}}", "N_posl = U / U_akb", 15),
    "tp_acad": (r"t_p = \frac{E_{dek} \cdot 0.1}{31}", "t_p = E_dek * 0.1 / 31", 15),
    "p_sun_acad": (r"P = \frac{E_{sut} \cdot 1.2}{t_p}", "P = E_sut * 1.2 / t_p", 15),
    "nm_acad": (r"N_m = \frac{P}{P_p}", "N_m = P / P_p", 15),
    "nm_posl_acad": (r"n_m = \frac{U}{U_m}", "n_m = U / U_m", 15),
    "i_load_acad": (r"I = \frac{P_{obsh}}{U}", "I = P_obsh / U", 15),
    "r_cable_acad": (r"R = \frac{\Delta U}{I \cdot L}", "R = dU / (I * L)", 15),
    # --- Professional / detailed analysis formulas ---
    "w_sut_prof": (
        r"W_{sut} = \frac{W_{perem} / \eta_{inv} + W_{post}}{7}",
        "W_sut = (W_perem / eta_inv + W_post) / 7",
        15,
    ),
    "c_req_prof": (
        r"C_{treb} = \frac{W_{sut} \cdot n}{U_{sist} \cdot DoD \cdot k_{temp}}",
        "C_treb = W_sut * n / (U_sist * DoD * k_temp)",
        15,
    ),
    "n_total_prof": (
        r"N_{obsh} = \left(\frac{U_{sist}}{U_{akb}}\right) \times \left\lceil \frac{C_{treb}}{C_{akb}} \right\rceil",
        "N_obsh = (U_sist / U_akb) * ceil(C_treb / C_akb)",
        15,
    ),
    "p_pv_prof": (
        r"P_{paneley} = \frac{W_{sut}}{PSH \cdot \eta_{sist} \cdot k_{relief}}",
        "P_paneley = W_sut / (PSH * eta_sist * k_relief)",
        15,
    ),
    "n_pv_prof": (
        r"N_{paneley} = \left\lceil \frac{P_{paneley}}{P_{modulya}} \right\rceil",
        "N_paneley = ceil(P_paneley / P_modulya)",
        15,
    ),
    "voc_prof": (
        r"U_{xx,string}(T_{min}) = U_{xx} \cdot N_{posl} \cdot [1 + \alpha_{Uxx} \cdot (T_{min} - 25)] < U_{mrpp,max}",
        "U_oc,string(Tmin) = U_oc * N_ser * (1 + alpha*(Tmin-25)) < U_mppt_max",
        15,
    ),
    "p_pusk_prof": (
        r"P_{pusk} = \max_i (P_{ost} + P_i \cdot k_{pusk})",
        "P_pusk = max(P_ost + P_i * k_pusk)",
        15,
    ),
    "s_cable_prof": (
        r"S = \max\left(\frac{2 \cdot \rho \cdot L \cdot I}{\Delta U_{dop}}, \, S_{I_{dop}}\right)",
        "S = max(2*rho*L*I / dU_dop, S_Idd)",
        15,
    ),
}

_CACHE: dict[str, str] | None = None


def _load_font(size: int):
    from PIL import ImageFont

    candidates = (
        r"C:\Windows\Fonts\cambria.ttf",
        r"C:\Windows\Fonts\cambriai.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def _render_with_matplotlib(latex: str, path: Path, fontsize: int = 15) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
    except Exception:  # noqa: BLE001
        return False

    try:
        fig = Figure(figsize=(0.1, 0.1), dpi=220)
        fig.patch.set_alpha(0.0)
        FigureCanvasAgg(fig)
        fig.text(0.0, 0.5, f"${latex}$", fontsize=fontsize, color="#1a1a1a", va="center")
        fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=0.08)
        return True
    except Exception:  # noqa: BLE001
        return False


def _render_with_pillow(text: str, path: Path) -> bool:
    try:
        from PIL import Image, ImageDraw
    except Exception:  # noqa: BLE001
        return False

    font = _load_font(30)
    probe = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox((0, 0), text, font=font)
    width = max(1, bbox[2] - bbox[0] + 34)
    height = max(1, bbox[3] - bbox[1] + 26)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.text((17 - bbox[0], 13 - bbox[1]), text, font=font, fill=(26, 26, 26, 255))
    image.save(path)
    return True


def ensure_formula_images() -> dict[str, str]:
    """Generate missing formula images and return {key: asset_path}."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    FORMULA_DIR.mkdir(parents=True, exist_ok=True)
    images: dict[str, str] = {}
    for key, item in FORMULAS.items():
        if len(item) >= 3:
            latex, fallback_text, fontsize = item[0], item[1], item[2]
        else:
            latex, fallback_text, fontsize = item[0], item[1], 15
        path = FORMULA_DIR / f"{key}.png"
        rendered = _render_with_matplotlib(latex, path, fontsize)
        if not rendered and not path.exists():
            _render_with_pillow(fallback_text, path)
        if path.exists():
            images[key] = f"assets/formulas/{key}.png"
    _CACHE = images
    return images


def formula_asset(key: str) -> str | None:
    return ensure_formula_images().get(key)


def render_dynamic_formula(latex: str, fontsize: int = 13) -> str | None:
    """Render an arbitrary LaTeX string (with substituted values) to a cached PNG asset."""
    import hashlib

    FORMULA_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{fontsize}:{latex}".encode("utf-8")).hexdigest()[:16]
    path = FORMULA_DIR / f"dyn_{key}.png"
    if not path.exists():
        if not _render_with_matplotlib(latex, path, fontsize):
            return None
    return f"assets/formulas/dyn_{key}.png"
