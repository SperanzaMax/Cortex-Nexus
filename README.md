# Cortex-Nexus: Inyección de Estados Emocionales Simulados en Modelos de Lenguaje
**Informe de Investigación Definitivo — Programa Completo con Validación Estadística**

[Read in English](README_EN.md)

**Maximiliano Rodrigo Speranza**  
*Cisco Networking Academy (Certificado); Universidad Tecnológica Nacional, Facultad Regional Buenos Aires (UTN-BA)*

**Colaboradores de IA:** Antigravity AI; Claude (Anthropic, diseño de investigación y análisis estadístico)  
**Curso:** Investigación Independiente en Sistemas de Inteligencia Artificial  
**Fecha:** 16 de abril de 2026

**Nota del Autor:** Toda la correspondencia relativa a este artículo debe dirigirse a Maximiliano Rodrigo Speranza. Contacto: maximiliano.speranza@gmail.com

---

## Resumen
El presente informe expone los resultados completos y estadísticamente validados del programa experimental Cortex-Nexus, el cual investigó si la inyección de estados emocionales simulados en los mensajes de sistema de los Modelos de Lenguaje Grande (LLMs) produce efectos medibles, reproducibles y específicos a cada emoción sobre la calidad del output generado. Se ejecutaron más de 3.664 ciclos experimentales repartidos entre cinco estados emocionales (curiosidad, frustración, asombro, confianza e interacciones 2D y 3D) con validación estadística formal mediante el test de Wilcoxon de rangos con signo (α = 0,05). 

Los hallazgos principales son: 
1. La inyección de **curiosidad** en modelos grandes (≥ 70 B de parámetros) mejora significativamente la calidad del output en tareas filosófico-exploratorias (W = 1773,0; p = 0,004; d de Cohen = 0,234).
2. La **configuración óptima** —curiosidad en 0,95 más fricción sintética baja en 0,20— supera estadísticamente a la curiosidad pura (p = 0,022; d = 0,263 frente a p = 0,034; d = 0,205).
3. El dominio técnico actúa como **control negativo perfecto**, con todos los p-valores entre 0,50 y 0,94 y efectos consistentemente negativos (d = -0,14), lo que demuestra especificidad de dominio estricta.
4. El asombro se aproxima asintóticamente al umbral estadístico (p = 0,058; d = 0,148; n = 294), lo que sugiere un efecto real pero estocásticamente errático.
5. La confianza opera en una capa epistémica independiente, modulando los patrones de hedging lingüístico sin afectar las puntuaciones de calidad del juez. 

La conclusión práctica central es que la inyección emocional en LLMs constituye un instrumento de precisión específico del dominio, no un potenciador universal de calidad.

**Palabras clave:** modelos de lenguaje grande, inyección emocional, prompting, curiosidad cognitiva, especificidad de dominio, diseño experimental controlado.

---

## Estructura del Repositorio

Este repositorio contiene todos los datos experimentales, el código fuente de los orquestadores y laboratorios de test, y la investigación final.

- `/cortex-nexus-validacion/`: Código fuente de la fase final de confirmación, incluyendo los tests estadísticos Wilcoxon (`analysis/statistical_tests.py`) y tests cross-domain.
- `/cortex-nexus-*/`: Carpetas con las diferentes fases experimentales (Asombro, Frustración, Confianza, Interacciones 2D/3D).
- `/resultados_combinados/` y `/resultados_confirmacion/`: Archivos de datos serializados `.jsonl` con las salidas y puntajes de los modelos interactuando bajo las condiciones estipuladas en el paper.
- `/cortex_nexus_PAPER_FINAL_v6.md`: El texto crudo del borrador antes del formateo APA7.

Este repositorio es el respaldo de "ciencia abierta" (open science) de la investigación para que cualquier entidad pueda verificar los datos y someter a análisis o escrutinio los más de 3.600 ciclos LLM que determinaron las conclusiones de este trabajo.

## Cómo citar
Speranza, M. R. (2026). *Cortex-Nexus: Inyección de Estados Emocionales Simulados en Modelos de Lenguaje.* Universidad Tecnológica Nacional, Facultad Regional Buenos Aires. Repositorio de GitHub.
