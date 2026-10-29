# Defensa oral — Assignment 2 (guion en español)

> Objetivo: poder explicar en 5–10 minutos la pregunta, el diseño que hace justa la comparación, los
> resultados más informativos y las limitaciones, y responder preguntas sobre el código.

## 1. La pregunta (30 s)
- **RQ-A:** ¿cuánto aceleran el *loop reordering* (i-k-j) y el *cache blocking* la multiplicación densa
  float64 secuencial frente a un baseline naive i-j-k validado, y cómo cambia con n?
- **RQ-B:** con las mismas matrices lógicas, ¿a partir de qué densidad deja de compensar CSR + SpGEMM de
  Gustavson frente al mejor kernel denso, y cómo influyen el patrón de no-ceros (uniforme vs banda) y los
  costes de conversión?
- Densidad d = % de no-ceros; sparsity = 1 − d (% de ceros). Lo pide el enunciado literalmente.

## 2. Por qué la comparación es justa (1 min)
- **Mismo lenguaje (C), mismo compilador y flags** (`gcc 13.3 -O2 -std=c11`, sin `-march=native`, sin BLAS)
  para todos los métodos → la única diferencia es el cambio algorítmico/de orden de bucles.
- **Mismas entradas byte a byte:** ficheros generados una vez con semilla fija (PCG64 de NumPy), con SHA-256.
- **Mismo tipo numérico** (float64) y **misma frontera de tiempo** (`kernel`: solo la llamada al kernel; la
  carga y la reserva de C quedan fuera).
- **Secuencial** (1 hilo) en todos los casos.
- **Lock global de la máquina:** el portátil es compartido con los otros assignments; cada configuración se
  ejecuta en exclusiva. Orden de métodos barajado por tamaño (semilla fija). Load average guardado por fila.
- **Parte B:** SpGEMM y denso multiplican las **mismas matrices lógicas** (mismo fichero COO). Las
  conversiones se miden **por separado** y solo se suman donde se dice ("incl. conversions").

## 3. El código, línea a línea

### Baseline `naive_ijk` (`src/c/baseline/matmul_naive.c`)
```c
for i: for j: sum = 0; for k: sum += A[i*n+k] * B[k*n+j]; C[i*n+j] = sum;
```
- A se recorre por filas (stride 1). **B se recorre por columnas: stride de 8n bytes** → para n grande, casi
  cada acceso a B es una línea de caché distinta. Es el cuello de botella.

### Optimización 1 — `reorder_ikj` (`src/c/dense/matmul_dense.c`)
```c
memset(C, 0); for i: for k: a = A[i*n+k]; for j: C[i*n+j] += a * B[k*n+j];
```
- Mismas operaciones, otro orden. El bucle interno es "fila de C += escalar × fila de B": **stride 1 en B y
  C**.
- **No hay SIMD:** comprobado con `gcc -S` y `-fopt-info-vec-all`: a -O2 (modelo de coste *very-cheap* de
  gcc ≥ 12) ninguno de los tres kernels se vectoriza; todos usan `mulsd/addsd` escalares. Por tanto la
  mejora se debe **solo al orden de acceso a memoria**. Si preguntan: "es una ventaja para la comparación,
  aísla el efecto de caché".
- `a` se queda en un registro durante todo el bucle j.

### Optimización 2 — `blocked_ikj(b)`
- Divide i, k, j en bloques de b×b; dentro de cada bloque, el mismo orden i-k-j.
- Idea: el trozo de B (b×b) y de C se reutilizan mientras siguen en caché. Working set ≈ 3·8·b² bytes
  (b=64 → 96 KiB, cabe en L2 de 256 KiB).
- b no tiene por qué dividir n (los bloques del borde son más pequeños; probado en los tests con b=3).
- **Regla de b declarada antes de medir:** se barre b ∈ {16,…,256} a n=1024 y 2048, y se usa el mejor a n=2048.

### CSR (`src/c/sparse/csr.h`)
- `row_ptr[n+1]` (int64): la fila i está en las posiciones `row_ptr[i] … row_ptr[i+1]-1`.
- `col_idx[nnz]` (int32) y `val[nnz]` (double). Memoria = 12·nnz + 8(n+1) bytes.
- Denso ocupa 8n² bytes por matriz → CSR ocupa menos mientras 12·nnz < 8n², es decir **d < 2/3**.

### SpGEMM de Gustavson (`spgemm_gustavson`)
1. **Fase simbólica:** para cada fila i, recorre los a_ik ≠ 0 y las columnas j de la fila k de B; un array
   `marker[j] = i` cuenta cada columna una sola vez → nnz exacto de cada fila de C → se reserva C exacto.
2. **Fase numérica:** acumula `acc[j] += a_ik * b_kj` en un acumulador denso de longitud n (SPA), apunta
   las columnas tocadas la primera vez, y al final de la fila las recoge y pone `acc` a 0.
- Trabajo ∝ flops = Σ_{a_ik≠0} nnz(B_k,:) ≈ d²n³ para entradas uniformes (vs 2n³ del denso).
- Columnas de salida **sin ordenar** (no hace falta para el resultado; lo digo en el report).

### Conversiones
- dense→CSR: dos pasadas (contar no-ceros por fila, luego copiar). Siempre lee las n² posiciones.
- CSR→dense: memset de n² + scatter.

## 4. Validación (30 s)
- Casos exactos: 2×2, 3×3 conocidos, identidad, cero (igualdad exacta). Aleatorios vs NumPy; dispersas vs
  SciPy; filas/columnas vacías; nnz(C) = nnz estructural; contador de flops verificado.
- Tolerancia: cota de Higham para el producto clásico en cualquier orden: |C − C_ref| ≤ 2·n·u·(|A||B|),
  u = 2⁻⁵³. Por qué ×2: el orden de suma de mi kernel y el de NumPy son distintos (cada uno ≤ γ_n).
- **Todos los tests pasan; el error máximo es ~0.30 de la cota.**

## 5. Protocolo (30 s)
- `clock_gettime(CLOCK_MONOTONIC)`; checksum de C impreso (evita que el compilador elimine el cálculo).
- 1 warm-up + k=5 repeticiones en el mismo proceso; n ≥ 3072: 0 warm-up + k=3 (presupuesto).
- Estadístico: **mediana e IQR**; speedup = cociente de medianas con IC 95 % por bootstrap.
- Memoria: **peak RSS** (GNU time) y, por separado, modelo analítico de almacenamiento. Nunca se mezclan.
- Presupuestos: 600 s por proceso (si no → `timeout`), 8 GiB por proceso con `prlimit` (si no → `oom`),
  ≤ 90 min en total.

## 6. Resultados más informativos (todos de `results/raw/`, run del 29/10/2026, 87 min, 125 ok + 1 timeout)
1. **Parte A — speedups crecen con n.** Frente a naive: i-k-j 2,20–8,37×, blocked (b=256) 2,65–12,0×
   (n=3072: 170 s naive vs 14,1 s blocked, IC 95 % [11,9; 12,7]). **Naive no completa n=4096 en 600 s**
   (timeout); i-k-j (46,5 s) y blocked (29,7 s) sí → mayor tamaño factible: naive 3072, optimizados 4096.
   - GFLOP/s: naive cae de 1,68 a 0,34 (exponente 3,97 ≫ 3 → limitado por memoria); i-k-j cae de ~3,7 a
     ~2,9 justo entre n=1024 y 1536 (**B pasa de 8 MiB a 18 MiB y deja de caber en la L3 de 12 MiB**);
     blocked se mantiene en 4,1–4,8.
   - **Matiz honesto:** blocked ya es 1,28× más rápido que i-k-j a n=256, donde b=n → un solo tile, mismo
     orden de iteración. Esa parte NO es caché; los bucles internos solo difieren en aritmética de
     direcciones (conjetura, sin contadores). La parte de caché es la subida a 1,43–1,56× para n ≥ 1536.
   - Block size: no monótono (dispersión 39 % a n=2048); el mejor es b=256, **el borde de la rejilla** →
     el óptimo podría ser mayor (limitación).
2. **Parte B — crossover ≈ 55 % de densidad** (n=2048): SpGEMM gana a denso hasta el 50 % (1,19× uniforme,
   1,21× banda) y pierde desde el 70 % (a 100 %: 0,30×). Mismo resultado en ambos patrones.
   - **Modelo de coste que lo explica:** denso = 0,44 ns por multiply-add × n³; SpGEMM ≈ 1,4 ns por
     multiply-add × d²n³ → d* = √(0,44/1,4) ≈ 55 %. Es decir, el crossover lo fija el **cociente de coste
     por operación**, no el % de ceros. Con un kernel denso vectorizado (BLAS) el crossover bajaría.
   - Memoria: CSR usa menos RSS hasta el 30 %, más desde el 50 % (12 B por entrada en CSR vs 8 B en denso,
     y la salida uniforme es 100 % densa desde d≈5 %: 2·12dn² + 12n² = 24n² en d = 50 %).
3. **Dónde se pierde la ventaja dispersa (H4):**
   - Conversiones: 11–48 ms dense→CSR, 1–6 ms CSR→dense. Irrelevantes cerca del crossover, pero a d=0,1 %
     son el 99 % del tiempo total y bajan la ventaja de 31 937× a 288×.
   - Overheads por fila: 14 ns por multiply-add a d=0,1 % vs ~1,4 ns a densidad alta (inicialización O(n)).
   - **Fill-in y patrón:** mismos flops (ratio 0,96–1,02) pero a d=2 % la salida uniforme tiene 13,7× más
     no-ceros y tarda 4,42× más que la de banda. A n=16384, d=1 %: uniforme 4,71 s y 2,58 GiB; banda
     0,63 s y 145 MiB. → **La densidad sola no determina el rendimiento.**
4. Escalado disperso: a d=0,1 % SpGEMM llega a n=32768 (0,43 s uniforme, 439 MiB), tamaño en el que el
   denso necesitaría 24 GiB (no intentado, fuera del presupuesto de 8 GiB).

## 7. Limitaciones (decirlas antes de que las pregunten)
- Una sola máquina (portátil), governor `powersave` con turbo → frecuencia no fijada.
- Máquina compartida con otros benchmarks (serializados por lock, pero hay trabajo no bloqueado).
- **Sin contadores hardware** (`perf_event_paranoid=4`): los cuellos de botella se infieren de tiempos,
  GFLOP/s, nnz y memoria, no de misses medidos → son explicaciones plausibles, no demostradas.
- Solo dos patrones sintéticos (uniforme y banda); ninguna matriz real (SuiteSparse).
- Strassen y unrolling manual no implementados.
- El kernel bloqueado es un blocking de un solo nivel, sin packing ni micro-kernel de registros (BLAS sería
  mucho más rápido; no es el objetivo).

## 8. Preguntas probables y respuesta corta
- **¿Por qué i-k-j es más rápido si hace las mismas operaciones?** Por el patrón de acceso a memoria
  (stride 1 en lugar de 8n bytes): cada línea de caché de 64 B trae 8 doubles útiles en vez de 1. Las
  operaciones son idénticas (2n³) y ninguno de los dos kernels está vectorizado.
- **¿Cuánto aporta el blocking sobre i-k-j?** 1,2–1,3× a todos los tamaños (no es caché: aparece con un
  solo tile a n=256) y 1,43–1,56× cuando B ya no cabe en L3 (n ≥ 1536). Solo esa subida es atribuible a
  la reutilización en caché.
- **¿Por qué b=256 y no b=64 si 3·8·64² cabe en L2?** Porque lo medí: la regla declarada elige la mediana
  más rápida a n=2048. La predicción "cabe en L2" no se cumplió; el óptimo está en el borde de la rejilla.
- **¿Qué es el "crossover"?** La densidad a partir de la cual el denso es más rápido que SpGEMM (≈55 % aquí).
  Lo fija el cociente de coste por operación de los dos kernels; el patrón cambia mucho el coste a densidad
  baja/media (fill-in, localidad) aunque aquí ambos cruzan en el mismo intervalo 50–70 %.
- **¿Por qué el naive no llega a 4096?** El presupuesto es 600 s por proceso; a n=3072 ya tardaba 170 s y
  extrapolando con el exponente 3,97 serían ≈530 s **por repetición** en 4096; el proceso (k=3, sin
  warm-up) no terminó en 600 s y se registró como `timeout` sin tiempo. No se reporta ningún tiempo
  parcial (sería inventar/mezclar fronteras).
- **¿La variabilidad?** IQR relativo mediano 0,66 % (denso). Pero entre procesos el mismo kernel a n=2048
  varió hasta un 15 % (3,59–4,13 s) → lo declaro como limitación: el IQR intra-proceso subestima la
  variación entre sesiones.
- **¿Por qué C se vuelve más densa?** Para entradas uniformes, P(C_ij ≠ 0) ≈ 1 − (1 − d²)ⁿ; con n=2048 y
  d=5 % ya casi todo C es no nulo.
- **¿Qué incluye el tiempo de SpGEMM?** Fase simbólica + reserva de C + fase numérica; las entradas ya están
  en CSR. Las conversiones aparte.
- **¿Cómo reproduzco un experimento?** `make test` y, por ejemplo:
  `build/bench_dense --method reorder_ikj --n 1024 --a data/inputs/dense_n1024_s42.f64 --b data/inputs/dense_n1024_s43.f64 --warmup 1 --reps 5`
