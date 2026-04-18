import json
import pandas as pd
from scipy import stats

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

def wilcoxon_test(df, label=""):
    if df.empty:
        return None

    ok = df[
        ~df.get("judge_error", pd.Series([False]*len(df))).fillna(False) &
        df["score_combinado_exp"].notna() &
        df["score_combinado_ctl"].notna() &
        (df["score_combinado_exp"] > 0) &
        (df["score_combinado_ctl"] > 0)
    ]

    if len(ok) < 10: return None

    exp = ok["score_combinado_exp"].tolist()
    ctl = ok["score_combinado_ctl"].tolist()

    diffs = [e - c for e, c in zip(exp, ctl)]
    if all(d == 0 for d in diffs): return None

    try:
        stat, p = stats.wilcoxon(exp, ctl, alternative="greater")
    except ValueError:
        stat, p = 0, 1.0

    all_scores = exp + ctl
    pooled_std = pd.Series(all_scores).std()
    effect_d = (sum(exp)/len(exp) - sum(ctl)/len(ctl)) / pooled_std if pooled_std > 0 else 0
    delta = sum(exp)/len(exp) - sum(ctl)/len(ctl)

    interp = "insignificante"
    if abs(effect_d) >= 0.2: interp = "pequeño"
    if abs(effect_d) >= 0.5: interp = "mediano"
    if abs(effect_d) >= 0.8: interp = "grande"

    sig = "✓ CONFIRMADO" if p < 0.05 else "✗ RECHAZADO"

    print(f"[{sig}] {label:<20} | n={len(ok):4d} | p={p:.6f} | Δ={delta:+.4f} | d={effect_d:+.4f} ({interp})")
    return {"p": p, "eff": effect_d, "n": len(ok)}

print("="*80)
print("ANÁLISIS WILCOXON - FASE DE CONFIRMACIÓN FINAL")
print("="*80)

# 1. ASOMBRO
df_as = load_jsonl("/home/maxi/Disco_de_Guardado/Cortex-Nexus/resultados_combinados/cycles_asombro_combinado.jsonl")
# Asombro General (todo el dataset Asombro Combinado)
wilcoxon_test(df_as, "Asombro Global")
# Especificamente Asombro Extremo (por ejemplo)
if "bloque" in df_as.columns:
    wilcoxon_test(df_as[df_as["bloque"] == "extremo"], "Asombro (Extremo)")

# 2. ÓPTIMO 2D
df_opt = load_jsonl("/home/maxi/Disco_de_Guardado/Cortex-Nexus/resultados_combinados/cycles_optimo_combinado.jsonl")
# Optimo General (Óptimo 2D)
if "condicion" in df_opt.columns:
    wilcoxon_test(df_opt[df_opt["condicion"] == "optimo_2d"], "Óptimo 2D")
    wilcoxon_test(df_opt[df_opt["condicion"] == "curiosidad_sola"], "Curiosidad Sola")

# 3. TÉCNICO (Confianza)
# Hay que tener cuidado aca: el dataset anterior tenia diferentes variables y el formato (condicion vs bloque).
df_tec = load_jsonl("/home/maxi/Disco_de_Guardado/Cortex-Nexus/resultados_combinados/cycles_tecnico_combinado.jsonl")
wilcoxon_test(df_tec, "Técnico Global")

# Buscar por bloque para tecnico
# Extraer el bloque/condicion si existe
if not df_tec.empty:
    if "bloque" in df_tec.columns:
        for b in sorted(df_tec["bloque"].dropna().unique()):
            wilcoxon_test(df_tec[df_tec["bloque"] == b], f"Técnico ({b})")
    elif "condicion" in df_tec.columns:
        for c in sorted(df_tec["condicion"].dropna().unique()):
            wilcoxon_test(df_tec[df_tec["condicion"] == c], f"Técnico ({c})")

print("="*80)
