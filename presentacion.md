# Guion de Presentación TFM — Sergio López González del Rey
---

# PARTE 1: GUION DE PRESENTACIÓN

---

## BLOQUE 1 — El problema biológico

"El SARS-CoV-2 no circula como una sola cepa. En cualquier momento dado, hay decenas o cientos de variantes circulando simultáneamente en todo el mundo, cada una con su propio perfil mutacional. La pregunta que se hacen todos los sistemas de vigilancia epidemiológica es: ¿cuál de estas variantes va a crecer y dominar en las próximas semanas?"

"Hoy eso se hace de forma reactiva: una variante empieza a crecer, aumenta su frecuencia en GISAID, los epidemiólogos lo detectan cuando ya está ocurriendo. Mi trabajo intenta hacer eso de forma predictiva: antes de que ocurra."

"Para eso uso dos fuentes de información. La primera es GISAID, con 17,5 millones de secuencias genómicas de todo el mundo. La segunda son datos de Ultra-Deep Sequencing de 28 pacientes."

"La hipótesis de partida es que dentro de un paciente ya están circulando las variantes del futuro. Cuando una persona se infecta, el virus no es una población homogénea: es una cuasiespecies, un enjambre de variantes con distintas mutaciones. La mayoría es el clado principal, pero una pequeña fracción tiene mutaciones características de clados que todavía no existen a escala poblacional."

**Analogía clave:**
> "Es como si en una sala con 100 personas, 95 llevan el mismo abrigo de invierno, pero 5 ya llevan el abrigo que estará de moda el año que viene. El UDS detecta esos 5."

**Pregunta probable: "¿Por qué 28 pacientes?"**
> "No es suficiente estadísticamente para entrenar el modelo, y eso es parte del resultado. Los 28 pacientes sirven para demostrar el concepto biológico: que el UDS detecta clados que luego emergen. Pero no son suficientes para mejorar la predicción del modelo. Eso lo discutimos en limitaciones."

---

## BLOQUE 2 — Los datos

**Qué decir:**

"Los datos de GISAID son secuencias de dos proteínas: Spike y NSP12. Spike porque es la proteína más bajo presión inmunológica, la que cambia más rápido y define la identidad inmunológica de la variante. NSP12 es la RNA polimerasa, más conservada, útil como marcador filogenético."

"De cada secuencia, Nextclade asigna un clado: una etiqueta jerárquica como 'XFG.2.3.1'. Ese es el nivel de análisis del modelo: no el linaje Pango, no la secuencia individual, sino el par clado × semana."

"Para los datos de UDS: tengo un Excel con 28 pacientes que contiene los haplotipos discordantes — aquellos haplotipos dentro de cada paciente cuyas mutaciones son características de un clado distinto al del aislado consenso. En otras palabras: la señal minoritaria dentro de cada paciente que coincide con clados que después emergieron globalmente."

**Pregunta probable: "¿Qué es Nextclade?"**
> "Nextclade es una herramienta de Nextstrain que alinea cada secuencia contra la referencia Wuhan-Hu-1 y la ubica en un árbol filogenético, asignando el clado según el perfil de mutaciones. La nomenclatura de Nextclade es más estable que Pango para análisis temporales largos."

---

## BLOQUE 3 — El modelo: qué hace y cómo funciona

**Qué decir:**

"La unidad de análisis es un par clado × semana. Para cada clado en cada semana, el modelo responde una pregunta binaria: ¿este clado va a crecer la semana siguiente?"

"Para responder esa pregunta, el modelo recibe 94 variables numéricas organizadas en tres grupos:"

"Primer grupo — variables temporales: la frecuencia actual del clado (freq_t0), la pendiente de crecimiento en las últimas 4 semanas (slope_4w), la aceleración, la frecuencia media en 8 semanas... El 'historial médico' del clado."

"Segundo grupo — variables geográficas: en cuántos países está presente, cómo está expandiéndose. Un clado que crece en nuevos países es una señal distinta a uno estancado."

"Tercer grupo — 80 variables mutacionales: variables binarias (0/1) que indican si ese clado tiene cada una de las 80 mutaciones aminoacídicas con mayor varianza temporal en el dataset. Las más informativas sobre identidad y evolución."

"El algoritmo es LightGBM: gradient boosting sobre árboles de decisión."

**Analogía para LightGBM:**
> "Imagina 500 médicos residentes. Cada uno toma la historia clínica del clado y diagnostica si va a crecer. Pero en vez de ser independientes, cada médico nuevo se especializa en corregir los errores del anterior. Al final votan, con más peso para los que han demostrado más aciertos. Eso es gradient boosting. LightGBM es la versión eficiente que procesa 17 millones de secuencias en tiempo razonable."

"Lo que el modelo produce es una probabilidad entre 0 y 1 para cada clado. Eso me da un ranking: los 15 primeros son los más probables de expandirse."

**Pregunta probable: "¿Por qué no una red neuronal?"**
> "LightGBM es el estándar para datos tabulares estructurados. Para una tabla de 94 variables numéricas, LightGBM suele ganar o empatar con redes neuronales con mucho menos coste computacional y más interpretabilidad."

---

## BLOQUE 4 — Rigor metodológico: data leakage

**Qué decir:**

"Data leakage significa que el modelo, sin que yo me dé cuenta, tiene acceso durante el entrenamiento a información que en la realidad solo estaría disponible en el futuro. Es el equivalente a que un estudiante vea las respuestas del examen antes de darlo."

"Había dos fuentes de leakage que identifiqué y corregí:"

"Primera: para seleccionar las 80 mutaciones más informativas, calculé la varianza de cada mutación. Si uso todos los datos incluyendo los de test (el futuro), estoy usando información futura para decidir qué variables entran. Corrección: la selección se hace solo con los datos de entrenamiento."

"Segunda: el modelo predice si un clado va a crecer la semana siguiente. Pero en las últimas semanas del período de entrenamiento, el 'futuro' ya había ocurrido dentro del período de datos disponibles. Corrección: excluir las últimas N semanas antes del corte temporal."

"Resultado contraintuitivo: corregir estos sesgos mejoró el AUC de 0,79 a 0,82. La selección de features más limpia le permite al modelo aprender la señal real."

---

## BLOQUE 5 — Resultados del modelo GISAID

**Qué decir:**

"El modelo principal, entrenado solo con datos de GISAID, alcanza un AUC de 0,82. El AUC mide la probabilidad de que el modelo, dado un clado que realmente creció y uno que no, asigne probabilidad más alta al que creció. 0,5 = azar. 1,0 = perfecto. 0,82 es sólido."

"Para uso real la métrica más relevante es el Average Precision (AP): el modelo alcanza AP = 0,27 frente a 0,05 del azar. Un lift de 5,6x. En términos prácticos: de cada 10 clados que el sistema señala como emergentes, 2-3 lo son realmente. No es un oráculo, es una herramienta de priorización."

"La validación walk-forward simula cuatro transiciones pandémicas reales, entrenando con oleadas pasadas y prediciendo la siguiente:"

| Transición | AUC |
|------------|-----|
| Pre-VOC → Delta | 0,77 |
| Delta → Omicron BA.1 | 0,88 |
| Omicron BA.1 → BA.4/5+ | 0,74 |
| BA.4/5+ → Post-2023 | 0,81 |
| **Media** | **0,80** |

"Lo más relevante: el AUC no colapsa en la transición a Omicron, el mayor salto evolutivo de la pandemia. Esto indica que el modelo captura señales de selección positiva que trascienden la identidad de la variante concreta."

**Pregunta probable: "¿Cómo se compara con otros trabajos?"**
> "Maher et al. (Science Translational Medicine, 2022) alcanzaron AUC 0,92–0,97 pero con features experimentales: energía de unión a ACE2, escape a anticuerpos medido experimentalmente. Yo uso solo frecuencias y mutaciones de secuencia. La diferencia se explica por las features, no por el algoritmo."

---

## BLOQUE 6 — El UDS: observación retrospectiva

**Qué decir:**

"Para cada haplotipo discordante de los 28 pacientes, calculé el lead-time: la diferencia en semanas entre la fecha de la muestra del paciente y la fecha en que ese clado alcanzó el 3% de frecuencia global en GISAID."

"Los resultados: lead-time siempre positivo (el UDS detectó siempre antes), media de ~25 semanas, mejor caso 50 semanas (clado 22E)."

"Hay que interpretar esto con precisión. El dataset contiene únicamente los haplotipos discordantes cuyas mutaciones coincidieron con clados que posteriormente emergieron. Los haplotipos que no emergieron no están incluidos. Por tanto, el 100% de lead-time positivo es una consecuencia del diseño retrospectivo del dataset, no una tasa de acierto prospectivo que se habría conseguido en tiempo real."

"Lo que sí podemos afirmar: el espacio mutacional intrapaciente se solapó con la evolución poblacional del virus. Esto valida biológicamente la teoría de cuasiespecies: el virus ya estaba explorando dentro del paciente las mutaciones que la presión selectiva acabaría seleccionando a escala global."

**Pregunta probable: "¿El cuello de botella de transmisión no elimina esas variantes?"**
> "Esa es exactamente la pregunta correcta. El cuello de botella de SARS-CoV-2 es de 1-8 viriones fundadores. Las variantes minoritarias se pierden en cada transmisión. Pero el lead-time largo (25 semanas) lo explica: esas mutaciones no se transmiten directamente de ese paciente al mundo. Confieren ventaja selectiva y surgen repetidamente en múltiples linajes por evolución convergente. El UDS las detecta en el reservorio intrapaciente antes de que la presión selectiva las lleve a frecuencias poblacionales."

---

## BLOQUE 7 — La contribución del UDS al modelo: resultado nulo

**Qué decir:**

"Cuando añado las features de UDS al modelo —el IPE score, el número de haplotipos discordantes por clado— el AUC no mejora significativamente. ΔAUC = −0,002, IC 95% [−0,012; +0,006], p = 0,68."

"¿Por qué? Porque el modelo ya tiene 17,5 millones de secuencias de GISAID. Añadir información de 28 pacientes, estadísticamente, no mueve la aguja. Es como intentar cambiar la temperatura de un océano con un cubo de agua caliente."

"¿Esto invalida el TFM? No. Son dos resultados distintos. El lead-time —que el UDS detecta clados semanas antes de GISAID— es un hallazgo biológico real medido retrospectivamente. Lo que no ocurre es que esa detección temprana mejore el modelo con 28 pacientes. Para eso haría falta 500-1.000 pacientes con un dataset diseñado específicamente."

"Un resultado nulo bien documentado tiene valor científico: establece el baseline y define el umbral de muestra necesario."

---

## BLOQUE 8 — Validación prospectiva real

**Qué decir:**

"En febrero de 2026, el modelo generó un ranking de los 139 clados activos. En mayo de 2026 consulté covSpectrum para ver qué había ocurrido realmente en abril."

"Los dos clados que dominan globalmente en abril de 2026 son la familia XFG* (70% de frecuencia global) y la familia XDV* (16,4%). El modelo tenía 5 posiciones XFG en el top-15 y 2 posiciones XDV (puestos 13 y 15)."

"El modelo no predijo el sublinaje exacto. Predijo qué familias virales dominarían, con 2,5 meses de antelación."

"Caveat: los datos de covSpectrum solo tienen ~2.400 secuencias abiertas porque la mayoría de secuencias GISAID son restringidas."

---

## BLOQUE 9 — Interpretabilidad SHAP

**Qué decir:**

"SHAP es el método estándar para interpretar modelos de ML. Te dice, para cada predicción, cuánto contribuyó cada variable al resultado, de forma que sumando todas las contribuciones recuperas la predicción original."

"El análisis global de importancia revela que las tres features más informativas son variables de trayectoria dinámica: freq_t0 (frecuencia actual), slope_4w (pendiente de crecimiento en 4 semanas) y geo_growth (expansión geográfica). El modelo identifica variantes principalmente por su dinámica de crecimiento, no por la presencia de mutaciones específicas aisladas."

"La primera mutación en el ranking global es Spike G252V (posición 11 de 94). Esta posición está en el NTD de Spike, en el loop N5 (residuos ~246–260), uno de los principales sitios antigénicos del NTD reconocidos por anticuerpos neutralizantes. Su importancia refleja la presión inmunológica sostenida sobre este dominio."

"Análisis de ablación: eliminar freq_t0 reduce el AUC en 0,033; eliminar mutaciones de Spike, en 0,031; eliminar la trayectoria temporal, en 0,012; eliminar el contexto geográfico, en solo 0,003."

---

## BLOQUE 10 — Limitaciones y trabajo futuro

1. **Cohorte UDS pequeña.** 28 pacientes establecen la prueba de concepto pero son insuficientes para contribución predictiva.

2. **Sesgo geográfico de GISAID.** 78% de secuencias de países de renta alta. Una variante que emerge primero en África Central podría ser invisible hasta mucho después.

3. **Ventana de predicción.** El modelo predice la semana siguiente, no dominancia a 3–6 meses. La ventana operacional útil es 4–8 semanas.

4. **Emergencias abruptas.** Clados con freq_t0 < 0,03 que emergen sin gradiente previo detectable (como JN.1 en su fase inicial). El modelo no los ve porque no tienen historia.

5. **Pacientes UDS desactualizados.** Los pacientes son de 2020–2023. Los clados emergentes de 2025–2026 (XFG, LP.8) no tienen señal UDS directa.

**Trabajo futuro más importante:** ampliar la cohorte UDS a 500–1.000 pacientes con recogida prospectiva de TODOS los haplotipos discordantes (no solo los que emergieron), para poder entrenar un modelo a nivel intrapaciente.

---

## CIERRE

"En resumen: he construido un sistema que procesa 17,5 millones de secuencias genómicas y predice qué variantes del SARS-CoV-2 van a expandirse, con AUC de 0,82 y validación prospectiva confirmada. El componente UDS demuestra biológicamente que el espacio mutacional intrapaciente anticipa la evolución poblacional del virus, coherente con la teoría de cuasiespecies. La arquitectura del sistema es aplicable en principio a cualquier virus RNA con vigilancia genómica activa."

---

## Hoja de referencia rápida — Números clave

| Dato | Valor |
|------|-------|
| Secuencias GISAID | 17,5 millones |
| Pacientes UDS | 28 |
| Variables del modelo | 94 |
| AUC modelo base | **0,82** |
| Walk-forward medio | **0,80** (rango 0,74–0,88) |
| ΔAUC UDS | **−0,002** (p=0,68, no significativo) |
| Lead-time (retrospectivo) | hasta 50 semanas; media ~25 semanas |
| Prospectiva XFG* | **70% global** (abril 2026) |
| Prospectiva XDV* | **16,4% global** (abril 2026) |
| Top feature global | **freq_t0 + slope_4w** (dinámicas) |
| Top mutación | **Spike G252V** (NTD, loop N5) |

---

## Las frases clave

**Para empezar:**
> "El objetivo es convertir 17,5 millones de secuencias en un número entre 0 y 1 que me diga qué variante del coronavirus va a expandirse la semana que viene, antes de que ocurra."

**Para el resultado nulo UDS:**
> "El UDS revela el espacio mutacional que el virus ya está explorando dentro del paciente. Pero con 28 pacientes y un dataset retrospectivo, no podemos enseñárselo al modelo. Eso no es un fallo, es el tamaño de muestra necesario para el siguiente paso."

**Para terminar:**
> "La validación prospectiva lo confirma: las familias que el modelo puso en el top-15 en febrero son las que dominan globalmente en mayo. El sistema funciona."

---
---

# PARTE 2: CONCEPTOS CLAVE PARA EXPLICAR EN PROFUNDIDAD

---

## A — Qué son los nuevos resultados y qué ha cambiado

Los resultados cambiaron porque se corrigieron dos errores metodológicos (data leakage). Aquí la comparación:

| Métrica | Antes (con leakage) | Ahora (corregido) | Interpretación |
|---------|---------------------|-------------------|----------------|
| AUC modelo base | 0,79 | **0,82** | Mejoró al limpiar el sesgo |
| ΔAUC UDS | +0,009 (p=0,013) | **−0,002 (p=0,68)** | UDS no mejora el modelo |
| Walk-forward medio | 0,82 | **0,80** | Más conservador y realista |
| Lead-time | "7-8 semanas" | **media 25 semanas** | Mejor estimación |

**La conclusión principal cambia:** antes parecía que el UDS mejoraba significativamente el modelo. Ahora está claro que no. La contribución real del UDS es como validación biológica (cuasiespecies), no como predictor adicional.

---

## B — Por qué el UDS no mejora el modelo (y por qué es honesto decirlo)

Un resultado nulo tiene tres causas posibles:

1. **La hipótesis es incorrecta** — el UDS no anticipa variantes. *Descartado: los lead-times demuestran que sí lo hace, pero retrospectivamente.*

2. **El diseño no es adecuado** — el dataset UDS es retrospectivo y curado, no prospectivo y completo. *Esta es la causa principal.*

3. **La muestra es insuficiente** — 28 pacientes no son suficientes para que el modelo aprenda. *También relevante.*

**Para la bióloga:** el resultado nulo es más valioso que un falso positivo. Establece exactamente qué habría que hacer para que el UDS contribuya.

---

## C — La diferencia fundamental entre GISAID y el Excel UDS

Esta es la distinción más importante para entender por qué el modelo funciona con uno y no con el otro.

**GISAID** contiene secuencias consenso (la variante dominante de cada paciente), pero de TODOS los clados que circulan en la población, incluidos los raros que luego desaparecen y los raros que luego dominan. El modelo aprende a distinguir "raro y creciendo" de "raro y desapareciendo". Tiene ganadores Y perdedores en todas las frecuencias.

**Excel UDS** contiene haplotipos discordantes (variantes minoritarias dentro del paciente), pero solo aquellos que coincidieron con clados que posteriormente emergieron globalmente. No tiene los haplotipos que no emergieron. Solo tiene ganadores.

| | GISAID | Excel UDS |
|--|--------|-----------|
| Nivel de diversidad | Entre pacientes (población) | Dentro del paciente |
| ¿Tiene perdedores? | ✅ Sí | ❌ No |
| ¿Se puede entrenar un modelo? | ✅ Sí | ❌ No (solo positivos) |
| Señal temporal | Frecuencias semanales completas | Solo fecha de muestra |

**Lo que haría falta para usar UDS como el modelo usa GISAID:**
- 500+ pacientes
- Todos los haplotipos discordantes (los que emergieron y los que no)
- Frecuencias de cada haplotipo dentro del paciente
- Recogida prospectiva

Con esos datos, se podría construir un modelo análogo al de GISAID pero a nivel intrapaciente, que vería las variantes incluso antes de que aparezcan en la vigilancia genómica poblacional.

---

## D — Cómo explicar la teoría de cuasiespecies a la bióloga

"El SARS-CoV-2 no existe como una sola secuencia dentro del paciente. La RNA polimerasa viral tiene una tasa de error de ~10⁻⁴ mutaciones por base por replicación. En un paciente con ~10⁸–10⁹ copias virales activas, eso genera una nube de variantes con todas las mutaciones a 1 paso de Hamming del consenso. Esa nube es la cuasiespecies."

"La presión selectiva del sistema inmune del hospedador actúa sobre esa nube: las variantes que escapan a los anticuerpos y linfocitos T del paciente concreto tienen ventaja selectiva. El UDS detecta cuáles son esas variantes en cada paciente."

"El paralelismo con la evolución poblacional es directo: la misma presión selectiva (anticuerpos, inmunidad preexistente) actúa a escala de millones de pacientes. Las mutaciones que el virus explora dentro del paciente son, probabilísticamente, las mismas que la evolución poblacional acaba seleccionando. Por eso el lead-time es positivo."

---

## E — Qué decir sobre las limitaciones del UDS sin que parezca un fracaso

Framing correcto:

> "Los datos de UDS que tenemos son la punta del iceberg: demuestran que el fenómeno existe y que es biológicamente relevante. El Excel que usamos es como el primer experimento que confirma una hipótesis en condiciones ideales. El siguiente paso —el experimento con poder estadístico real— sería la cohorte prospectiva. El TFM establece exactamente qué habría que hacer y por qué vale la pena hacerlo."

---

## F — Respuestas preparadas para preguntas difíciles

**"¿Por qué el AUC es solo 0,82 y no más alto?"**
> "El problema es inherentemente difícil. Los datos son solo secuencias y frecuencias, sin mediciones experimentales de fitness. Los mejores modelos de la literatura (Maher et al.) usan energía de unión a ACE2 y escape a anticuerpos medidos experimentalmente y alcanzan 0,92–0,97. Con acceso a esos datos mi modelo mejoraría significativamente."

**"¿Confías en los datos de GISAID?"**
> "GISAID tiene un sesgo geográfico documentado: el 78% de secuencias son de países de renta alta. Una variante que emerge primero en África Subsahariana podría ser invisible durante semanas. El modelo captura lo que GISAID captura, no la realidad global completa."

**"¿Por qué JN.1 no aparece en el ranking?"**
> "JN.1 exacto desapareció como clado dominante en septiembre de 2025, reemplazado por sus sublinajes (XFG, LP.8, XDV). Las 5 posiciones XFG en el top-15 SON descendientes de JN.1. El modelo los predice como familia, que es el nivel biológicamente relevante para vigilancia."

**"¿Esto se podría usar en la práctica clínica?"**
> "El sistema está diseñado para vigilancia epidemiológica, no diagnóstico clínico. Su uso natural sería en plataformas como Nextstrain o ECDC para generar semanalmente un ranking de los clados que merecen más atención. También para asistir en la selección de composición vacunal, combinándolo con datos de deep mutational scanning."

---
