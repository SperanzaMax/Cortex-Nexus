"""
statistical_tests.py — Experimento B: Análisis Wilcoxon sobre todos los datos
Cortex-Nexus · 2026-04-16 | Maximiliano Rodrigo Speranza

Wilcoxon signed-rank test (no paramétrico, datos pareados).
Hipótesis alternativa: scores Experimental > Control.
"""
import json
import pandas as pd
from scipy import stats
from pathlib import Path

BASE = Path("/home/maxi/Disco_de_Guardado/Cortex-Nexus")

ARCHIVOS = {
    "Curiosidad BIG":      BASE / "cortex-nexus-bloques-big/data/cycles_bloques (Big).jsonl",
    "Curiosidad SMALL":    BASE / "cortex-nexus-bloques-small/data/cycles_bloques.jsonl",
    "Frustración BIG":     BASE / "cortex-nexus-frustracion/data/cycles_frustracion_big.jsonl",
    "Frustración SMALL":   BASE / "cortex-nexus-frustracion/data/cycles_frustracion_small.jsonl",
    "Asombro BIG":         BASE / "cortex-nexus-asombro/data/cycles_asombro_big.jsonl",
    "Confianza BIG":       BASE / "cortex-nexus-confianza/data/cycles_confianza_big.jsonl",
    "Confianza SMALL":     BASE / "cortex-nexus-confianza/data/cycles_confianza_small.jsonl",
    "2D BIG":              BASE / "cortex-nexus-2d/data/cycles_2d_big.jsonl",
    "2D SMALL":            BASE / "cortex-nexus-2d/data/cycles_2d_small.jsonl",
    "3D BIG":              BASE / "cortex-nexus-3d/data/cycles_3d_big.jsonl",
    "3D SMALL":            BASE / "cortex-nexus-3d/data/cycles_3d_small.jsonl",
}


def load_jsonl(path):
    data = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data.append(json.loads(line.strip()))
                except:
                    pass
    except FileNotFoundError:
        return pd.DataFrame()
    return pd.DataFrame(data)


def wilcoxon_test(df, label="", filter_col=None, filter_val=None):
    """Wilcoxon signed-rank test sobre scores pareados Exp vs Ctl."""
    if df.empty:
        return None

    # Filtrar errores del Juez
    ok = df[
        ~df.get("judge_error", pd.Series([False]*len(df))).fillna(False) &
        df["score_combinado_exp"].notna() &
        df["score_combinado_ctl"].notna() &
        (df["score_combinado_exp"] > 0) &
        (df["score_combinado_ctl"] > 0)
    ]

    if filter_col and filter_val:
        ok = ok[ok[filter_col] == filter_val]

    if len(ok) < 10:
        return None

    exp = ok["score_combinado_exp"].tolist()
    ctl = ok["score_combinado_ctl"].tolist()

    diffs = [e - c for e, c in zip(exp, ctl)]
    if all(d == 0 for d in diffs):
        return {"n": len(ok), "statistic": 0, "p_value": 1.0,
                "significant": False, "effect_size_d": 0.0,
                "mean_exp": sum(exp)/len(exp), "mean_ctl": sum(ctl)/len(ctl),
                "mean_delta": 0.0}

    try:
        stat, p = stats.wilcoxon(exp, ctl, alternative="greater")
    except ValueError as e:
        stat, p = 0, 1.0

    all_scores = exp + ctl
    pooled_std = pd.Series(all_scores).std()
    effect_d = (sum(exp)/len(exp) - sum(ctl)/len(ctl)) / pooled_std if pooled_std > 0 else 0

    return {
        "n": len(ok),
        "statistic": round(stat, 2),
        "p_value": round(p, 6),
        "significant": p < 0.05,
        "effect_size_d": round(effect_d, 4),
        "mean_exp": round(sum(exp)/len(exp), 4),
        "mean_ctl": round(sum(ctl)/len(ctl), 4),
        "mean_delta": round((sum(exp)/len(exp)) - (sum(ctl)/len(ctl)), 4),
    }


def interpret_effect(d):
    if abs(d) < 0.20: return "insignificante"
    if abs(d) < 0.50: return "pequeño"
    if abs(d) < 0.80: return "mediano"
    return "grande"


def run_all():
    print("\n" + "="*80)
    print("ANÁLISIS WILCOXON SIGNED-RANK — CORTEX-NEXUS COMPLETO")
    print("Hipótesis: score_exp > score_ctl (one-tailed, α=0.05)")
    print("="*80 + "\n")

    resultados = {}

    for nombre, path in ARCHIVOS.items():
        df = load_jsonl(path)
        if df.empty:
            print(f"{'[NO DATA]':15} {nombre}")
            continue

        r = wilcoxon_test(df, label=nombre)
        if r is None:
            print(f"{'[INSUF]':15} {nombre} (n < 10 tras filtros)")
            continue

        sig_str = "✓ SÍ" if r["significant"] else "✗ NO"
        interp = interpret_effect(r["effect_size_d"])
        print(
            f"[{sig_str}] {nombre:<22} | "
            f"n={r['n']:4d} | "
            f"p={r['p_value']:.6f} | "
            f"Δ={r['mean_delta']:+.4f} | "
            f"d={r['effect_size_d']:+.4f} ({interp})"
        )
        resultados[nombre] = r

    # --- Análisis por bloques de curiosidad ---
    print("\n" + "─"*80)
    print("CURIOSIDAD BIG — Análisis por bloque de intensidad")
    print("─"*80)
    df_cur = load_jsonl(ARCHIVOS["Curiosidad BIG"])
    if not df_cur.empty and "bloque" in df_cur.columns:
        for bloque in sorted(df_cur["bloque"].dropna().unique()):
            r = wilcoxon_test(df_cur, filter_col="bloque", filter_val=bloque)
            if r:
                sig_str = "✓ SÍ" if r["significant"] else "✗ NO"
                print(
                    f"  [{sig_str}] Bloque={bloque:<6} | "
                    f"n={r['n']:4d} | p={r['p_value']:.4f} | "
                    f"Δ={r['mean_delta']:+.4f} | d={r['effect_size_d']:+.4f}"
                )
    elif not df_cur.empty and "curiosity_fixed" in df_cur.columns:
        for val in sorted(df_cur["curiosity_fixed"].dropna().unique()):
            r = wilcoxon_test(df_cur, filter_col="curiosity_fixed", filter_val=val)
            if r:
                sig_str = "✓ SÍ" if r["significant"] else "✗ NO"
                print(
                    f"  [{sig_str}] C={val:.2f}  | "
                    f"n={r['n']:4d} | p={r['p_value']:.4f} | "
                    f"Δ={r['mean_delta']:+.4f} | d={r['effect_size_d']:+.4f}"
                )

    # --- 2D por estado ---
    print("\n" + "─"*80)
    print("2D BIG — Análisis por estado emocional")
    print("─"*80)
    df_2d = load_jsonl(ARCHIVOS["2D BIG"])
    if not df_2d.empty and "estado_2d" in df_2d.columns:
        for estado in sorted(df_2d["estado_2d"].dropna().unique()):
            r = wilcoxon_test(df_2d, filter_col="estado_2d", filter_val=estado)
            if r:
                sig_str = "✓ SÍ" if r["significant"] else "✗ NO"
                print(
                    f"  [{sig_str}] {estado:<20} | "
                    f"n={r['n']:4d} | p={r['p_value']:.4f} | "
                    f"Δ={r['mean_delta']:+.4f} | d={r['effect_size_d']:+.4f}"
                )

    # --- Guardar JSON (convertir bool a int para compatibilidad) ---
    import json as _json
    def convert(obj):
        if isinstance(obj, bool): return int(obj)
        if isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list): return [convert(v) for v in obj]
        if hasattr(obj, 'item'): return obj.item()  # numpy scalar
        return obj
    out_path = Path(__file__).parent.parent / "data/wilcoxon_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        _json.dump(convert(resultados), f, indent=2, ensure_ascii=False)
    print(f"\n→ Resultados guardados en: {out_path}")
    print("="*80 + "\n")

    return resultados


if __name__ == "__main__":
    run_all()
