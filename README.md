# Predicción de la expansión de variantes de SARS-CoV-2 en la población mediante Aprendizaje Automático

Trabajo de Fin de Máster (TFM) que explora si los **haplotipos discordantes de clado** (CDH, antes referidos como UDS) detectados en secuenciación de alta profundidad anticipan qué mutaciones y familias Pango de SARS-CoV-2 van a crecer en las semanas siguientes, y cuánto tardarían en dominar globalmente.

## Hipótesis e idea general

La secuenciación de alta profundidad detecta, dentro de una misma muestra, variantes minoritarias que no coinciden con el clado consenso del paciente. La hipótesis del trabajo es que una parte de esos haplotipos discordantes no es ruido de secuenciación, sino señal temprana de mutaciones que más adelante se extienden en la población. El proyecto construye y evalúa un sistema predictivo en dos capas para poner esa hipótesis a prueba con datos reales de GISAID.

| Capa | Modelo | Pregunta que responde |
|---|---|---|
| Corto plazo | LightGBM (gradient boosting) | ¿Está creciendo esta mutación/familia ahora mismo? |
| Largo plazo | Regresión de Cox (supervivencia) | ¿Cuánto tardará en llegar a dominar? |

El sistema se evalúa a tres niveles de granularidad (mutación individual, familia Pango, familia + perfil mutacional Spike/NSP12), con validación temporal estricta (split fijo, walk-forward por épocas pandémicas) y comparación empírica frente a regresión logística, random forest y gradient boosting genérico.

## Estructura del repositorio

```
TFMi.ipynb                 Notebook principal (análisis, modelos, resultados)
run_streaming_standalone.py  Script auxiliar para el streaming de metadatos GISAID
                              (evita problemas de memoria dentro del notebook/IDE)
MemoriaTFM_2.docx/.pdf      Memoria del TFM
tfm_output/                 Figuras generadas por el notebook
tfm_data/                   Acumuladores intermedios de streaming (no versionado)
data/                       Datos de entrada (GISAID, FASTA) — no incluidos, ver abajo
requirements.txt            Dependencias de Python
```

## Datos

Los datos de secuencias y metadatos proceden de [GISAID](https://gisaid.org/) y de haplotipos discordantes de clado proporcionados por el grupo de biología del proyecto. Por las condiciones de uso de GISAID, **estos datos no se distribuyen en este repositorio**. Para reproducir el análisis es necesario:

1. Solicitar acceso a GISAID y descargar las secuencias/metadatos de Spike y NSP12 del periodo de estudio.
2. Colocar los ficheros descargados en `data/` siguiendo los nombres que espera el notebook (ver celdas iniciales de `TFMi.ipynb`).
3. Ejecutar `run_streaming_standalone.py` para generar `tfm_data/streaming_accumulators.pkl` antes de correr el notebook desde la sección de streaming (proceso de 30-50 min).

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Uso

Abrir `TFMi.ipynb` y ejecutar en orden. El notebook está organizado por secciones numeradas (Introducción, Estado del Arte, ingeniería de características, modelos de corto plazo, supervivencia, validación, proyección forward) que se corresponden con los capítulos de la memoria.

## Resultados principales

Split temporal fijo (evaluación de corto plazo, LightGBM):

| Dataset | AUC test | AP | N_test |
|---|---|---|---|
| M3-SPNSP (mutación individual + perfil Spike/NSP12) | 0.925 | 0.860 | 50.897 |
| M2 (familia Pango) | 0.886 | 0.628 | 6.241 |
| M3-ALL (mutación individual) | 0.854 | 0.690 | 186.352 |

El benchmark frente a regresión logística, random forest y gradient boosting confirma que LightGBM es el único modelo competitivo de forma consistente en las tres granularidades, con ventaja clara a nivel de familia Pango (donde las variables mutacionales muy correlacionadas hunden a los modelos lineales) y resultado más ajustado a nivel de mutación individual. Detalle completo, validación walk-forward, interpretabilidad (SHAP) y validación externa en la memoria.

## Memoria

El desarrollo completo (marco teórico, metodología, resultados, discusión y limitaciones) está en `MemoriaTFM_2.pdf`.

## Contexto académico

TFM del Máster Universitario en Sistemas Interactivos Inteligentes (MUSII), Universidad Autónoma de Madrid (UAM). Director: Manuel Sánchez-Montañés Isla.

## Autor

Sergio López González del Rey
