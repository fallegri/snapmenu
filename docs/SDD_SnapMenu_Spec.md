# Documento de Especificaciones de Diseño de Software (SDD)
## **MenuAI — Sistema Inteligente de Sugerencia de Menú por Reconocimiento Visual de Ingredientes**

---

| Campo | Detalle |
|-------|---------|
| **Versión** | 1.1.0 |
| **Fecha** | 2026-07-22 |
| **Estado** | Borrador — Alcance Ampliado |
| **Clasificación** | Confidencial — Uso Interno |
| **Estándares** | IEEE 1016 (SDD), ISO/IEC/IEEE 42010:2022, SOLID, OWASP, WCAG 2.1 |
| **Autor** | Equipo de Desarrollo MenuAI |

---

## Tabla de Contenidos

1. [Introducción](#1-introducción)
2. [Alcance](#2-alcance)
3. [Referencias Normativas](#3-referencias-normativas)
4. [Definiciones y Acrónimos](#4-definiciones-y-acrónimos)
5. [Descripción Arquitectónica (ISO 42010)](#5-descripción-arquitectónica-iso-42010)
6. [Requisitos Funcionales](#6-requisitos-funcionales)
7. [Requisitos No Funcionales](#7-requisitos-no-funcionales)
8. [Diseño del Modelo ML y Pipeline de Datos](#8-diseño-del-modelo-ml-y-pipeline-de-datos)
9. [Principios SOLID Aplicados](#9-principios-solid-aplicados)
10. [Diseño UX/UI](#10-diseño-uxui)
11. [Seguridad, Privacidad y Consideraciones OSINT](#11-seguridad-privacidad-y-consideraciones-osint)
12. [Buenas Prácticas de Desarrollo](#12-buenas-prácticas-de-desarrollo)
13. [Apéndices](#13-apéndices)

---


## 1. Introducción

### 1.1 Propósito

Este documento define las especificaciones de diseño de software para **MenuAI**, una aplicación móvil que utiliza visión por computadora y aprendizaje automático para identificar ingredientes alimentarios a través de la cámara del dispositivo y, con base en ellos, sugerir menús personalizados considerando restricciones dietéticas, alergias, intolerancias y contraindicaciones del usuario.

### 1.2 Audiencia Objetivo

| Stakeholder | Interés Principal |
|-------------|-------------------|
| Desarrolladores | Implementación técnica, arquitectura de código |
| Data Scientists / ML Engineers | Pipeline de datos, entrenamiento y despliegue del modelo |
| Diseñadores UX/UI | Flujos de interacción, accesibilidad |
| Product Owners | Alcance funcional, roadmap |
| QA Engineers | Criterios de aceptación, testing |
| Security Engineers | Superficie de ataque, privacidad de datos |

### 1.3 Visión del Producto

> *"Transformar los ingredientes disponibles en inspiración culinaria personalizada, accesible con solo apuntar la cámara."*

El sistema resuelve el problema cotidiano de "¿qué cocino con lo que tengo?" eliminando la fricción de buscar recetas manualmente y garantizando que las sugerencias respeten las condiciones de salud del usuario.

---


## 2. Alcance

### 2.1 Dentro del Alcance (In-Scope)

| # | Funcionalidad | Descripción Detallada | Prioridad | Release |
|---|---------------|----------------------|-----------|---------|
| 1 | Captura de imagen en tiempo real mediante cámara del dispositivo | Stream de video en vivo con preview, soporte para cámara frontal/trasera, flash, autofocus. Captura continua de frames para detección sin necesidad de foto explícita. | **P0 — Crítica** | v1.0 |
| 2 | Detección y clasificación de ingredientes usando modelo CNN entrenado | Modelo YOLOv8n customizado ejecutándose on-device. Detección multi-objeto simultánea (≥5 ingredientes). Bounding boxes con labels y score de confianza en overlay sobre el preview. | **P0 — Crítica** | v1.0 |
| 3 | Confirmación y edición manual de ingredientes | El usuario puede confirmar, eliminar o agregar ingredientes manualmente post-detección. Modo acumulativo para múltiples escaneos. Búsqueda por texto con autocompletado. | **P0 — Crítica** | v1.0 |
| 4 | Cuestionario inteligente de restricciones de salud | Wizard progresivo (máx. 5 pantallas) para capturar: alergias, intolerancias, contraindicaciones médicas y preferencias dietéticas. Contextual (se activa solo cuando es relevante). | **P0 — Crítica** | v1.0 |
| 5 | Motor de sugerencia de menú personalizado | Algoritmo de matching: ingredientes detectados ∩ catálogo de recetas — restricciones del perfil. Scoring por relevancia, dificultad y preferencias. Mínimo 3 sugerencias por sesión. | **P0 — Crítica** | v1.0 |
| 6 | Persistencia cifrada del perfil dietético | Almacenamiento local con AES-256-GCM. Sincronización opt-in a cloud. Incluye alergias, intolerancias, condiciones médicas, preferencias de cocina y nivel de dificultad. | **P0 — Crítica** | v1.0 |
| 7 | Detalle de receta completa | Vista detallada con: ingredientes con cantidades, pasos de preparación, tiempo estimado, info nutricional básica, señalización de alérgenos presentes. | **P1 — Alta** | v1.0 |
| 8 | Historial de sesiones y menús sugeridos | Registro cronológico de escaneos: ingredientes detectados, menú seleccionado, fecha/hora. Búsqueda y filtro por ingrediente/fecha. | **P1 — Alta** | v1.0 |
| 9 | Sistema de favoritos | Guardar recetas favoritas con organización por tags/categorías propias del usuario. Acceso rápido desde navegación principal. | **P1 — Alta** | v1.0 |
| 10 | Modo offline completo para core features | Detección de ingredientes + sugerencia de menú básica sin conexión a internet. Cache local de recetas más comunes. Sincronización delta cuando hay conexión. | **P0 — Crítica** | v1.0 |
| 11 | Soporte multi-idioma | Español (LATAM) + Inglés en v1. Arquitectura preparada para extensión a otros idiomas. Todos los strings externalizados. | **P1 — Alta** | v1.0 |
| 12 | Onboarding interactivo | Tutorial de 3 pantallas (máx. 60s) explicando la propuesta de valor. Opcional y omitible. | **P2 — Media** | v1.0 |
| 13 | Actualización OTA del modelo ML | Descarga en background de nuevas versiones del modelo. Rollback automático si crash rate > 1%. | **P1 — Alta** | v1.1 |
| 14 | Preguntas contextuales proactivas | Si se detecta un ingrediente potencialmente alérgeno y el perfil está incompleto, se pregunta contextualmente (máx. 1 por sesión). | **P2 — Media** | v1.1 |
| 15 | Aprendizaje de preferencias | El sistema mejora sugerencias con el tiempo basándose en aceptaciones/rechazos del usuario. Feedback loop implícito. | **P2 — Media** | v1.1 |

#### 2.1.1 Mapa de Features por Módulo

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FEATURES MAP — SnapMenu v1.0                        │
│                                                                        │
│  ┌─────────────────────────────────┐  ┌────────────────────────────┐  │
│  │   MÓDULO: DETECCIÓN VISUAL      │  │  MÓDULO: PERFIL DE SALUD   │  │
│  │                                 │  │                            │  │
│  │  • Stream cámara en vivo        │  │  • Wizard de alergias      │  │
│  │  • Detección multi-ingrediente  │  │  • Wizard de intolerancias │  │
│  │  • Bounding boxes + labels      │  │  • Contraindicaciones      │  │
│  │  • Edición manual de lista      │  │  • Preferencias dietéticas │  │
│  │  • Modo acumulativo             │  │  • Cifrado AES-256         │  │
│  │  • Feedback visual (confianza)  │  │  • Preguntas contextual.   │  │
│  │                                 │  │  • CRUD completo           │  │
│  └─────────────────────────────────┘  └────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────┐  ┌────────────────────────────┐  │
│  │   MÓDULO: MOTOR DE MENÚ        │  │  MÓDULO: HISTORIAL/FAV     │  │
│  │                                 │  │                            │  │
│  │  • Matching ingredientes-recetas│  │  • Lista cronológica       │  │
│  │  • Filtrado por restricciones   │  │  • Búsqueda y filtros      │  │
│  │  • Scoring y ranking            │  │  • Favoritos con tags      │  │
│  │  • Mín. 3 sugerencias          │  │  • Tracking aceptar/rech.  │  │
│  │  • Detalle de receta            │  │  • Aprendizaje implícito   │  │
│  │  • Info nutricional             │  │  • Export de datos         │  │
│  │  • Alternativas si descarta     │  │                            │  │
│  └─────────────────────────────────┘  └────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   MÓDULO: TRANSVERSAL (Cross-Cutting)                            │  │
│  │                                                                  │  │
│  │  • Offline-first  • i18n (ES/EN)  • Onboarding  • OTA Model    │  │
│  │  • Analytics      • Logging       • Auth         • Dark Mode    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

#### 2.1.2 Flujo de Valor Principal (Value Stream)

```
┌────────────────────── USER VALUE STREAM ──────────────────────────────┐
│                                                                        │
│  [PROBLEMA]          [ACCIÓN]           [RESULTADO]     [VALOR]       │
│                                                                        │
│  "¿Qué cocino       Apuntar cámara     Ingredientes    Inspiración   │
│   con lo que        a los ingredientes   detectados      instantánea  │
│   tengo?"                                                              │
│       │                   │                   │              │         │
│       ▼                   ▼                   ▼              ▼         │
│  "¿Es seguro         Sistema verifica    Restricciones    Seguridad   │
│   para mí?"          perfil de salud     aplicadas        alimentaria │
│       │                   │                   │              │         │
│       ▼                   ▼                   ▼              ▼         │
│  "No sé qué          Motor sugiere       3+ opciones     Decisión    │
│   preparar"          menú personalizado   rankeadas       sin esfuerzo│
│       │                   │                   │              │         │
│       ▼                   ▼                   ▼              ▼         │
│  "Quiero algo        Detalle paso a paso  Receta con      Confianza   │
│   que pueda           con info completa   tiempos, info   para cocinar│
│   hacer"                                  nutricional                  │
│                                                                        │
│  TIEMPO TOTAL: < 3 minutos desde escaneo hasta receta seleccionada   │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Fuera del Alcance (Out-of-Scope) — v1.0

| # | Funcionalidad Excluida | Justificación | Roadmap Potencial |
|---|------------------------|---------------|-------------------|
| 1 | Compra automática de ingredientes faltantes | Complejidad de integración con marketplaces locales; requiere partnerships | v2.0+ (integración con apps de delivery) |
| 2 | Integración con dispositivos IoT de cocina | Fragmentación de protocolos; nicho reducido de usuarios con IoT | v3.0+ (si hay demanda validada) |
| 3 | Generación de contenido de video/recetas paso a paso | Alto costo de producción de contenido; requiere equipo de content | v2.0+ (UGC o partnerships con chefs) |
| 4 | Funcionalidad social (compartir menús, seguir usuarios) | Complejidad de moderación y comunidad; distrae del core value | v2.0+ (si métricas de retención lo justifican) |
| 5 | Integración con expedientes médicos electrónicos (EHR/HCE) | Regulación compleja (HIPAA/normativas locales); certificaciones requeridas | Evaluación post-v2.0 |
| 6 | Planificación semanal de menú automática | Requiere motor más sofisticado (variedad, nutrición semanal) | v1.2 — extensión natural del motor |
| 7 | Lista de compras generada automáticamente | Depende de base de datos de ingredientes con cantidades exactas | v1.1 — feature complementaria |
| 8 | Detección de ingredientes por voz/texto libre NLP | Scope adicional de NLP; la cámara es el diferenciador | v2.0+ (input multimodal) |
| 9 | Soporte para restricciones religiosas avanzadas (Halal, Kosher certificado) | Requiere certificaciones y validación con autoridades religiosas | v1.2 (como preferencias básicas en v1.0) |
| 10 | Cálculo nutricional preciso por porción | Requiere base de datos nutricional certificada; responsabilidad legal | v1.1 (info nutricional indicativa en v1.0) |

#### 2.2.1 Criterios para Inclusión Futura

Un feature se evalúa para inclusión en releases futuros según:

```
┌──────────────── FRAMEWORK DE PRIORIZACIÓN (RICE) ─────────────────┐
│                                                                    │
│  SCORE = (Reach × Impact × Confidence) / Effort                   │
│                                                                    │
│  Reach:      ¿A cuántos usuarios impacta? (usuarios/quarter)     │
│  Impact:     ¿Cuánto mejora la experiencia? (0.25 / 0.5 / 1 / 2 / 3) │
│  Confidence: ¿Cuán seguros estamos de los estimados? (0-100%)    │
│  Effort:     ¿Cuántas persona-semanas requiere? (person-weeks)   │
│                                                                    │
│  Umbral de inclusión: RICE score > 5.0 para consideración         │
│  Validación adicional: entrevistas con ≥ 5 usuarios potenciales   │
└────────────────────────────────────────────────────────────────────┘
```

### 2.3 Supuestos y Restricciones

#### 2.3.1 Supuestos del Proyecto

| ID | Supuesto | Riesgo si es Falso | Plan de Mitigación |
|----|----------|--------------------|--------------------|
| SUP-01 | El usuario cuenta con un dispositivo con cámara de al menos 5MP | Detecciones de baja calidad; falsos negativos altos | Guía de "cámara mínima recomendada"; preprocessing más agresivo; modo galería como fallback |
| SUP-02 | Existe conectividad para sincronización, pero la inferencia funciona offline | Si no hay nunca conectividad, no hay nuevas recetas ni model updates | Cache amplio de recetas (~500) pre-instalado; modelo base incluido en APK |
| SUP-03 | El dataset de entrenamiento cubre las categorías iniciales (palta, pollo, papas, cerdo, etc.) | Modelo con baja precisión en v1 | Transfer learning desde COCO dataset; active learning post-launch para expandir |
| SUP-04 | Los usuarios están dispuestos a compartir datos de salud (opt-in) | Baja adopción del perfil → sugerencias genéricas | El sistema funciona SIN perfil (sugerencias no filtradas); el perfil mejora pero no bloquea |
| SUP-05 | El mercado objetivo tiene acceso a smartphones con ≥ 3GB RAM | Modelo no corre en devices low-end | Versión "lite" del modelo (~3MB) con menos precisión pero funcional para 2GB RAM |
| SUP-06 | Existe un catálogo de recetas suficiente (≥500) para arrancar | Sugerencias repetitivas; baja retención | Partnership con APIs de recetas existentes (Spoonacular, Edamam); contenido curado manualmente |
| SUP-07 | Los usuarios entienden el concepto de "apuntar la cámara" sin mucha explicación | Fricción en onboarding; abandono | Onboarding visual; animación guiada; tooltip en primer uso |

#### 2.3.2 Restricciones del Proyecto

| ID | Tipo | Restricción | Impacto en Diseño |
|----|------|-------------|-------------------|
| RES-01 | **Técnica** | El modelo ML debe ejecutarse on-device (edge inference) con latencia < 2s | Limita complejidad del modelo; requiere quantización; excluye modelos >100MB |
| RES-02 | **Legal/Regulatoria** | Cumplimiento con GDPR (EU), LGPD (Brasil) y ley de protección de datos peruana para datos de salud | Consentimiento explícito; data minimization; derecho al olvido; cifrado obligatorio |
| RES-03 | **Técnica** | Tamaño total de la app (con modelo incluido) ≤ 150MB | Modelo quantizado (INT8); assets comprimidos; lazy loading de recursos no críticos |
| RES-04 | **Técnica** | Soporte mínimo: Android 8.0+ (API 26) / iOS 14+ | Limita uso de APIs más recientes; requiere compatibility testing en devices antiguos |
| RES-05 | **Ética/Legal** | La app NO puede dar consejo médico ni nutricional profesional | Disclaimers obligatorios; lenguaje indicativo ("sugerencia") no prescriptivo; no calcular dietas |
| RES-06 | **Negocio** | Time-to-market: MVP funcional en ≤ 4 meses desde inicio de desarrollo | Scope reducido para v1.0; priorización estricta; features no P0 van a backlog |
| RES-07 | **Técnica** | Las imágenes capturadas por la cámara NUNCA deben persistir ni transmitirse | Procesamiento in-memory exclusivamente; no cache de frames; no analytics con imágenes |
| RES-08 | **Técnica** | Consumo de batería durante escaneo activo (5 min) ≤ 5% | Throttling de FPS en inferencia (5-10 FPS, no 30); GPU delegate si disponible; early stop |
| RES-09 | **Operativa** | Equipo de desarrollo reducido (3-5 personas) | Clean Architecture para paralelizar features; CI/CD desde día 1; priorización agresiva |
| RES-10 | **Datos** | No usar datos de usuarios para reentrenamiento sin consentimiento explícito | Opt-in claro y separado para contribuir datos; anonimización obligatoria si se acepta |

#### 2.3.3 Dependencias Externas

| ID | Dependencia | Proveedor | Riesgo | Contingencia |
|----|-------------|-----------|--------|--------------|
| DEP-01 | API de Cámara del SO | Google (Android) / Apple (iOS) | Cambios breaking en APIs | Abstracción via plugin; pinning de versiones; adapter pattern |
| DEP-02 | TensorFlow Lite Runtime | Google | Deprecación o cambio de API | Migración a ONNX Runtime como alternativa viable (ADR-001) |
| DEP-03 | Catálogo de recetas | API externa (Spoonacular/Edamam) + DB propia | API caída; rate limits; costos | Cache local robusto; fallback a recetas pre-cargadas; múltiples fuentes |
| DEP-04 | Firebase / Cloud Services | Google Cloud | Outage; cambios de pricing | Abstracción del backend; posibilidad de migrar a AWS/Azure |
| DEP-05 | Flutter Framework | Google | Breaking changes entre major versions | Pinning de versión; migración planificada por major version |
| DEP-06 | Dataset de entrenamiento | Equipo interno + fuentes abiertas | Insuficiente cantidad o calidad | Augmentation agresiva; Active Learning; crowdsourcing opt-in post-launch |

### 2.4 Usuarios Objetivo (Target Audience)

#### 2.4.1 Personas

| Persona | Perfil | Motivación Principal | Pain Point |
|---------|--------|---------------------|------------|
| **Ana, 28** | Profesional joven, cocina ocasional, alergia al gluten | Quiere ideas rápidas con lo que compró | No sabe qué preparar; pierde tiempo buscando recetas "gluten-free" |
| **Carlos, 42** | Padre de familia, cocina diaria, hipertensión leve | Necesita variar menú familiar respetando restricciones | Siempre hace lo mismo; no recuerda qué ingredientes debe evitar |
| **María, 65** | Jubilada, le gusta cocinar, diabetes tipo 2 | Quiere explorar recetas nuevas que pueda comer | Las recetas online no consideran su condición; tiene miedo de cocinar "mal" |
| **Diego, 22** | Estudiante universitario, bajo presupuesto, vegetariano | Aprovechar al máximo los pocos ingredientes que tiene | No tiene tiempo ni experiencia; quiere algo fácil y rápido |

#### 2.4.2 Escenarios de Uso Principales

```
┌─────────────────── ESCENARIOS DE USO ─────────────────────────────────┐
│                                                                        │
│  ESCENARIO 1: "Cocina del día a día"                                  │
│  ─────────────────────────────────────                                 │
│  Actor: Ana (profesional, alergia al gluten)                          │
│  Contexto: Llega a casa del trabajo, abre la nevera                   │
│  Acción: Escanea pollo, pimiento, arroz                               │
│  Resultado: 3 opciones sin gluten en < 1 minuto                      │
│  Frecuencia: 3-5 veces por semana                                     │
│                                                                        │
│  ESCENARIO 2: "Planificación con restricciones"                       │
│  ─────────────────────────────────────                                 │
│  Actor: Carlos (padre, hipertensión)                                   │
│  Contexto: Quiere cocinar algo diferente para la familia              │
│  Acción: Escanea ingredientes del mercado; sistema filtra por sodio   │
│  Resultado: Menú familiar bajo en sal con ingredientes frescos        │
│  Frecuencia: 2-3 veces por semana                                     │
│                                                                        │
│  ESCENARIO 3: "Exploración segura"                                    │
│  ─────────────────────────────────────                                 │
│  Actor: María (diabetes tipo 2)                                        │
│  Contexto: Quiere probar algo nuevo pero tiene miedo                  │
│  Acción: Escanea verduras y pollo; sistema excluye alto IG            │
│  Resultado: Recetas con info nutricional + badge "apta para diabetes" │
│  Frecuencia: 1-2 veces por semana                                     │
│                                                                        │
│  ESCENARIO 4: "Máximo rendimiento con poco"                           │
│  ─────────────────────────────────────                                 │
│  Actor: Diego (estudiante, vegetariano, bajo presupuesto)             │
│  Contexto: Solo tiene papas, huevos y tomate                          │
│  Acción: Escanea los 3 ingredientes; pide "fácil y rápido"           │
│  Resultado: Tortilla española, papa rellena, etc. (todo < 30 min)    │
│  Frecuencia: 4-6 veces por semana                                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.5 Contexto de Negocio

#### 2.5.1 Propuesta de Valor Única (UVP)

| Diferenciador | SnapMenu | Competidores (Yummly, SuperCook, etc.) |
|---------------|----------|----------------------------------------|
| **Input visual (cámara)** | Detección automática por IA | Input manual de ingredientes |
| **Seguridad alimentaria** | Perfil de salud integrado; exclusión automática | Filtros básicos opcionales |
| **Inferencia offline** | Funciona sin internet | Requieren conexión |
| **Privacidad** | Imágenes nunca salen del dispositivo | Cloud processing |
| **Contextualidad** | Preguntas inteligentes cuando detecta riesgo | Sin alertas proactivas |
| **Personalización** | Aprende de preferencias implícitas | Recomendaciones genéricas |

#### 2.5.2 Modelo de Monetización (Consideraciones para v2+)

| Modelo | Descripción | Viabilidad |
|--------|-------------|------------|
| **Freemium** | Core gratis; premium = más recetas, planificación semanal, analytics nutricional | Alta — bajo costo de adquisición |
| **Partnership B2B** | Integración con supermercados/delivery para sugerir compras | Media — requiere partnerships |
| **White-label** | Licencia a nutricionistas/clínicas para uso con pacientes | Media-alta — canal profesional |
| **Afiliados** | Comisión por compras de ingredientes sugeridos vía delivery apps | Baja en v1 — requiere volumen |

> **Nota:** El modelo de monetización NO afecta el alcance de v1.0. Se documenta como contexto para decisiones arquitectónicas que deben soportar extensibilidad futura.

### 2.6 Roadmap de Alto Nivel

```
┌────────────────────── ROADMAP — SnapMenu ─────────────────────────────┐
│                                                                        │
│  Q3 2026 ──────── Q4 2026 ──────── Q1 2027 ──────── Q2 2027          │
│                                                                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │
│  │  v1.0    │    │  v1.1    │    │  v1.2    │    │  v2.0    │        │
│  │  MVP     │    │  Polish  │    │  Expand  │    │  Social  │        │
│  ├──────────┤    ├──────────┤    ├──────────┤    ├──────────┤        │
│  │• Detección│   │• OTA model│   │• +100 ingr│   │• Compartir│       │
│  │• Perfil   │   │• Lista de │   │• Planific.│   │• Community│       │
│  │• Motor    │   │  compras  │   │  semanal  │   │• Video    │       │
│  │• Historial│   │• Learning │   │• Halal/   │   │  recetas  │       │
│  │• Offline  │   │  from user│   │  Kosher   │   │• IoT      │       │
│  │• i18n     │   │• +Idiomas │   │• Nutri    │   │• B2B      │       │
│  │           │   │• Analytics│   │  detallada│   │           │       │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘        │
│                                                                        │
│  MÉTRICAS CLAVE POR RELEASE:                                          │
│  v1.0: 1K descargas, DAU > 20%, crash-free > 99%                    │
│  v1.1: 5K descargas, retención D7 > 40%, NPS > 7                    │
│  v1.2: 15K descargas, retención D30 > 25%                           │
│  v2.0: 50K descargas, revenue positivo                               │
└────────────────────────────────────────────────────────────────────────┘
```

---


## 3. Referencias Normativas

| Estándar / Referencia | Aplicación |
|-----------------------|------------|
| **IEEE 1016-2009** | Estructura base del documento SDD |
| **ISO/IEC/IEEE 42010:2022** | Marco de descripción arquitectónica |
| **ISO 25010:2011** | Modelo de calidad de producto software |
| **OWASP Mobile Top 10** | Seguridad en aplicaciones móviles |
| **OWASP ML Top 10** | Seguridad en sistemas de Machine Learning |
| **WCAG 2.1 (AA)** | Accesibilidad de interfaz |
| **GDPR / LGPD** | Protección de datos personales y de salud |
| **SOLID Principles (Robert C. Martin)** | Principios de diseño orientado a objetos |
| **Material Design 3 / Human Interface Guidelines** | Guías de diseño de interfaces |
| **OSINT Framework** | Evaluación de exposición de datos |

---

## 4. Definiciones y Acrónimos

| Término | Definición |
|---------|------------|
| **CNN** | Convolutional Neural Network — Red neuronal convolucional |
| **SDD** | Software Design Description |
| **ML** | Machine Learning — Aprendizaje Automático |
| **OSINT** | Open Source Intelligence — Inteligencia de fuentes abiertas |
| **Edge Inference** | Ejecución del modelo directamente en el dispositivo del usuario |
| **IoU** | Intersection over Union — métrica de detección de objetos |
| **mAP** | Mean Average Precision — precisión promedio del modelo |
| **TFLite** | TensorFlow Lite — framework para modelos en dispositivos móviles |
| **ONNX** | Open Neural Network Exchange — formato interoperable de modelos |
| **Alérgeno** | Sustancia que puede causar una reacción alérgica |
| **Intolerancia** | Incapacidad del organismo para digerir/procesar un alimento |
| **Contraindicación** | Condición que hace inadecuado un alimento para el usuario |

---


## 5. Descripción Arquitectónica (ISO 42010)

> Esta sección sigue el marco de descripción arquitectónica definido en **ISO/IEC/IEEE 42010:2022**, documentando el sistema a través de stakeholders, concerns, viewpoints, vistas y decisiones arquitectónicas.

### 5.1 Contexto del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTORNO EXTERNO                           │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │ Usuario  │    │   Cámara     │    │  Base de Recetas      │  │
│  │ (Actor)  │    │ (Dispositivo)│    │  (API/Local DB)       │  │
│  └────┬─────┘    └──────┬───────┘    └───────────┬───────────┘  │
│       │                  │                        │              │
│       ▼                  ▼                        ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    MenuAI Application                      │   │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌───────────┐  │   │
│  │  │   UI    │  │  ML      │  │ Perfil  │  │  Motor de │  │   │
│  │  │  Layer  │  │  Engine  │  │ Salud   │  │  Menú     │  │   │
│  │  └─────────┘  └──────────┘  └─────────┘  └───────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Stakeholders y Concerns (Partes Interesadas y Preocupaciones)

| ID | Stakeholder | Concerns (Preocupaciones) |
|----|-------------|---------------------------|
| STK-01 | **Usuario Final** | Precisión en detección de ingredientes, rapidez de respuesta, menús relevantes y seguros, privacidad de datos de salud |
| STK-02 | **Product Owner** | Time-to-market, escalabilidad del catálogo, retención de usuarios, diferenciación competitiva |
| STK-03 | **Desarrollador Mobile** | Mantenibilidad del código, rendimiento en dispositivo, testabilidad, claridad de APIs internas |
| STK-04 | **ML Engineer** | Calidad del dataset, métricas del modelo (mAP > 85%), pipeline reproducible, monitoreo de drift |
| STK-05 | **Diseñador UX** | Flujos intuitivos, accesibilidad (WCAG 2.1 AA), coherencia visual, feedback inmediato |
| STK-06 | **Security Engineer** | Protección de datos de salud, superficie de ataque minimizada, cumplimiento GDPR |
| STK-07 | **Nutricionista (Dominio)** | Precisión de restricciones alimentarias, seguridad en recomendaciones, responsabilidad legal |
| STK-08 | **DevOps / SRE** | Despliegue del modelo, monitoreo, CI/CD, rollback de versiones |



### 5.3 Viewpoints (Puntos de Vista Arquitectónicos)

#### 5.3.1 Viewpoint Lógico (Logical Viewpoint)

**Propósito:** Describir la descomposición funcional del sistema en módulos lógicos.

**Concerns atendidos:** Mantenibilidad, separación de responsabilidades, testabilidad.

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                       │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  Camera    │  │  Health    │  │  Menu Suggestion     │  │
│  │  Screen    │  │  Profile   │  │  Screen              │  │
│  │  Module    │  │  Wizard    │  │  Module              │  │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬───────────┘  │
├─────────┼───────────────┼────────────────────┼──────────────┤
│         ▼               ▼                    ▼              │
│                    CAPA DE DOMINIO                            │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │ Ingredient │  │  User      │  │  Menu                │  │
│  │ Recognition│  │  Health    │  │  Generation          │  │
│  │ Service    │  │  Service   │  │  Service             │  │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬───────────┘  │
├─────────┼───────────────┼────────────────────┼──────────────┤
│         ▼               ▼                    ▼              │
│                    CAPA DE DATOS                              │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  ML Model  │  │  Local DB  │  │  Recipe              │  │
│  │  Repository│  │  (SQLite/  │  │  Repository          │  │
│  │            │  │   Room)    │  │  (API + Cache)       │  │
│  └────────────┘  └────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 5.3.2 Viewpoint de Proceso (Process Viewpoint)

**Propósito:** Describir los flujos dinámicos y concurrencia del sistema.

**Concerns atendidos:** Rendimiento, latencia, experiencia de usuario en tiempo real.

```
┌─────────────────── FLUJO PRINCIPAL ───────────────────────────┐
│                                                                │
│  [1] Usuario apunta cámara → Stream de frames                 │
│       │                                                        │
│       ▼                                                        │
│  [2] Pre-procesamiento de imagen (resize, normalize)           │
│       │                                                        │
│       ▼                                                        │
│  [3] Inferencia ML (TFLite/ONNX Runtime) ← Hilo separado     │
│       │                                                        │
│       ▼                                                        │
│  [4] Post-procesamiento (NMS, threshold filtering)             │
│       │                                                        │
│       ▼                                                        │
│  [5] Ingredientes detectados → UI feedback visual              │
│       │                                                        │
│       ▼                                                        │
│  [6] Usuario confirma ingredientes                             │
│       │                                                        │
│       ▼                                                        │
│  [7] Sistema verifica perfil de salud del usuario              │
│       │                                                        │
│       ├─── ¿Perfil completo? ─── SÍ ──→ [9]                  │
│       │                                                        │
│       └─── NO ──→ [8] Wizard de preguntas de salud            │
│                         • Alergias conocidas                   │
│                         • Intolerancias (lactosa, gluten...)   │
│                         • Contraindicaciones médicas            │
│                         • Preferencias dietéticas               │
│                              │                                 │
│                              ▼                                 │
│  [9] Motor de Menú: Ingredientes ∩ Recetas - Restricciones    │
│       │                                                        │
│       ▼                                                        │
│  [10] Presentación de menú sugerido con alternativas           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```



#### 5.3.3 Viewpoint de Despliegue (Deployment Viewpoint)

**Propósito:** Describir cómo se distribuyen los componentes en la infraestructura.

**Concerns atendidos:** Disponibilidad, escalabilidad, costos operativos.

```
┌──────────────────────────────────────────────────────────────────┐
│                      DISPOSITIVO MÓVIL                             │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  App MenuAI  │  │  Modelo ML   │  │  Base de Datos Local   │  │
│  │  (Flutter/   │  │  (TFLite/    │  │  (SQLite + Hive)       │  │
│  │   React      │  │   ONNX)      │  │  - Perfil usuario      │  │
│  │   Native)    │  │  ~50-100MB   │  │  - Cache recetas       │  │
│  └──────┬───────┘  └──────────────┘  │  - Historial           │  │
│         │                             └────────────────────────┘  │
└─────────┼────────────────────────────────────────────────────────┘
          │ HTTPS/gRPC
          ▼
┌──────────────────────────────────────────────────────────────────┐
│                         CLOUD BACKEND                              │
│                                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  API Gateway    │  │  Recipe Service  │  │  Model Registry │  │
│  │  (Kong/AWS      │  │  (Microservicio) │  │  (MLflow /      │  │
│  │   API GW)       │  │                  │  │   Vertex AI)    │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                     │                     │           │
│           ▼                     ▼                     ▼           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Auth Service   │  │  PostgreSQL /   │  │  Object Storage │  │
│  │  (Firebase /    │  │  MongoDB        │  │  (S3 / GCS)     │  │
│  │   Cognito)      │  │  (Recetas DB)   │  │  (Modelos)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              ML Training Pipeline (Offline)                   │  │
│  │  Dataset → Preprocessing → Training → Evaluation → Export    │  │
│  │  (Kubeflow / Vertex AI Pipelines / SageMaker)                │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.3.4 Viewpoint de Información (Data Viewpoint)

**Propósito:** Describir las entidades de datos, sus relaciones y flujo.

```
┌─────────────────── MODELO DE DATOS PRINCIPAL ─────────────────┐
│                                                                │
│  ┌──────────────┐       ┌──────────────────┐                 │
│  │    User      │ 1───N │  HealthProfile   │                 │
│  ├──────────────┤       ├──────────────────┤                 │
│  │ id           │       │ id               │                 │
│  │ name         │       │ user_id (FK)     │                 │
│  │ email        │       │ allergies[]      │                 │
│  │ created_at   │       │ intolerances[]   │                 │
│  └──────┬───────┘       │ contraindications│                 │
│         │               │ diet_preference  │                 │
│         │               │ updated_at       │                 │
│         │               └──────────────────┘                 │
│         │                                                     │
│         │ 1───N                                               │
│         ▼                                                     │
│  ┌──────────────┐       ┌──────────────────┐                 │
│  │  MenuSession │ N───N │   Ingredient     │                 │
│  ├──────────────┤       ├──────────────────┤                 │
│  │ id           │       │ id               │                 │
│  │ user_id (FK) │       │ name             │                 │
│  │ detected_    │       │ category         │                 │
│  │   ingredients│       │ common_allergens │                 │
│  │ suggested_   │       │ nutritional_info │                 │
│  │   menu_id    │       │ ml_class_id      │                 │
│  │ created_at   │       └──────────────────┘                 │
│  └──────────────┘                                             │
│                                                                │
│  ┌──────────────┐       ┌──────────────────┐                 │
│  │    Recipe    │ N───N │   Ingredient     │                 │
│  ├──────────────┤       ├──────────────────┤                 │
│  │ id           │       │ (via join table  │                 │
│  │ name         │       │  recipe_ingredient)               │
│  │ description  │       └──────────────────┘                 │
│  │ prep_time    │                                             │
│  │ difficulty   │                                             │
│  │ cuisine_type │                                             │
│  │ allergen_tags│                                             │
│  │ instructions │                                             │
│  └──────────────┘                                             │
└────────────────────────────────────────────────────────────────┘
```



### 5.4 Decisiones Arquitectónicas (Architecture Decision Records — ADR)

#### ADR-001: Inferencia en Dispositivo (Edge) vs. Cloud

| Aspecto | Decisión |
|---------|----------|
| **Contexto** | La detección de ingredientes requiere procesamiento de imágenes en tiempo real |
| **Decisión** | Inferencia en dispositivo (on-device) usando TFLite/ONNX Runtime |
| **Justificación** | Latencia < 2s requerida; funcionamiento offline; privacidad (imágenes no salen del dispositivo) |
| **Consecuencias** | Modelo debe ser < 100MB; requiere quantización; actualizaciones OTA del modelo |
| **Alternativa descartada** | Cloud inference — mayor latencia, dependencia de red, costos por request |

#### ADR-002: Arquitectura de la Aplicación

| Aspecto | Decisión |
|---------|----------|
| **Contexto** | Se requiere una arquitectura mantenible, testable y escalable |
| **Decisión** | Clean Architecture con patrón MVVM + Repository |
| **Justificación** | Separación clara de capas; facilita testing unitario; principios SOLID |
| **Consecuencias** | Mayor boilerplate inicial; curva de aprendizaje para junior devs |
| **Alternativa descartada** | MVC monolítico — difícil de testear y escalar |

#### ADR-003: Estrategia de Almacenamiento de Datos de Salud

| Aspecto | Decisión |
|---------|----------|
| **Contexto** | Datos de alergias e intolerancias son datos sensibles de salud (GDPR Art. 9) |
| **Decisión** | Almacenamiento local cifrado + sincronización opt-in con backend |
| **Justificación** | Minimización de datos; cumplimiento GDPR; control del usuario |
| **Consecuencias** | Si el usuario pierde el dispositivo sin sync, pierde perfil; requiere backup cifrado |
| **Alternativa descartada** | Solo almacenamiento cloud — riesgo regulatorio, dependencia de red |

#### ADR-004: Motor de Sugerencia de Menú

| Aspecto | Decisión |
|---------|----------|
| **Contexto** | Se necesita un motor que combine ingredientes con recetas respetando restricciones |
| **Decisión** | Motor basado en reglas + scoring con posibilidad de evolución a ML-based ranking |
| **Justificación** | Transparencia en recomendaciones (explicabilidad); menor riesgo en v1; iterable |
| **Consecuencias** | Las reglas deben mantenerse manualmente; menor personalización vs. ML puro |
| **Alternativa descartada** | LLM para generar recetas — costos, alucinaciones posibles, riesgo en recomendaciones de salud |

#### ADR-005: Framework de Desarrollo Móvil

| Aspecto | Decisión |
|---------|----------|
| **Contexto** | Se necesita soporte iOS y Android con acceso a cámara y modelos ML |
| **Decisión** | Flutter con plugins nativos para cámara y ML runtime |
| **Justificación** | Codebase único; buen rendimiento; ecosistema maduro para ML mobile |
| **Consecuencias** | Dependencia del ecosistema Flutter; plugins nativos para funciones específicas |
| **Alternativa descartada** | React Native — puentes nativos más complejos para ML; Kotlin/Swift nativo — doble mantenimiento |

### 5.5 Correspondencias entre Vistas (View Correspondences)

| Vista Origen | Vista Destino | Correspondencia |
|--------------|---------------|-----------------|
| Lógica: `IngredientRecognitionService` | Proceso: Paso [3] Inferencia ML | El servicio encapsula la lógica del hilo de inferencia |
| Lógica: `UserHealthService` | Datos: `HealthProfile` | El servicio gestiona el ciclo de vida de la entidad |
| Lógica: `MenuGenerationService` | Proceso: Paso [9] Motor de Menú | El servicio orquesta el algoritmo de matching |
| Despliegue: Modelo ML en dispositivo | Proceso: Paso [3] | El artefacto TFLite se ejecuta en el hilo de inferencia |
| Datos: `Recipe` | Despliegue: Recipe Service (Cloud) | La entidad se sincroniza desde el microservicio backend |

### 5.6 Rationale (Justificación Global)

La arquitectura se diseñó priorizando:

1. **Privacidad por diseño** — Las imágenes del usuario nunca abandonan el dispositivo
2. **Offline-first** — La funcionalidad core (detección + sugerencia básica) funciona sin red
3. **Seguridad alimentaria** — El sistema NO reemplaza consejo médico; las restricciones son conservadoras (ante duda, excluir)
4. **Evolución incremental** — Del motor de reglas a ML-based ranking sin reescritura
5. **Rendimiento percibido** — Feedback visual inmediato mientras el modelo procesa

---


## 6. Requisitos Funcionales

### 6.1 Épicas y Historias de Usuario

#### EP-01: Reconocimiento Visual de Ingredientes

| ID | Historia de Usuario | Criterios de Aceptación |
|----|--------------------|-----------------------|
| **RF-01** | Como usuario, quiero apuntar mi cámara a los ingredientes disponibles para que el sistema los identifique automáticamente | • El sistema detecta ingredientes en < 2s por frame<br>• Muestra bounding box + label con confianza > 70%<br>• Soporta detección múltiple (≥ 5 ingredientes simultáneos)<br>• Funciona sin conexión a internet |
| **RF-02** | Como usuario, quiero confirmar o corregir los ingredientes detectados antes de continuar | • Lista editable de ingredientes detectados<br>• Opción de eliminar falsos positivos<br>• Opción de agregar ingredientes manualmente (búsqueda por texto)<br>• Botón de "re-escanear" para nueva captura |
| **RF-03** | Como usuario, quiero poder capturar ingredientes en múltiples tomas para agregar todos los que tengo | • Modo "acumulativo" que suma ingredientes de múltiples escaneos<br>• Indicador visual del total acumulado<br>• Opción de reiniciar la lista completa |

#### EP-02: Perfil de Salud y Restricciones Alimentarias

| ID | Historia de Usuario | Criterios de Aceptación |
|----|--------------------|-----------------------|
| **RF-04** | Como usuario, quiero registrar mis alergias alimentarias para que el sistema nunca me sugiera recetas peligrosas | • Lista predefinida de alérgenos principales (14 alérgenos EU + regionales)<br>• Búsqueda libre para alérgenos no listados<br>• Nivel de severidad configurable (leve/moderado/severo)<br>• Alerta visual prominente si se detecta ingrediente alérgeno |
| **RF-05** | Como usuario, quiero indicar mis intolerancias alimentarias para recibir menús que pueda digerir | • Intolerancias predefinidas: lactosa, gluten, fructosa, histamina, etc.<br>• Diferenciación clara entre alergia (inmunológica) e intolerancia (digestiva)<br>• Nivel de tolerancia configurable (puede consumir en pequeñas cantidades vs. exclusión total) |
| **RF-06** | Como usuario, quiero registrar contraindicaciones médicas para que las sugerencias sean seguras | • Condiciones predefinidas: diabetes, hipertensión, enfermedad celíaca, gota, etc.<br>• Mapeo condición → ingredientes a evitar/limitar<br>• Disclaimer médico visible: "No reemplaza consejo profesional"<br>• Fecha de última actualización del perfil visible |
| **RF-07** | Como usuario, quiero indicar mis preferencias dietéticas para personalizar las sugerencias | • Opciones: omnívoro, vegetariano, vegano, pescetariano, keto, paleo, etc.<br>• Preferencias regionales de cocina (peruana, mexicana, mediterránea, etc.)<br>• Nivel de dificultad preferido (fácil/medio/avanzado) |



#### EP-03: Generación y Presentación de Menú

| ID | Historia de Usuario | Criterios de Aceptación |
|----|--------------------|-----------------------|
| **RF-08** | Como usuario, quiero recibir sugerencias de menú basadas en mis ingredientes detectados y mi perfil | • Mínimo 3 opciones de menú sugeridas<br>• Cada opción muestra: nombre, tiempo estimado, dificultad, ingredientes usados/faltantes<br>• Menús filtrados según restricciones del perfil de salud<br>• Indicador de "match" (% de ingredientes que ya tengo) |
| **RF-09** | Como usuario, quiero ver el detalle de cada receta sugerida | • Ingredientes con cantidades<br>• Pasos de preparación<br>• Tiempo total y por paso<br>• Información nutricional básica (calorías, proteínas, carbohidratos, grasas)<br>• Señalización de alérgenos presentes |
| **RF-10** | Como usuario, quiero poder descartar sugerencias y pedir alternativas | • Botón "no me gusta" / "otra opción" por cada sugerencia<br>• El sistema aprende de los descartes para futuras recomendaciones<br>• Opción de indicar motivo del descarte (no me gusta, muy difícil, muy largo, etc.) |
| **RF-11** | Como usuario, quiero guardar menús favoritos para acceder a ellos después | • Botón de favorito/guardar en cada receta<br>• Sección de favoritos accesible desde navegación principal<br>• Posibilidad de organizar por categorías/tags propios |

#### EP-04: Cuestionario Inteligente (Wizard de Salud)

| ID | Historia de Usuario | Criterios de Aceptación |
|----|--------------------|-----------------------|
| **RF-12** | Como usuario nuevo, quiero que el sistema me guíe paso a paso para completar mi perfil de salud | • Wizard progresivo de máximo 5 pantallas<br>• Indicador de progreso visible<br>• Posibilidad de omitir y completar después<br>• Lenguaje accesible (no médico/técnico)<br>• Explicación breve de por qué se pide cada dato |
| **RF-13** | Como usuario, quiero que el sistema me pregunte preguntas de seguimiento contextualmente relevantes | • Si detecto "leche" y no tengo perfil de lactosa → pregunta proactiva<br>• Si detecto "pan" y no tengo perfil de gluten → pregunta proactiva<br>• Preguntas no intrusivas (máximo 1 por sesión si perfil incompleto)<br>• Opción de "no preguntar de nuevo" |
| **RF-14** | Como usuario, quiero actualizar mi perfil de salud en cualquier momento | • Accesible desde configuración<br>• Historial de cambios<br>• Confirmación antes de guardar cambios críticos (añadir/quitar alergia) |

#### EP-05: Historial y Aprendizaje

| ID | Historia de Usuario | Criterios de Aceptación |
|----|--------------------|-----------------------|
| **RF-15** | Como usuario, quiero ver el historial de mis escaneos y menús sugeridos | • Lista cronológica de sesiones anteriores<br>• Cada sesión muestra: fecha, ingredientes detectados, menú elegido<br>• Búsqueda y filtro por ingrediente/fecha |
| **RF-16** | Como usuario, quiero que el sistema mejore sus sugerencias con el tiempo | • Tracking de recetas aceptadas vs. descartadas<br>• Peso de preferencias implícitas en el ranking<br>• Reset de preferencias aprendidas disponible |



### 6.2 Matriz de Trazabilidad (Requisitos ↔ Componentes)

| Requisito | Componente Lógico | Vista de Proceso | Datos Involucrados |
|-----------|-------------------|------------------|-------------------|
| RF-01, RF-02, RF-03 | IngredientRecognitionService | Pasos [1]-[5] | ML Model, Ingredient |
| RF-04, RF-05, RF-06, RF-07 | UserHealthService | Paso [8] Wizard | HealthProfile, User |
| RF-08, RF-09, RF-10, RF-11 | MenuGenerationService | Pasos [9]-[10] | Recipe, MenuSession |
| RF-12, RF-13, RF-14 | UserHealthService + UI Wizard | Pasos [7]-[8] | HealthProfile |
| RF-15, RF-16 | HistoryService + RecommendationEngine | Post-flujo | MenuSession |

---

## 7. Requisitos No Funcionales

### 7.1 Rendimiento (ISO 25010 — Performance Efficiency)

| ID | Requisito | Métrica | Objetivo |
|----|-----------|---------|----------|
| **RNF-01** | Latencia de detección | Tiempo desde captura hasta resultado visible | ≤ 2 segundos (P95) |
| **RNF-02** | Precisión del modelo | Mean Average Precision (mAP@0.5) | ≥ 85% en categorías del dataset |
| **RNF-03** | Tiempo de generación de menú | Desde confirmación de ingredientes hasta presentación | ≤ 3 segundos |
| **RNF-04** | Consumo de batería | Durante sesión activa de escaneo (5 min) | ≤ 5% de batería consumida |
| **RNF-05** | Uso de memoria RAM | Durante inferencia activa | ≤ 300MB adicionales al baseline de la app |
| **RNF-06** | Tamaño de la aplicación | APK/IPA instalada (incluyendo modelo) | ≤ 150MB |

### 7.2 Escalabilidad (Scalability)

| ID | Requisito | Métrica | Objetivo |
|----|-----------|---------|----------|
| **RNF-07** | Escalabilidad del catálogo de ingredientes | Clases soportadas por el modelo | ≥ 50 ingredientes en v1, extensible a 200+ |
| **RNF-08** | Escalabilidad de recetas | Recetas en la base de datos | ≥ 500 recetas en v1, sin límite arquitectónico |
| **RNF-09** | Usuarios concurrentes (backend) | Requests por segundo al Recipe Service | ≥ 1000 RPS con auto-scaling |

### 7.3 Fiabilidad (Reliability)

| ID | Requisito | Métrica | Objetivo |
|----|-----------|---------|----------|
| **RNF-10** | Disponibilidad del backend | Uptime mensual | ≥ 99.5% |
| **RNF-11** | Disponibilidad offline | Funcionalidad core sin red | Detección + menú básico 100% operativos offline |
| **RNF-12** | Tolerancia a fallos del modelo | Comportamiento ante ingrediente no reconocido | Graceful degradation: "No identificado" + input manual |
| **RNF-13** | Integridad de datos de salud | Pérdida de datos del perfil | Zero data loss con backup local cifrado |

### 7.4 Seguridad (Security)

| ID | Requisito | Métrica | Objetivo |
|----|-----------|---------|----------|
| **RNF-14** | Cifrado de datos en reposo | Algoritmo de cifrado para datos de salud | AES-256 para almacenamiento local |
| **RNF-15** | Cifrado en tránsito | Protocolo de comunicación | TLS 1.3 mínimo |
| **RNF-16** | Autenticación | Método de autenticación | OAuth 2.0 + biometría local opcional |
| **RNF-17** | Privacidad de imágenes | Imágenes capturadas por la cámara | NUNCA salen del dispositivo; se eliminan post-inferencia |
| **RNF-18** | Consentimiento GDPR | Gestión de consentimiento | Opt-in explícito para cada tipo de dato; revocable |

### 7.5 Usabilidad (Usability)

| ID | Requisito | Métrica | Objetivo |
|----|-----------|---------|----------|
| **RNF-19** | Accesibilidad | Nivel WCAG | 2.1 AA mínimo |
| **RNF-20** | Onboarding | Tiempo hasta primera sugerencia exitosa | ≤ 3 minutos para usuario nuevo |
| **RNF-21** | Tasa de éxito de tarea | Porcentaje de usuarios que completan el flujo | ≥ 90% en test de usabilidad |
| **RNF-22** | Idiomas soportados | Localización | Español (LATAM) + Inglés en v1 |
| **RNF-23** | Soporte de dispositivos | Versiones mínimas | Android 8.0+ / iOS 14+ |

### 7.6 Mantenibilidad (Maintainability)

| ID | Requisito | Métrica | Objetivo |
|----|-----------|---------|----------|
| **RNF-24** | Cobertura de tests | Porcentaje de code coverage | ≥ 80% unitarios, ≥ 60% integración |
| **RNF-25** | Complejidad ciclomática | Por método/función | ≤ 10 (McCabe) |
| **RNF-26** | Actualización del modelo ML | Tiempo de despliegue de nuevo modelo | ≤ 24h desde validación hasta producción (OTA) |
| **RNF-27** | Documentación de código | Porcentaje de APIs públicas documentadas | 100% |

---


## 8. Diseño del Modelo ML y Pipeline de Datos

> ### ⚠️ ADDENDUM v1.1 — Cambio de Estrategia ML (2026-07-22)
>
> Tras el análisis del dataset real disponible (Kaggle: `compilado-de-ingredientesalimentos`),
> se identificó que el dataset es de **clasificación** (una imagen = un ingrediente) y **NO tiene
> anotaciones de bounding box**. Por esta razón, la estrategia se adapta:
>
> | Aspecto | SDD Original (v1.0) | Estrategia Revisada (v1.1) |
> |---------|--------------------|-----------------------------|
> | **Problema ML** | Detección de objetos (multi-ingrediente) | Clasificación de imagen (un ingrediente por foto) |
> | **Modelo** | YOLOv8n (Object Detection) | EfficientNetV2-S (Image Classification) |
> | **Input** | 640×640 stream de cámara | 224×224 foto individual |
> | **Output** | Bounding boxes + clases | Top-K clases + probabilidades |
> | **UX** | Apuntar cámara en vivo (streaming) | Tomar foto → clasificar → agregar a lista |
> | **Dataset** | Requería anotaciones bbox | Funciona directo con carpetas por clase ✅ |
> | **Entrenamiento** | GPU potente requerida | Kaggle/Colab gratis (P100/T4) ✅ |
> | **Tamaño modelo** | ~6-15MB (YOLOv8n quantizado) | ~5-10MB (EfficientNetV2-S quantizado) |
> | **Latencia** | <2s por frame | <500ms por foto |
>
> **Roadmap de evolución:**
> - **v1.0:** Clasificación (EfficientNetV2-S) — dataset actual sin modificar
> - **v1.2+:** Detección (YOLOv8n) — cuando se anoten bounding boxes (auto-labeling con modelo v1 como pre-anotador)
>
> La arquitectura de software (Clean Architecture, interfaces, DI) NO cambia. Solo se
> sustituye la implementación concreta: `TFLiteClassifier` en lugar de `TFLiteDetector`,
> ambos implementando la misma interfaz `IngredientDetectorPort` (principio LSP/DIP).

### 8.0 Dataset Real — Análisis del Dataset Disponible

| Aspecto | Valor |
|---------|-------|
| **Fuente** | Kaggle: `guigasousa/compilado-de-ingredientesalimentos` |
| **Total imágenes** | 43,515 |
| **Categorías** | 35 ingredientes |
| **Anotaciones bbox** | ❌ No disponibles |
| **Formato** | Carpetas por clase (`/train/chicken/*.jpg`) |
| **Resolución** | Variable (168px a 1612px) — normalizado a 224×224 |
| **Balance** | Desbalanceado (apple: 7013 vs black_beans: 164) |
| **Split original** | Solo `train/` — creamos splits 70/15/15 |

#### Categorías del Dataset

| Categoría (EN) | Nombre (ES) | Imágenes | Balance |
|----------------|-------------|----------|---------|
| apple | manzana | 7,013 | ↓ subsample a 2000 |
| carrots | zanahoria | 2,739 | ↓ subsample a 2000 |
| cauliflower | coliflor | 2,139 | ↓ subsample a 2000 |
| corn | maíz | 2,027 | ↓ subsample a 2000 |
| cabbage | repollo | 2,014 | ↓ subsample a 2000 |
| avocado | palta | 1,792 | ✓ ok |
| butter | mantequilla | 1,561 | ✓ ok |
| chicken | pollo | 1,412 | ✓ ok |
| broccoli | brócoli | 1,321 | ✓ ok |
| cheese | queso | 1,314 | ✓ ok |
| bacon | tocino | 1,306 | ✓ ok |
| bread | pan | 1,304 | ✓ ok |
| crab | cangrejo | 1,300 | ✓ ok |
| coconut | coco | 1,300 | ✓ ok |
| chocolate | chocolate | 1,300 | ✓ ok |
| cherries | cerezas | 1,300 | ✓ ok |
| celery | apio | 1,300 | ✓ ok |
| blackberries | moras | 1,300 | ✓ ok |
| beef | carne de res | 1,300 | ✓ ok |
| beans | frijoles | 1,300 | ✓ ok |
| bagels | bagel | 1,300 | ✓ ok |
| banana | plátano | 1,236 | ✓ ok |
| cilantro leaves | cilantro | 849 | ✓ ok |
| capsicum | pimiento | 498 | ✓ ok |
| apricot | damasco | 492 | ✓ ok |
| cranberries | arándanos | 438 | ✓ ok |
| beetroot | betarraga | 412 | ✓ ok |
| brown sugar | azúcar morena | 336 | ⚠ augmentation |
| black pepper | pimienta negra | 330 | ⚠ augmentation |
| chili powder | ají en polvo | 282 | ⚠ augmentation |
| bay leaves | laurel | 282 | ⚠ augmentation |
| baking powder | polvo de hornear | 226 | ⚠ augmentation |
| chilli | ají | 190 | ⚠ augmentation |
| corn starch | maicena | 182 | ⚠ augmentation |
| black beans | frijoles negros | 164 | ⚠ augmentation |

### 8.0.1 Modelo Seleccionado — EfficientNetV2-S

| Aspecto | Detalle |
|---------|---------|
| **Arquitectura** | EfficientNetV2-S (Small) |
| **Pre-entrenamiento** | ImageNet-1K (1000 clases) |
| **Input** | 224×224×3 (RGB normalizado) |
| **Output** | Vector de 35 probabilidades (softmax) |
| **Parámetros totales** | ~21.5M |
| **Parámetros entrenables (Phase 1)** | ~270K (solo classifier head) |
| **Tamaño FP32** | ~85MB |
| **Tamaño quantizado (FP16)** | ~42MB |
| **Tamaño quantizado (INT8)** | ~22MB |
| **Latencia esperada (mobile)** | 200-500ms |

#### ¿Por qué EfficientNetV2-S sobre otras opciones?

| Modelo | Accuracy ImageNet | Size (MB) | Latencia Mobile | Decisión |
|--------|-------------------|-----------|-----------------|----------|
| MobileNetV3-Large | 75.2% | 5.4 | 30ms | Descartado — accuracy insuficiente para 35 clases similares |
| EfficientNetV2-S | **84.2%** | 22 (INT8) | 300ms | **SELECCIONADO** — mejor accuracy con tamaño aceptable |
| EfficientNetV2-M | 85.1% | 55 (INT8) | 600ms | Backup — si S no alcanza targets |
| ResNet50 | 80.4% | 25 (INT8) | 400ms | Descartado — EfficientNetV2 es superior en accuracy/size |
| ViT-B/16 | 85.0% | 86 (INT8) | 1200ms | Descartado — demasiado pesado para mobile |

### 8.0.2 Estrategia de Entrenamiento (2 Fases)

```
┌──────────────── TRAINING STRATEGY v1.1 ────────────────────────────┐
│                                                                     │
│  PHASE 1: TRAIN CLASSIFIER HEAD (Backbone Frozen)                  │
│  ─────────────────────────────────────────────────                  │
│  • Epochs: 10                                                       │
│  • Learning Rate: 1e-3 (cosine decay)                              │
│  • Capas entrenadas: Classifier head solamente (270K params)       │
│  • Propósito: Adaptar la capa de salida a nuestras 35 clases      │
│  • Resultado esperado: ~70-80% accuracy rápidamente                │
│                                                                     │
│  PHASE 2: FINE-TUNE ALL LAYERS                                     │
│  ─────────────────────────────────────────────────                  │
│  • Epochs: 40 (early stopping patience=10)                         │
│  • Learning Rate: 1e-4 (cosine with warm restarts)                 │
│  • Capas entrenadas: TODAS (21.5M params)                          │
│  • Técnicas: Mixup (α=0.2), Label Smoothing (0.1), Class Weights  │
│  • Propósito: Ajuste fino para ingredientes específicos            │
│  • Resultado esperado: ≥ 90% accuracy, ≥ 88% F1                  │
│                                                                     │
│  HARDWARE: Kaggle GPU (P100 16GB) — Tiempo estimado: 2-4 horas    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.0.3 Pipeline de Inferencia Revisado (Clasificación)

```
┌──────────── INFERENCE PIPELINE (Classification) ──────────────────┐
│                                                                    │
│  [1] Usuario toma FOTO de un ingrediente                          │
│       │                                                            │
│       ▼                                                            │
│  [2] Pre-procesamiento                                            │
│       • Resize a 256px (lado menor)                               │
│       • Center crop a 224×224                                     │
│       • Normalizar con mean/std de ImageNet                       │
│       │                                                            │
│       ▼                                                            │
│  [3] Inferencia TFLite (on-device)                                │
│       • Input: tensor [1, 3, 224, 224]                            │
│       • Output: vector [35] probabilidades                        │
│       • Latencia: ~200-500ms                                      │
│       │                                                            │
│       ▼                                                            │
│  [4] Post-procesamiento                                           │
│       • Softmax → probabilidades                                  │
│       • Top-K (K=3) clases con confidence > 0.7                   │
│       • Mapeo class_id → nombre ingrediente (ES)                  │
│       │                                                            │
│       ▼                                                            │
│  [5] UI: Mostrar resultado + confirmar                            │
│       • "¿Es esto POLLO? (94%)"                                  │
│       • Botones: ✓ Sí | ✗ No, es otro | 📷 Escanear más         │
│       │                                                            │
│       ▼                                                            │
│  [6] Agregar a lista de ingredientes                              │
│       • Modo acumulativo (puede seguir escaneando)                │
│       • Cuando listo → ir al Motor de Menú                        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---


### 8.1 Visión General del Sistema ML

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ML LIFECYCLE COMPLETO                              │
│                                                                          │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │  DATA   │───▶│  TRAIN   │───▶│  EVAL    │───▶│  DEPLOY  │           │
│  │PIPELINE │    │ PIPELINE │    │ PIPELINE │    │ PIPELINE │           │
│  └─────────┘    └──────────┘    └──────────┘    └──────────┘           │
│       │              │               │               │                   │
│       ▼              ▼               ▼               ▼                   │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │Dataset  │    │ Modelo   │    │ Métricas │    │ Modelo   │           │
│  │Versionado│   │ Entrenado│    │ & Reports│    │ en Prod  │           │
│  │(DVC/GCS)│    │ (MLflow) │    │          │    │ (TFLite) │           │
│  └─────────┘    └──────────┘    └──────────┘    └──────────┘           │
│                                                                          │
│                    ┌──────────────────────┐                              │
│                    │   MONITORING &       │                              │
│                    │   RETRAINING LOOP    │◀── Feedback de producción    │
│                    └──────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Dataset

#### 8.2.1 Descripción del Dataset Actual

| Aspecto | Detalle |
|---------|---------|
| **Categorías iniciales** | Palta (aguacate), pollo, papas, carne de cerdo, tomate, cebolla, ajo, arroz, huevos, limón, zanahoria, pimiento, brócoli, queso, leche |
| **Formato** | Imágenes JPEG/PNG + anotaciones en formato COCO/YOLO |
| **Resolución objetivo** | 640x640 px (redimensionado para entrenamiento) |
| **Variabilidad requerida** | Múltiples ángulos, iluminaciones, fondos, estados (crudo/cocido/cortado) |
| **Balanceo** | Mínimo 200 imágenes por clase; oversampling/augmentation para clases minoritarias |

#### 8.2.2 Estrategia de Anotación

```
┌────────────────────── PROCESO DE ANOTACIÓN ──────────────────────┐
│                                                                    │
│  [1] Captura / Recolección de imágenes                            │
│       │                                                            │
│       ▼                                                            │
│  [2] Filtrado de calidad (eliminar borrosas, duplicadas)          │
│       │                                                            │
│       ▼                                                            │
│  [3] Anotación con herramienta (CVAT / Label Studio / Roboflow)  │
│       • Bounding boxes para detección de objetos                  │
│       • Labels de clase por cada ingrediente                      │
│       │                                                            │
│       ▼                                                            │
│  [4] Revisión cruzada (2do anotador valida ≥ 20% del dataset)    │
│       │                                                            │
│       ▼                                                            │
│  [5] Exportación en formato COCO JSON + YOLO TXT                 │
│       │                                                            │
│       ▼                                                            │
│  [6] Versionamiento con DVC (Data Version Control)                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 8.2.3 Data Augmentation

| Técnica | Parámetros | Propósito |
|---------|------------|-----------|
| Rotación | ±15° | Simular diferentes ángulos de captura |
| Flip horizontal | 50% probabilidad | Invarianza a orientación |
| Ajuste de brillo | ±30% | Simular diferentes condiciones de luz |
| Ajuste de contraste | ±20% | Robustez a cámaras de diferente calidad |
| Recorte aleatorio | 80-100% del área | Ingredientes parcialmente visibles |
| Ruido gaussiano | σ = 0.01 | Robustez a ruido de cámara |
| Mosaic augmentation | 4 imágenes combinadas | Multi-objeto y contexto variado |
| Mixup | α = 0.2 | Regularización y generalización |



### 8.3 Arquitectura del Modelo

#### 8.3.1 Selección del Modelo Base

| Modelo Candidato | Tamaño | mAP (COCO) | Latencia Mobile | Decisión |
|------------------|--------|-------------|-----------------|----------|
| YOLOv8n (nano) | ~6MB | 37.3 | ~30ms | **SELECCIONADO** — mejor balance tamaño/velocidad |
| YOLOv8s (small) | ~22MB | 44.9 | ~60ms | Alternativa si se necesita más precisión |
| EfficientDet-D0 | ~15MB | 34.6 | ~50ms | Descartado — menor mAP para el tamaño |
| MobileNetV3 + SSD | ~10MB | 22.0 | ~25ms | Descartado — mAP insuficiente |
| YOLOv8m (medium) | ~52MB | 50.2 | ~120ms | Descartado — demasiado pesado para mobile |

#### 8.3.2 Arquitectura Detallada (YOLOv8n - Custom)

```
┌─────────────────────── YOLOv8n-MenuAI ───────────────────────────┐
│                                                                    │
│  INPUT: 640x640x3 (RGB normalizado)                              │
│       │                                                            │
│       ▼                                                            │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │                    BACKBONE (CSPDarknet)                  │      │
│  │  Conv → C2f → Conv → C2f → Conv → C2f → SPPF           │      │
│  │  Extracción de features multi-escala                     │      │
│  └───────────────┬────────────────┬────────────┬───────────┘      │
│                  │ P3             │ P4         │ P5               │
│                  ▼                ▼            ▼                   │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │                    NECK (PANet / FPN)                     │      │
│  │  Fusión de features multi-escala (top-down + bottom-up)  │      │
│  └───────────────┬────────────────┬────────────┬───────────┘      │
│                  │                │            │                   │
│                  ▼                ▼            ▼                   │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │                    HEAD (Decoupled)                       │      │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │      │
│  │  │ Det Head   │  │ Det Head   │  │ Det Head   │        │      │
│  │  │ 80x80      │  │ 40x40      │  │ 20x20      │        │      │
│  │  │ (objetos   │  │ (objetos   │  │ (objetos   │        │      │
│  │  │  pequeños) │  │  medianos) │  │  grandes)  │        │      │
│  │  └────────────┘  └────────────┘  └────────────┘        │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                    │
│  OUTPUT: [batch, num_detections, 5 + num_classes]                 │
│          (x, y, w, h, confidence, class_probabilities)            │
│                                                                    │
│  num_classes = 50 (v1: 15 iniciales + espacio para expansión)    │
└────────────────────────────────────────────────────────────────────┘
```

#### 8.3.3 Transfer Learning Strategy

| Fase | Epochs | Learning Rate | Capas Entrenadas | Propósito |
|------|--------|---------------|------------------|-----------|
| **Fase 1: Freeze backbone** | 20 | 1e-3 | Solo head (detection layers) | Adaptar detección a ingredientes |
| **Fase 2: Fine-tune** | 50 | 1e-4 (cosine decay) | Todas las capas | Ajuste fino completo |
| **Fase 3: Pruning + QAT** | 10 | 1e-5 | Todas (con quantization-aware) | Optimización para mobile |



### 8.4 Pipeline de Entrenamiento

```
┌────────────────────── TRAINING PIPELINE ──────────────────────────┐
│                                                                    │
│  ┌──────────────┐                                                 │
│  │  Raw Dataset │  (imágenes + anotaciones versionadas con DVC)  │
│  └──────┬───────┘                                                 │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────┐                 │
│  │  PREPROCESSING                                │                 │
│  │  • Resize a 640x640                          │                 │
│  │  • Normalización [0,1]                       │                 │
│  │  • Split: Train 70% / Val 20% / Test 10%    │                 │
│  │  • Stratified split (mantener balance)       │                 │
│  └──────┬───────────────────────────────────────┘                 │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────┐                 │
│  │  DATA AUGMENTATION (online durante training)  │                 │
│  │  • Mosaic, Mixup, HSV augment                │                 │
│  │  • Random perspective                         │                 │
│  └──────┬───────────────────────────────────────┘                 │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────┐                 │
│  │  TRAINING                                     │                 │
│  │  • Optimizer: AdamW (weight_decay=0.0005)    │                 │
│  │  • Batch size: 16-32 (según GPU disponible)  │                 │
│  │  • Epochs: 80 (early stopping patience=15)   │                 │
│  │  • Loss: CIoU + BCE (classification)         │                 │
│  │  • Hardware: GPU NVIDIA T4/A100 (cloud)      │                 │
│  └──────┬───────────────────────────────────────┘                 │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────┐                 │
│  │  EVALUATION                                   │                 │
│  │  • mAP@0.5 (objetivo: ≥ 85%)                │                 │
│  │  • mAP@0.5:0.95 (objetivo: ≥ 60%)           │                 │
│  │  • Precision / Recall por clase              │                 │
│  │  • Confusion matrix                          │                 │
│  │  • Latencia de inferencia en target device   │                 │
│  └──────┬───────────────────────────────────────┘                 │
│         │                                                          │
│         ├── Métricas OK? ── NO ──▶ Ajustar hiperparámetros       │
│         │                          y volver a entrenar            │
│         │                                                          │
│         └── SÍ                                                    │
│              │                                                     │
│              ▼                                                     │
│  ┌──────────────────────────────────────────────┐                 │
│  │  EXPORT & OPTIMIZATION                        │                 │
│  │  • Export a ONNX                             │                 │
│  │  • Conversión a TFLite (INT8 quantization)   │                 │
│  │  • Validación post-conversión (< 2% drop)    │                 │
│  │  • Benchmark en dispositivo real             │                 │
│  └──────┬───────────────────────────────────────┘                 │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────┐                 │
│  │  REGISTRY & VERSIONING (MLflow)               │                 │
│  │  • Modelo versionado (v1.0, v1.1, ...)       │                 │
│  │  • Métricas asociadas                        │                 │
│  │  • Dataset version asociado                  │                 │
│  │  • Reproducibilidad garantizada              │                 │
│  └──────────────────────────────────────────────┘                 │
└────────────────────────────────────────────────────────────────────┘
```

### 8.5 Pipeline de Inferencia (On-Device)

```
┌────────────────────── INFERENCE PIPELINE ─────────────────────────┐
│                                                                    │
│  ┌─────────────┐   Thread: UI (Main)                             │
│  │  Camera     │                                                  │
│  │  Preview    │──── Frame (YUV/RGB) ────┐                       │
│  └─────────────┘                          │                       │
│                                           ▼                       │
│                              ┌─────────────────────┐              │
│                              │  PRE-PROCESSING     │  Thread: BG  │
│                              │  • YUV → RGB        │              │
│                              │  • Resize 640x640   │              │
│                              │  • Normalize [0,1]  │              │
│                              │  • Tensor creation  │              │
│                              └──────────┬──────────┘              │
│                                         │                         │
│                                         ▼                         │
│                              ┌─────────────────────┐              │
│                              │  ML INFERENCE       │  Thread: ML  │
│                              │  • TFLite Interpreter│             │
│                              │  • GPU Delegate     │              │
│                              │    (si disponible)  │              │
│                              │  • NNAPI Delegate   │              │
│                              │    (Android)        │              │
│                              └──────────┬──────────┘              │
│                                         │                         │
│                                         ▼                         │
│                              ┌─────────────────────┐              │
│                              │  POST-PROCESSING    │  Thread: BG  │
│                              │  • NMS (IoU > 0.45) │              │
│                              │  • Confidence filter│              │
│                              │    (threshold > 0.7)│              │
│                              │  • Class mapping    │              │
│                              └──────────┬──────────┘              │
│                                         │                         │
│                                         ▼                         │
│                              ┌─────────────────────┐              │
│                              │  RESULT             │  Thread: UI  │
│                              │  • Overlay bounding │              │
│                              │    boxes en preview │              │
│                              │  • Update lista de  │              │
│                              │    ingredientes     │              │
│                              └─────────────────────┘              │
└────────────────────────────────────────────────────────────────────┘

Frecuencia de inferencia: ~5-10 FPS (throttled para ahorro de batería)
```



### 8.6 Estrategia de Actualización del Modelo (OTA)

| Aspecto | Estrategia |
|---------|-----------|
| **Distribución** | Modelo empaquetado en app para v1 + OTA updates para modelos nuevos |
| **Descarga OTA** | Background download cuando WiFi disponible; aplicación al próximo inicio |
| **Rollback** | Siempre mantener modelo anterior como fallback; auto-rollback si crash rate > 1% |
| **A/B Testing** | Capacidad de servir diferentes versiones del modelo a % de usuarios |
| **Versionamiento** | Semantic versioning: MAJOR.MINOR.PATCH (ej: model-v1.2.0) |
| **Tamaño delta** | Actualizaciones incrementales cuando sea posible (< 20MB) |

### 8.7 Monitoreo y Reentrenamiento

#### 8.7.1 Métricas de Monitoreo en Producción

| Métrica | Fuente | Alerta si |
|---------|--------|-----------|
| Tasa de corrección manual | Usuarios que editan ingredientes post-detección | > 30% de sesiones |
| Distribución de confianza | Scores promedio de detección | Media cae < 0.75 |
| Clases no reconocidas | Ingredientes añadidos manualmente sin detección previa | Patrón recurrente (> 50 usuarios) |
| Latencia de inferencia | Tiempo medido en dispositivo | P95 > 3s |
| Crash rate en módulo ML | Crashes asociados al modelo | > 0.5% de sesiones |

#### 8.7.2 Triggers de Reentrenamiento

```
┌─────────────── CICLO DE REENTRENAMIENTO ──────────────────────┐
│                                                                │
│  TRIGGER automático si:                                        │
│  • mAP estimado en producción cae > 5% vs. baseline           │
│  • Nuevo ingrediente solicitado por > 100 usuarios             │
│  • Dataset aumenta > 20% desde último entrenamiento            │
│  • Han pasado > 90 días desde último modelo desplegado         │
│                                                                │
│  PROCESO:                                                      │
│  1. Recolectar nuevas muestras (opt-in de usuarios)            │
│  2. Anotar y validar                                           │
│  3. Entrenar con dataset extendido                             │
│  4. Evaluar contra test set + shadow deployment                │
│  5. Canary release (5% → 25% → 100%)                         │
│  6. Monitorear 72h post-release                                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 8.8 Consideraciones Éticas del Modelo

| Aspecto | Medida |
|---------|--------|
| **Bias en dataset** | Auditoría de representatividad geográfica/cultural de ingredientes; incluir ingredientes de diversas cocinas |
| **Transparencia** | El usuario siempre puede ver y corregir lo que el modelo detectó; nunca se toman decisiones ocultas |
| **Falsos negativos seguros** | Ante duda, NO incluir un ingrediente potencialmente peligroso en sugerencia |
| **No reemplaza profesionales** | Disclaimer claro: las restricciones de salud son indicativas, no prescriptivas |
| **Privacidad del dataset** | Nunca usar imágenes de usuarios para entrenamiento sin consentimiento explícito |

---


## 9. Principios SOLID Aplicados

> Los principios SOLID (Robert C. Martin) guían el diseño orientado a objetos de MenuAI, asegurando un código mantenible, extensible y testable. A continuación se documenta cómo cada principio se materializa en la arquitectura.

### 9.1 S — Single Responsibility Principle (SRP)

> *"Una clase debe tener una, y solo una, razón para cambiar."*

#### Aplicación en MenuAI:

| Componente | Responsabilidad Única | Razón de Cambio |
|------------|----------------------|-----------------|
| `CameraService` | Gestionar el stream de la cámara y captura de frames | Cambia si cambia la API de cámara del SO |
| `ImagePreprocessor` | Transformar frames crudos al formato requerido por el modelo | Cambia si cambian los requisitos de input del modelo |
| `IngredientDetector` | Ejecutar inferencia ML y devolver detecciones crudas | Cambia si cambia el modelo o runtime ML |
| `DetectionPostProcessor` | Aplicar NMS, filtrar por confianza, mapear clases | Cambia si cambian umbrales o lógica de filtrado |
| `HealthProfileRepository` | Persistir y recuperar datos del perfil de salud | Cambia si cambia la estrategia de almacenamiento |
| `AllergenValidator` | Verificar ingredientes contra alergias del usuario | Cambia si cambian las reglas de validación de alérgenos |
| `MenuScoringEngine` | Calcular score de match entre ingredientes y recetas | Cambia si cambia el algoritmo de ranking |
| `RecipeRepository` | Acceder a recetas (local cache + API remota) | Cambia si cambia la fuente de datos de recetas |
| `NotificationService` | Gestionar alertas y warnings al usuario | Cambia si cambian los canales de notificación |

#### Ejemplo de código (Dart/Flutter):

```dart
// ✅ CORRECTO: Cada clase tiene una sola responsabilidad
class IngredientDetector {
  final MLModelRunner _modelRunner;
  
  Future<List<RawDetection>> detect(PreprocessedImage image) async {
    return await _modelRunner.runInference(image.tensorData);
  }
}

class DetectionPostProcessor {
  final double _confidenceThreshold;
  final double _nmsIoUThreshold;
  
  List<DetectedIngredient> process(List<RawDetection> rawDetections) {
    final filtered = _filterByConfidence(rawDetections);
    final nmsApplied = _applyNMS(filtered);
    return _mapToIngredients(nmsApplied);
  }
}

// ❌ INCORRECTO: Clase con múltiples responsabilidades
class IngredientDetectorMonolith {
  // Viola SRP: cámara + preprocesamiento + inferencia + post-procesamiento
  Future<List<DetectedIngredient>> detectFromCamera() async { ... }
}
```

### 9.2 O — Open/Closed Principle (OCP)

> *"Las entidades de software deben estar abiertas a extensión, pero cerradas a modificación."*

#### Aplicación en MenuAI:

| Punto de Extensión | Mecanismo | Ejemplo |
|-------------------|-----------|---------|
| Nuevos tipos de restricción de salud | Interfaz `HealthRestriction` | Añadir "embarazo" sin modificar `AllergenValidator` |
| Nuevos modelos ML | Interfaz `MLModelRunner` | Migrar de TFLite a ONNX sin cambiar `IngredientDetector` |
| Nuevas fuentes de recetas | Interfaz `RecipeDataSource` | Añadir API de terceros sin modificar `RecipeRepository` |
| Nuevos algoritmos de scoring | Interfaz `ScoringStrategy` | Implementar ML-based ranking sin tocar la UI |
| Nuevos formatos de exportación | Interfaz `MenuExporter` | Añadir PDF/compartir sin modificar lógica core |

#### Ejemplo de código:

```dart
// Abierto a extensión mediante abstracciones
abstract class HealthRestriction {
  String get name;
  bool isIngredientSafe(Ingredient ingredient);
  String get warningMessage;
}

class AllergyRestriction implements HealthRestriction {
  final Allergen allergen;
  final Severity severity;
  
  @override
  bool isIngredientSafe(Ingredient ingredient) {
    return !ingredient.allergens.contains(allergen);
  }
}

class IntoleranceRestriction implements HealthRestriction {
  final IntoleranceType type;
  final ToleranceLevel level;
  
  @override
  bool isIngredientSafe(Ingredient ingredient) {
    if (level == ToleranceLevel.none) {
      return !ingredient.contains(type.substance);
    }
    return ingredient.getAmount(type.substance) < level.threshold;
  }
}

// Agregar nueva restricción (ej: embarazo) NO modifica código existente
class PregnancyRestriction implements HealthRestriction {
  @override
  bool isIngredientSafe(Ingredient ingredient) {
    return !_pregnancyUnsafeIngredients.contains(ingredient.id);
  }
}
```



### 9.3 L — Liskov Substitution Principle (LSP)

> *"Los objetos de un programa deberían ser reemplazables por instancias de sus subtipos sin alterar la corrección del programa."*

#### Aplicación en MenuAI:

| Abstracción Base | Sustituciones Válidas | Garantía de Comportamiento |
|-----------------|----------------------|---------------------------|
| `MLModelRunner` | `TFLiteRunner`, `ONNXRunner`, `MockRunner` | Toda implementación acepta tensor y devuelve detecciones con mismo formato |
| `RecipeDataSource` | `LocalDBSource`, `RemoteAPISource`, `CachedSource` | Toda implementación devuelve `List<Recipe>` con mismo contrato |
| `HealthRestriction` | `AllergyRestriction`, `IntoleranceRestriction`, `MedicalCondition` | Toda implementación responde `isIngredientSafe()` de forma booleana |
| `ImageSource` | `LiveCameraSource`, `GallerySource`, `TestFixtureSource` | Toda implementación provee frames en formato estándar |

#### Ejemplo de código:

```dart
// Contrato base con pre/post-condiciones claras
abstract class MLModelRunner {
  /// Pre-condición: inputData no vacío, dimensiones correctas
  /// Post-condición: retorna lista (puede ser vacía, nunca null)
  /// Invariante: no modifica el estado del inputData
  Future<List<RawDetection>> runInference(Float32List inputData);
  
  /// Invariante: siempre libera recursos al disponer
  void dispose();
}

class TFLiteRunner implements MLModelRunner {
  @override
  Future<List<RawDetection>> runInference(Float32List inputData) async {
    // Cumple mismo contrato: mismas pre/post condiciones
    final output = await _interpreter.run(inputData);
    return _parseOutput(output); // Nunca retorna null
  }
}

class ONNXRunner implements MLModelRunner {
  @override
  Future<List<RawDetection>> runInference(Float32List inputData) async {
    // Sustituto válido: mismo comportamiento observable
    final session = await _onnxSession.run(inputData);
    return _parseOnnxOutput(session); // Nunca retorna null
  }
}

// En el consumidor: funciona con CUALQUIER implementación
class IngredientDetector {
  final MLModelRunner _runner; // No sabe ni le importa cuál implementación
  
  Future<List<RawDetection>> detect(PreprocessedImage image) {
    return _runner.runInference(image.tensorData);
  }
}
```

### 9.4 I — Interface Segregation Principle (ISP)

> *"Los clientes no deben ser forzados a depender de interfaces que no usan."*

#### Aplicación en MenuAI:

```dart
// ❌ INCORRECTO: Interfaz "gorda" que fuerza implementaciones innecesarias
abstract class UserService {
  Future<User> getUser();
  Future<HealthProfile> getHealthProfile();
  Future<List<MenuSession>> getHistory();
  Future<void> updatePreferences();
  Future<void> syncToCloud();
  Future<void> exportData();
}

// ✅ CORRECTO: Interfaces segregadas por responsabilidad
abstract class UserReader {
  Future<User> getUser(String userId);
}

abstract class HealthProfileManager {
  Future<HealthProfile> getProfile(String userId);
  Future<void> updateProfile(String userId, HealthProfile profile);
}

abstract class MenuHistoryReader {
  Future<List<MenuSession>> getHistory(String userId, {int limit});
}

abstract class DataSyncable {
  Future<SyncResult> syncToCloud();
  Future<DateTime?> lastSyncDate();
}

abstract class DataExportable {
  Future<ExportedData> exportUserData(ExportFormat format);
}
```

#### Segregación aplicada a los módulos principales:

| Módulo | Interfaces que consume | Interfaces que NO necesita |
|--------|----------------------|---------------------------|
| `CameraScreen` | `ImageSource`, `IngredientDetectorPort` | `RecipeDataSource`, `DataSyncable` |
| `HealthWizard` | `HealthProfileManager`, `AllergenCatalog` | `MLModelRunner`, `MenuHistoryReader` |
| `MenuSuggestionScreen` | `MenuGenerator`, `RecipeReader` | `ImageSource`, `DataExportable` |
| `SettingsScreen` | `HealthProfileManager`, `DataSyncable`, `DataExportable` | `MLModelRunner`, `IngredientDetectorPort` |



### 9.5 D — Dependency Inversion Principle (DIP)

> *"Los módulos de alto nivel no deben depender de módulos de bajo nivel. Ambos deben depender de abstracciones."*

#### Aplicación en MenuAI:

```
┌─────────────────── DEPENDENCY INVERSION ──────────────────────────┐
│                                                                    │
│  CAPA DE ALTO NIVEL (Dominio/Casos de Uso)                       │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  GenerateMenuUseCase                                      │     │
│  │    depends on:                                            │     │
│  │      • IngredientDetectorPort (abstracción)              │     │
│  │      • HealthProfilePort (abstracción)                   │     │
│  │      • RecipeRepositoryPort (abstracción)                │     │
│  │      • MenuScoringPort (abstracción)                     │     │
│  └──────────────────────────────────────────────────────────┘     │
│                          ▲ depende de abstracciones                │
│                          │                                         │
│  ─────────────── CAPA DE ABSTRACCIONES (Ports) ──────────────     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  abstract IngredientDetectorPort                          │     │
│  │  abstract HealthProfilePort                               │     │
│  │  abstract RecipeRepositoryPort                            │     │
│  │  abstract MenuScoringPort                                 │     │
│  └──────────────────────────────────────────────────────────┘     │
│                          ▲ implementa abstracciones                │
│                          │                                         │
│  CAPA DE BAJO NIVEL (Infraestructura/Adapters)                   │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  TFLiteIngredientDetector implements IngredientDetectorPort│    │
│  │  SQLiteHealthProfileRepo implements HealthProfilePort     │     │
│  │  RestRecipeRepository implements RecipeRepositoryPort     │     │
│  │  RuleBasedScoring implements MenuScoringPort              │     │
│  └──────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

#### Inyección de Dependencias (DI Container):

```dart
// Configuración del contenedor DI (usando get_it o injectable)
final serviceLocator = GetIt.instance;

void configureDependencies() {
  // ML Layer
  serviceLocator.registerLazySingleton<MLModelRunner>(
    () => TFLiteRunner(modelPath: 'assets/models/menuai_v1.tflite'),
  );
  
  serviceLocator.registerLazySingleton<IngredientDetectorPort>(
    () => IngredientDetectorImpl(
      modelRunner: serviceLocator<MLModelRunner>(),
      postProcessor: serviceLocator<DetectionPostProcessor>(),
    ),
  );
  
  // Data Layer
  serviceLocator.registerLazySingleton<HealthProfilePort>(
    () => EncryptedHealthProfileRepository(
      database: serviceLocator<AppDatabase>(),
      encryptor: serviceLocator<DataEncryptor>(),
    ),
  );
  
  serviceLocator.registerLazySingleton<RecipeRepositoryPort>(
    () => CachedRecipeRepository(
      remoteSource: serviceLocator<RecipeAPIClient>(),
      localCache: serviceLocator<RecipeLocalCache>(),
    ),
  );
  
  // Domain Layer (Use Cases)
  serviceLocator.registerFactory<GenerateMenuUseCase>(
    () => GenerateMenuUseCase(
      detector: serviceLocator<IngredientDetectorPort>(),
      healthProfile: serviceLocator<HealthProfilePort>(),
      recipes: serviceLocator<RecipeRepositoryPort>(),
      scoring: serviceLocator<MenuScoringPort>(),
    ),
  );
}
```

### 9.6 Resumen de Beneficios SOLID en MenuAI

| Principio | Beneficio Principal | Impacto en el Proyecto |
|-----------|--------------------|-----------------------|
| **SRP** | Cambios localizados | Actualizar el modelo ML no afecta la UI ni el perfil de salud |
| **OCP** | Extensibilidad sin riesgo | Añadir nuevos ingredientes/restricciones sin tocar código estable |
| **LSP** | Intercambiabilidad | Cambiar TFLite por ONNX sin afectar la lógica de detección |
| **ISP** | Bajo acoplamiento | El módulo de cámara no conoce ni depende del módulo de recetas |
| **DIP** | Testabilidad total | Cada capa se testea con mocks/fakes sin infraestructura real |

### 9.7 Patrones Complementarios Aplicados

| Patrón | Dónde se Aplica | Propósito |
|--------|----------------|-----------|
| **Repository** | Acceso a datos (recetas, perfil, historial) | Abstraer fuente de datos; facilitar caching |
| **Strategy** | Algoritmo de scoring de menú | Intercambiar algoritmos sin modificar consumidores |
| **Observer/Stream** | Resultados de detección en tiempo real | Desacoplar producción de detecciones de su consumo UI |
| **Factory** | Creación de `HealthRestriction` según tipo | Encapsular lógica de instanciación compleja |
| **Adapter** | Integración con SDKs de cámara/ML | Adaptar interfaces externas al contrato interno |
| **Facade** | `MenuAIFacade` para orquestar el flujo completo | Simplificar interacción para la capa de presentación |

---


## 10. Diseño UX/UI

> Esta sección define la experiencia de usuario siguiendo principios de diseño centrado en el usuario (UCD), heurísticas de Nielsen, patrones de Material Design 3 y cumplimiento WCAG 2.1 AA.

### 10.1 Principios de Diseño UX

| # | Principio | Aplicación en MenuAI |
|---|-----------|---------------------|
| 1 | **Visibilidad del estado del sistema** | Feedback visual durante detección (bounding boxes animados); indicador de progreso en wizard |
| 2 | **Correspondencia con el mundo real** | Usar nombres comunes de ingredientes (no nombres científicos); iconografía alimentaria reconocible |
| 3 | **Control y libertad del usuario** | Siempre poder editar ingredientes detectados; omitir preguntas del wizard; deshacer acciones |
| 4 | **Consistencia y estándares** | Patrones de navegación estándar; iconografía consistente; terminología uniforme |
| 5 | **Prevención de errores** | Confirmar antes de eliminar perfil de salud; validación en tiempo real; sugerencias predictivas |
| 6 | **Reconocer antes que recordar** | Ingredientes con imágenes thumbnail; recetas con foto; historial accesible |
| 7 | **Flexibilidad y eficiencia** | Shortcuts para usuarios frecuentes; "repetir último escaneo"; favoritos |
| 8 | **Diseño minimalista** | Una acción principal por pantalla; información progresiva (disclosure gradual) |
| 9 | **Ayudar a reconocer y recuperar errores** | Mensajes claros si el modelo no detecta nada; guía para mejorar la captura |
| 10 | **Ayuda y documentación** | Tooltips contextuales; onboarding interactivo; FAQ accesible |

### 10.2 Arquitectura de Información

```
┌─────────────────── MAPA DE NAVEGACIÓN ────────────────────────────┐
│                                                                    │
│                    ┌──────────────────┐                            │
│                    │   Splash/Login   │                            │
│                    └────────┬─────────┘                            │
│                             │                                      │
│               ┌─────────────┼──────────────┐                      │
│               ▼             ▼              ▼                       │
│     ┌─────────────┐  ┌──────────┐  ┌───────────────┐             │
│     │  Onboarding │  │  Home    │  │  Returning    │             │
│     │  (1ra vez)  │  │  Screen  │  │  User Flow    │             │
│     └──────┬──────┘  └────┬─────┘  └───────┬───────┘             │
│            │               │                │                      │
│            ▼               ▼                ▼                      │
│     ┌──────────────────────────────────────────────────────┐      │
│     │              BOTTOM NAVIGATION BAR                     │      │
│     │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐     │      │
│     │  │ 📷     │  │ 📋     │  │ ⭐     │  │ 👤     │     │      │
│     │  │Escanear│  │Historial│  │Favoritos│ │ Perfil │     │      │
│     │  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘     │      │
│     └──────┼────────────┼──────────┼────────────┼──────────┘      │
│            │            │          │            │                   │
│            ▼            ▼          ▼            ▼                   │
│     ┌──────────┐  ┌─────────┐ ┌────────┐ ┌──────────────┐        │
│     │  Camera  │  │ Session │ │ Saved  │ │  Perfil      │        │
│     │  View    │  │ List    │ │ Recipes│ │  ├─ Salud    │        │
│     │  ├─ Live │  │ ├─ Date │ │ ├─ Tags│ │  ├─ Alergias│        │
│     │  ├─ Scan │  │ ├─ Ingr.│ │ └─ List│ │  ├─ Preferen│        │
│     │  └─ Conf.│  │ └─ Menu │ └────────┘ │  ├─ Config  │        │
│     └────┬─────┘  └─────────┘            │  └─ Datos   │        │
│          │                                 └──────────────┘        │
│          ▼                                                         │
│     ┌──────────┐     ┌───────────┐     ┌──────────────┐          │
│     │ Health   │────▶│   Menu    │────▶│   Recipe     │          │
│     │ Check    │     │ Suggest.  │     │   Detail     │          │
│     │ (Wizard) │     │ Results   │     │              │          │
│     └──────────┘     └───────────┘     └──────────────┘          │
└────────────────────────────────────────────────────────────────────┘
```



### 10.3 Wireflows — Flujo Principal

#### 10.3.1 Flujo de Escaneo y Sugerencia de Menú

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PANTALLA 1: CÁMARA                                                      │
│  ┌───────────────────────────────────────┐                               │
│  │  ┌─────────────────────────────────┐  │                               │
│  │  │                                 │  │                               │
│  │  │      [Vista de cámara]          │  │                               │
│  │  │                                 │  │                               │
│  │  │   ┌─────────┐  ┌──────────┐    │  │                               │
│  │  │   │ 🥑 Palta│  │ 🍗 Pollo │    │  │  ← Bounding boxes en vivo    │
│  │  │   │  94%    │  │   87%    │    │  │                               │
│  │  │   └─────────┘  └──────────┘    │  │                               │
│  │  │                                 │  │                               │
│  │  │         ┌──────────┐            │  │                               │
│  │  │         │ 🥔 Papa  │            │  │                               │
│  │  │         │   91%    │            │  │                               │
│  │  │         └──────────┘            │  │                               │
│  │  └─────────────────────────────────┘  │                               │
│  │                                        │                               │
│  │  Ingredientes detectados: 3            │                               │
│  │  ┌──────┐ ┌──────┐ ┌──────┐          │                               │
│  │  │Palta │ │Pollo │ │Papa  │  [+]     │  ← Chips editables            │
│  │  └──────┘ └──────┘ └──────┘          │                               │
│  │                                        │                               │
│  │  [ 🔄 Seguir escaneando ]             │                               │
│  │  [ ✅ Listo, sugerir menú  ]          │  ← CTA principal              │
│  └───────────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │ Tap "Listo, sugerir menú"
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PANTALLA 2: VERIFICACIÓN DE SALUD (condicional)                         │
│  ┌───────────────────────────────────────┐                               │
│  │                                        │                               │
│  │  ⚠️  Antes de sugerirte un menú...    │                               │
│  │                                        │                               │
│  │  Detectamos ingredientes que pueden    │                               │
│  │  causar reacciones. Queremos estar     │                               │
│  │  seguros.                              │                               │
│  │                                        │                               │
│  │  ¿Tienes alguna alergia alimentaria?  │                               │
│  │                                        │                               │
│  │  ○ No, ninguna                         │                               │
│  │  ○ Sí (seleccionar)                   │                               │
│  │    ┌────────────────────────────┐      │                               │
│  │    │ □ Frutos secos  □ Mariscos │      │                               │
│  │    │ □ Lácteos       □ Huevos   │      │                               │
│  │    │ □ Gluten        □ Soya     │      │                               │
│  │    │ □ Otro: [___________]      │      │                               │
│  │    └────────────────────────────┘      │                               │
│  │                                        │                               │
│  │  ━━━━━━━━━●━━━━━ Paso 1 de 3          │  ← Progreso                  │
│  │                                        │                               │
│  │  [ Omitir ]        [ Siguiente → ]    │                               │
│  └───────────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │ Completa wizard o lo omite
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PANTALLA 3: SUGERENCIAS DE MENÚ                                         │
│  ┌───────────────────────────────────────┐                               │
│  │                                        │                               │
│  │  🍽️  Menús sugeridos                  │                               │
│  │  Con: Palta, Pollo, Papa              │                               │
│  │                                        │                               │
│  │  ┌─────────────────────────────────┐  │                               │
│  │  │ 🥇 Pollo a la crema con puré   │  │                               │
│  │  │ ⏱️ 45 min  ⭐ Fácil  📊 92%   │  │  ← % match ingredientes      │
│  │  │ Ingredientes: ✅ Pollo ✅ Papa  │  │                               │
│  │  │              ✅ Palta  ❌ Crema │  │  ← Faltante señalado         │
│  │  │ [ Ver receta ]  [ ❤️ ]  [ ✕ ]  │  │                               │
│  │  └─────────────────────────────────┘  │                               │
│  │                                        │                               │
│  │  ┌─────────────────────────────────┐  │                               │
│  │  │ 🥈 Ensalada de pollo y palta   │  │                               │
│  │  │ ⏱️ 20 min  ⭐ Fácil  📊 100%  │  │                               │
│  │  │ Ingredientes: ✅ Todos disponib.│  │                               │
│  │  │ [ Ver receta ]  [ ❤️ ]  [ ✕ ]  │  │                               │
│  │  └─────────────────────────────────┘  │                               │
│  │                                        │                               │
│  │  ┌─────────────────────────────────┐  │                               │
│  │  │ 🥉 Causa rellena de pollo      │  │                               │
│  │  │ ⏱️ 60 min  ⭐ Medio  📊 85%   │  │                               │
│  │  │ [ Ver receta ]  [ ❤️ ]  [ ✕ ]  │  │                               │
│  │  └─────────────────────────────────┘  │                               │
│  │                                        │                               │
│  │  [ 🔄 Más sugerencias ]              │                               │
│  └───────────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```



### 10.4 Estados de la Interfaz

#### 10.4.1 Estados de la Pantalla de Cámara

| Estado | Visual | Comportamiento |
|--------|--------|---------------|
| **Inicializando** | Spinner + "Preparando cámara..." | Cargando permisos y modelo ML |
| **Listo para escanear** | Vista de cámara con overlay guía | Texto: "Apunta a tus ingredientes" |
| **Detectando** | Bounding boxes animados sobre ingredientes | Actualización en tiempo real (~5-10 FPS) |
| **Ingrediente confirmado** | Chip verde añadido a la barra inferior | Haptic feedback suave |
| **Sin detección** | Mensaje contextual tras 5s sin resultados | "Acerca la cámara o mejora la iluminación" |
| **Error de cámara** | Pantalla de error con acción de retry | "No se puede acceder a la cámara" + configuración |
| **Permiso denegado** | Explicación + botón a ajustes del SO | Explicar por qué se necesita el permiso |

#### 10.4.2 Estados del Wizard de Salud

| Estado | Visual | Comportamiento |
|--------|--------|---------------|
| **Primera vez** | Wizard completo (5 pasos) | Amigable, explicativo, omitible |
| **Perfil incompleto** | Pregunta contextual inline (1 pregunta) | No intrusivo, descartable |
| **Perfil completo** | No se muestra; paso directo a menú | Accesible desde configuración |
| **Ingrediente riesgoso detectado** | Alert inline con opción de revisar perfil | "Detectamos X, ¿seguro que no tienes alergia?" |

#### 10.4.3 Estados de Resultados de Menú

| Estado | Visual | Comportamiento |
|--------|--------|---------------|
| **Cargando** | Skeleton cards animadas | "Buscando las mejores recetas..." |
| **Resultados exitosos** | Cards de recetas ordenadas por score | Mínimo 3 opciones |
| **Sin resultados** | Empty state amigable | "No encontramos recetas. ¿Agregar ingredientes?" |
| **Resultados filtrados por salud** | Badge de seguridad | "Excluimos X recetas por tus restricciones" |
| **Error de red (solo para sync)** | Resultados locales + aviso | "Mostrando recetas offline. Conecta para más opciones" |

### 10.5 Sistema de Diseño Visual

#### 10.5.1 Paleta de Colores

| Token | Valor | Uso |
|-------|-------|-----|
| `--color-primary` | `#4CAF50` (Green 500) | Acciones principales, confirmaciones, ingredientes detectados |
| `--color-secondary` | `#FF9800` (Orange 500) | Warnings, elementos de atención, timer |
| `--color-error` | `#F44336` (Red 500) | Errores, alertas de alérgenos, eliminar |
| `--color-surface` | `#FFFFFF` / `#121212` (dark) | Fondos de cards y superficies |
| `--color-on-surface` | `#212121` / `#E0E0E0` (dark) | Texto principal |
| `--color-allergen-warning` | `#D32F2F` (Red 700) | Señalización de alérgenos presentes |
| `--color-safe` | `#2E7D32` (Green 800) | Ingrediente seguro confirmado |

#### 10.5.2 Tipografía

| Nivel | Font | Size | Weight | Uso |
|-------|------|------|--------|-----|
| H1 | Inter | 28sp | Bold | Título de pantalla |
| H2 | Inter | 22sp | SemiBold | Secciones principales |
| H3 | Inter | 18sp | Medium | Subtítulos, nombre de receta |
| Body1 | Inter | 16sp | Regular | Texto principal, descripciones |
| Body2 | Inter | 14sp | Regular | Texto secundario, metadata |
| Caption | Inter | 12sp | Regular | Labels, timestamps, % confianza |
| Button | Inter | 14sp | SemiBold | Texto de botones |

#### 10.5.3 Spacing y Layout

| Token | Valor | Uso |
|-------|-------|-----|
| `--spacing-xs` | 4dp | Separación entre chips |
| `--spacing-sm` | 8dp | Padding interno de componentes pequeños |
| `--spacing-md` | 16dp | Padding de cards, separación entre secciones |
| `--spacing-lg` | 24dp | Márgenes de pantalla |
| `--spacing-xl` | 32dp | Separación entre bloques principales |
| `--radius-sm` | 8dp | Chips, botones pequeños |
| `--radius-md` | 12dp | Cards, inputs |
| `--radius-lg` | 16dp | Bottom sheets, modals |



### 10.6 Accesibilidad (WCAG 2.1 AA)

#### 10.6.1 Requisitos de Accesibilidad

| Criterio WCAG | Nivel | Implementación en MenuAI |
|---------------|-------|--------------------------|
| 1.1.1 Contenido no textual | A | Alt-text para todas las imágenes; labels en bounding boxes legibles por screen reader |
| 1.3.1 Info y relaciones | A | Estructura semántica correcta; roles ARIA en componentes custom |
| 1.4.3 Contraste mínimo | AA | Ratio ≥ 4.5:1 para texto normal; ≥ 3:1 para texto grande |
| 1.4.11 Contraste no textual | AA | Iconos y controles con contraste ≥ 3:1 contra fondo |
| 2.1.1 Teclado | A | Toda funcionalidad accesible sin touch (para dispositivos con teclado externo) |
| 2.4.3 Orden de foco | A | Orden lógico de navegación: cámara → ingredientes → CTA |
| 2.5.1 Gestos de puntero | A | No depender de gestos complejos; alternativas de tap disponibles |
| 3.3.1 Identificación de errores | A | Errores identificados claramente con texto (no solo color) |
| 3.3.2 Etiquetas o instrucciones | A | Todos los inputs con label visible y placeholder descriptivo |
| 4.1.2 Nombre, función, valor | A | Componentes custom con semantics correctos para TalkBack/VoiceOver |

#### 10.6.2 Consideraciones Específicas de Accesibilidad

| Funcionalidad | Desafío | Solución |
|---------------|---------|----------|
| Detección por cámara | Usuarios con discapacidad visual | Feedback por audio/vibración: "Se detectaron 3 ingredientes: palta, pollo, papa" |
| Bounding boxes | No perceptibles sin visión | Anuncio por voice-over al detectar nuevo ingrediente |
| Wizard de salud | Formularios complejos | Progresión paso a paso; resumen por voz; agrupación lógica |
| Resultados de menú | Mucha información por card | Jerarquía de lectura definida; expandir/colapsar detalles |
| Alertas de alérgenos | Criticidad del mensaje | Vibración + sonido + visual + texto descriptivo (multi-canal) |

### 10.7 Patrones de Interacción

#### 10.7.1 Micro-interacciones

| Acción | Feedback | Duración |
|--------|----------|----------|
| Ingrediente detectado | Haptic tick + chip aparece con scale animation | 200ms |
| Ingrediente eliminado | Chip se desvanece + haptic light | 150ms |
| Menú cargado exitosamente | Cards aparecen con stagger animation (una tras otra) | 300ms entre cards |
| Alérgeno detectado | Vibración fuerte + badge rojo pulse animation | 500ms + persistente |
| Favorito guardado | Corazón se llena con bounce + confetti sutil | 400ms |
| Escaneo completado | Checkmark animado + transition a siguiente pantalla | 600ms |

#### 10.7.2 Gestos Soportados

| Gesto | Acción | Contexto |
|-------|--------|----------|
| Tap | Acción principal del elemento | Universal |
| Long press | Opciones contextuales | Cards de receta, chips de ingrediente |
| Swipe left | Descartar sugerencia | Card de menú sugerido |
| Swipe right | Guardar en favoritos | Card de menú sugerido |
| Pull to refresh | Recargar sugerencias | Lista de resultados |
| Pinch to zoom | Zoom en imagen de receta | Pantalla de detalle |
| Double tap | Quick favorite | Card de receta |

### 10.8 Responsive Design y Adaptabilidad

| Breakpoint | Dispositivo | Adaptación |
|-----------|-------------|------------|
| < 360dp | Teléfonos pequeños | Layout compacto; menos texto en chips; scroll horizontal |
| 360-411dp | Teléfonos estándar | Layout base optimizado |
| 412-599dp | Teléfonos grandes / phablets | Cards más amplias; 2 columnas en favoritos |
| ≥ 600dp | Tablets | Vista split: cámara izquierda + resultados derecha; grid 2-3 columnas |

### 10.9 Onboarding (Primera Experiencia)

```
┌─── FLUJO ONBOARDING (máx. 60 segundos) ──────────────────────┐
│                                                                │
│  [Pantalla 1] ── "Muestra tus ingredientes"                  │
│  Animación: usuario apuntando cámara a ingredientes           │
│  Tiempo: 3s auto-advance o tap                                │
│                                                                │
│  [Pantalla 2] ── "Te cuidamos"                                │
│  Animación: shield icon + check marks en restricciones        │
│  Texto: "Respetamos tus alergias y preferencias"              │
│  Tiempo: 3s auto-advance o tap                                │
│                                                                │
│  [Pantalla 3] ── "Recetas para ti"                            │
│  Animación: card de receta personalizándose                   │
│  Texto: "Menús hechos a tu medida"                            │
│  Tiempo: 3s auto-advance o tap                                │
│                                                                │
│  [CTA Final] ── [ Empezar ] / [ Configurar perfil primero ]  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---


## 11. Seguridad, Privacidad y Consideraciones OSINT

> Esta sección aborda la seguridad del sistema desde múltiples perspectivas: protección de datos personales y de salud, mitigación de amenazas (OWASP), evaluación de exposición mediante técnicas OSINT, y cumplimiento regulatorio (GDPR/LGPD).

### 11.1 Clasificación de Datos

| Categoría | Ejemplos | Nivel de Sensibilidad | Tratamiento |
|-----------|----------|----------------------|-------------|
| **Datos de identidad** | Nombre, email, foto de perfil | MEDIO | Cifrado en reposo; mínimo necesario |
| **Datos de salud** | Alergias, intolerancias, condiciones médicas | **CRÍTICO** (GDPR Art. 9 — categoría especial) | Cifrado AES-256; almacenamiento local preferente; consentimiento explícito |
| **Imágenes de cámara** | Frames capturados para detección | ALTO (metadatos potenciales) | **NUNCA persisten**; procesadas en memoria y descartadas |
| **Datos de uso** | Historial de menús, favoritos, preferencias | BAJO-MEDIO | Pseudonimizados para analytics; usuario puede eliminar |
| **Datos del modelo** | Pesos del modelo ML, configuración | BAJO (público por diseño) | No contiene datos personales; proteger IP comercial |
| **Metadatos de dispositivo** | Device ID, OS version, RAM | BAJO | Solo para debugging/compatibilidad; anonimizados |

### 11.2 Análisis de Amenazas (Threat Modeling — STRIDE)

```
┌─────────────────── MODELO DE AMENAZAS STRIDE ─────────────────────┐
│                                                                    │
│  SUPERFICIE DE ATAQUE                                             │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  [Dispositivo] ←→ [Red] ←→ [Backend] ←→ [Base Datos]   │     │
│  │       │                        │              │          │     │
│  │       ▼                        ▼              ▼          │     │
│  │  • Modelo ML local       • API Gateway    • Recetas DB  │     │
│  │  • Base local cifrada    • Auth Service   • User DB     │     │
│  │  • Cámara/Sensores       • Recipe Service              │     │
│  └──────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

| Amenaza (STRIDE) | Vector | Impacto | Probabilidad | Mitigación |
|------------------|--------|---------|--------------|------------|
| **S**poofing (Suplantación) | Sesión robada; API key expuesta | Alto | Media | OAuth 2.0 + refresh tokens cortos; certificate pinning |
| **T**ampering (Manipulación) | Modificar modelo ML en dispositivo; interceptar API calls | Alto | Baja | Firma digital del modelo; TLS 1.3; integridad de binarios |
| **R**epudiation (Repudio) | Usuario niega haber configurado restricción de salud | Medio | Baja | Audit log local de cambios en perfil de salud con timestamp |
| **I**nformation Disclosure (Fuga) | Leak de datos de salud; imágenes capturadas | **Crítico** | Media | Cifrado E2E; imágenes nunca persisten; data minimization |
| **D**enial of Service (DoS) | Flooding al backend; crash del modelo con input malicioso | Medio | Media | Rate limiting; input validation; model robustness testing |
| **E**levation of Privilege (Escalada) | Acceso a perfil de salud de otro usuario | **Crítico** | Baja | Aislamiento de datos por usuario; autenticación fuerte; RBAC |



### 11.3 Evaluación OSINT (Open Source Intelligence)

> Las técnicas OSINT se aplican en dos dimensiones: (1) evaluar qué información del usuario/sistema podría ser recopilada por atacantes a partir de fuentes abiertas, y (2) asegurar que la aplicación no exponga involuntariamente datos que faciliten ataques.

#### 11.3.1 Superficie de Exposición OSINT — ¿Qué podría descubrir un atacante?

| Fuente OSINT | Información Expuesta Potencial | Riesgo | Mitigación |
|--------------|-------------------------------|--------|------------|
| **App Store / Play Store** | Stack tecnológico (via metadata de APK), versiones, permisos solicitados | Bajo | Minimizar permisos; ofuscar código (ProGuard/R8) |
| **APK/IPA Reverse Engineering** | Endpoints de API, claves hardcodeadas, estructura del modelo ML | Alto | No hardcodear secrets; ofuscación; server-side API keys |
| **Network Traffic Analysis** | Patrones de uso, endpoints de backend, tamaño de payloads | Medio | Certificate pinning; TLS 1.3; payload padding |
| **Public Code Repos (GitHub)** | Credenciales expuestas, lógica de negocio, vulnerabilidades | **Crítico** | Secret scanning; .gitignore robusto; pre-commit hooks |
| **DNS/Subdomain Enumeration** | Infraestructura del backend, servicios expuestos | Medio | Minimizar subdominios públicos; WAF; no exponer servicios internos |
| **Social Engineering** | Datos del equipo de desarrollo (LinkedIn, etc.) | Medio | Security awareness training; MFA en todas las cuentas |
| **Metadata de imágenes (EXIF)** | Ubicación GPS, modelo de dispositivo, timestamp | Alto | Stripping completo de EXIF antes de cualquier procesamiento |
| **Error Messages / Stack Traces** | Tecnología interna, rutas de archivos, versiones | Medio | Mensajes genéricos en producción; logging interno sin exposición |

#### 11.3.2 Contramedidas OSINT Implementadas

```
┌─────────────── CAPAS DE PROTECCIÓN CONTRA OSINT ──────────────────┐
│                                                                    │
│  CAPA 1: CÓDIGO FUENTE                                            │
│  ├─ Secret scanning en CI/CD (GitLeaks, TruffleHog)              │
│  ├─ .gitignore exhaustivo (keys, .env, modelos locales)          │
│  ├─ Pre-commit hooks que bloquean secrets                         │
│  └─ Variables de entorno para toda configuración sensible         │
│                                                                    │
│  CAPA 2: APLICACIÓN COMPILADA                                     │
│  ├─ Ofuscación de código (ProGuard/R8 para Android)              │
│  ├─ Bitcode + strip symbols (iOS)                                │
│  ├─ No incluir debug symbols en release builds                   │
│  ├─ Integridad de la app (SafetyNet/App Attest)                  │
│  └─ Detección de root/jailbreak                                  │
│                                                                    │
│  CAPA 3: COMUNICACIONES                                           │
│  ├─ Certificate pinning (backup pins incluidos)                  │
│  ├─ TLS 1.3 exclusivo (no fallback a versiones antiguas)         │
│  ├─ No incluir versiones de software en headers HTTP             │
│  └─ Randomizar tamaño de payloads (padding)                      │
│                                                                    │
│  CAPA 4: INFRAESTRUCTURA                                          │
│  ├─ Servicios internos no expuestos a internet                   │
│  ├─ WAF con reglas anti-fingerprinting                           │
│  ├─ Rate limiting por IP y por usuario                           │
│  └─ DNS: no usar subdominios descriptivos (no "ml-api.domain")  │
│                                                                    │
│  CAPA 5: DATOS DEL USUARIO                                        │
│  ├─ EXIF stripping automático de toda imagen procesada           │
│  ├─ No almacenar imágenes (procesamiento in-memory only)         │
│  ├─ Pseudonimización de analytics                                │
│  └─ Derecho al olvido implementado (borrado completo)            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 11.3.3 OSINT como Herramienta Defensiva

| Actividad OSINT Propia | Frecuencia | Propósito |
|------------------------|-----------|-----------|
| Búsqueda de credenciales expuestas (GitHub, Pastebin) | Semanal (automatizado) | Detectar leaks antes que atacantes |
| Escaneo de subdominios/servicios propios | Mensual | Verificar superficie de ataque mínima |
| Análisis de APK propia (como atacante) | Cada release | Verificar que no hay secrets o rutas expuestas |
| Monitoreo de menciones de la marca/producto | Continuo | Detectar campañas de phishing que usen nuestra marca |
| Revisión de dependencias públicas (SBOM) | En cada build | Detectar vulnerabilidades conocidas en librerías |



### 11.4 Seguridad del Modelo ML (OWASP ML Top 10)

| # OWASP ML | Amenaza | Aplicación en MenuAI | Mitigación |
|------------|---------|---------------------|------------|
| ML01 | Input Manipulation (Adversarial) | Imagen manipulada para forzar detección incorrecta | Input validation; confidence threshold alto (0.7); usuario confirma |
| ML02 | Data Poisoning | Dataset contaminado con labels incorrectos | Revisión cruzada de anotaciones; trazabilidad de datos; validación estadística |
| ML03 | Model Inversion | Recuperar datos de entrenamiento desde el modelo | Modelo no contiene datos de usuarios; differential privacy en training |
| ML04 | Membership Inference | Determinar si un dato específico fue usado en training | Dataset no contiene datos personales (solo imágenes de alimentos genéricos) |
| ML05 | Model Theft | Extraer/copiar el modelo del dispositivo | Cifrado del modelo en reposo; ofuscación; detección de tampering |
| ML06 | AI Supply Chain | Dependencias ML comprometidas (PyTorch, TFLite) | SBOM; verificación de hashes; pinning de versiones |
| ML07 | Transfer Learning Attack | Pre-trained model con backdoor | Usar solo modelos de fuentes confiables (Ultralytics oficial); fine-tune validation |
| ML08 | Model Skewing | Drift entre training y producción | Monitoreo continuo de métricas; alertas automáticas |
| ML09 | Output Integrity | Manipulación de resultados post-inferencia | Validación de outputs; checksums en pipeline |
| ML10 | Model DoS | Inputs diseñados para maximizar latencia/consumo | Timeout de inferencia; input size limits; resource caps |

### 11.5 Privacidad por Diseño (Privacy by Design — 7 Principios)

| # | Principio | Implementación en MenuAI |
|---|-----------|--------------------------|
| 1 | **Proactivo, no reactivo** | Análisis de privacidad desde diseño; DPIA realizado antes de desarrollo |
| 2 | **Privacidad como configuración predeterminada** | Sync desactivado por defecto; analytics opt-in; mínimo de datos recolectados |
| 3 | **Privacidad integrada en el diseño** | Cifrado, data minimization y retention policies son parte de la arquitectura, no add-ons |
| 4 | **Funcionalidad total (positive-sum)** | Privacidad no degrada funcionalidad; inferencia local = privado + rápido |
| 5 | **Seguridad end-to-end** | Datos protegidos durante todo el ciclo de vida (creación → almacenamiento → eliminación) |
| 6 | **Visibilidad y transparencia** | Privacy policy clara; usuario puede ver todos sus datos; export en formato legible |
| 7 | **Respeto por el usuario** | Configuración granular; revocación de consentimiento; borrado efectivo |

### 11.6 Cumplimiento Regulatorio

#### 11.6.1 GDPR / LGPD — Derechos del Usuario

| Derecho | Implementación Técnica |
|---------|----------------------|
| **Acceso** (Art. 15) | Endpoint GET `/user/data-export` genera JSON con todos los datos del usuario |
| **Rectificación** (Art. 16) | UI de edición de perfil; API PUT para todos los campos |
| **Supresión** (Art. 17) | Botón "Eliminar mi cuenta"; cascade delete en todas las tablas; confirmar eliminación de backup |
| **Portabilidad** (Art. 20) | Exportación en formato JSON/CSV estándar y legible por máquina |
| **Oposición** (Art. 21) | Opt-out de analytics y personalización; funcionalidad core sigue operativa |
| **Limitación** (Art. 18) | Capacidad de "congelar" procesamiento sin borrar datos |
| **Consentimiento** (Art. 7) | Consentimiento granular por propósito; revocable; registro con timestamp |

#### 11.6.2 Datos de Salud — Protecciones Adicionales

```
┌─────────── FLUJO DE DATOS DE SALUD ──────────────────────────────┐
│                                                                    │
│  RECOLECCIÓN                                                       │
│  ├─ Consentimiento explícito + informado (no pre-checked)         │
│  ├─ Explicación del propósito ("para no sugerirte recetas         │
│  │   que puedan causar reacción alérgica")                        │
│  └─ Opción de no proveer (funcionalidad reducida, no bloqueada)  │
│                                                                    │
│  ALMACENAMIENTO                                                    │
│  ├─ Local-first: datos de salud en dispositivo por defecto       │
│  ├─ Cifrado AES-256-GCM con key derivada de biometría/PIN       │
│  ├─ Backup cifrado a cloud solo con opt-in explícito             │
│  └─ Segregación: DB separada para datos de salud (no mezclada)   │
│                                                                    │
│  PROCESAMIENTO                                                     │
│  ├─ Solo en dispositivo (filtrado de recetas es local)           │
│  ├─ Nunca se envía perfil de salud al backend                    │
│  └─ Analytics: solo contadores agregados, nunca datos individuales│
│                                                                    │
│  RETENCIÓN                                                         │
│  ├─ Mientras el usuario mantenga la cuenta activa                │
│  ├─ Auto-delete de datos tras 24 meses de inactividad (warning) │
│  └─ Eliminación inmediata al solicitar borrado de cuenta         │
│                                                                    │
│  ELIMINACIÓN                                                       │
│  ├─ Secure delete (overwrite, no solo unlink)                    │
│  ├─ Propagación a backups en ≤ 30 días                           │
│  └─ Confirmación al usuario de eliminación completa              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 11.7 OWASP Mobile Top 10 — Mitigaciones

| # | Riesgo | Mitigación en MenuAI |
|---|--------|---------------------|
| M1 | Uso inadecuado de credenciales | No almacenar passwords localmente; tokens con TTL corto; biometría |
| M2 | Seguridad de supply chain | SBOM; dependabot; auditoría de paquetes; lockfiles |
| M3 | Autenticación/autorización insegura | OAuth 2.0 + PKCE; refresh token rotation; session management |
| M4 | Validación insuficiente de input/output | Schema validation en API; sanitización de inputs; output encoding |
| M5 | Comunicación insegura | TLS 1.3; certificate pinning; no HTTP fallback |
| M6 | Privacy controls inadecuados | Privacy by Design; data minimization; consentimiento granular |
| M7 | Binary protections insuficientes | Ofuscación; anti-tampering; detección de debug/root |
| M8 | Security misconfiguration | Hardening de backend; secure defaults; automated security scans |
| M9 | Almacenamiento inseguro de datos | Encrypted SharedPreferences; Keystore/Keychain; no datos en external storage |
| M10 | Criptografía insuficiente | AES-256-GCM; no algoritmos deprecados; key management robusto |

---


## 12. Buenas Prácticas de Desarrollo

### 12.1 Estructura del Proyecto (Clean Architecture)

```
menuai/
├── lib/
│   ├── main.dart                          # Entry point + DI setup
│   ├── app/                               # App-level config (routing, theme, localization)
│   │   ├── router.dart
│   │   ├── theme.dart
│   │   └── localization/
│   │
│   ├── core/                              # Shared utilities y base classes
│   │   ├── error/                         # Failure classes, exceptions
│   │   ├── network/                       # Network info, API client base
│   │   ├── utils/                         # Extensions, helpers
│   │   └── constants/                     # App-wide constants
│   │
│   ├── features/                          # Feature-first organization
│   │   ├── ingredient_detection/
│   │   │   ├── domain/                    # Entities, Use Cases, Ports (abstractions)
│   │   │   │   ├── entities/
│   │   │   │   ├── usecases/
│   │   │   │   └── repositories/          # Abstract repository interfaces
│   │   │   ├── data/                      # Adapters (implementations)
│   │   │   │   ├── models/                # DTOs, data models
│   │   │   │   ├── datasources/           # ML runtime, camera SDK
│   │   │   │   └── repositories/          # Concrete implementations
│   │   │   └── presentation/              # UI + State Management
│   │   │       ├── screens/
│   │   │       ├── widgets/
│   │   │       └── bloc/                  # BLoC/Cubit state management
│   │   │
│   │   ├── health_profile/
│   │   │   ├── domain/
│   │   │   ├── data/
│   │   │   └── presentation/
│   │   │
│   │   ├── menu_suggestion/
│   │   │   ├── domain/
│   │   │   ├── data/
│   │   │   └── presentation/
│   │   │
│   │   └── history/
│   │       ├── domain/
│   │       ├── data/
│   │       └── presentation/
│   │
│   └── di/                                # Dependency injection modules
│       ├── injection_container.dart
│       └── modules/
│
├── test/
│   ├── unit/                              # Tests unitarios por feature
│   ├── integration/                       # Tests de integración
│   ├── widget/                            # Tests de widgets/UI
│   ├── e2e/                               # Tests end-to-end
│   ├── fixtures/                          # Datos de prueba
│   └── mocks/                             # Mocks generados (Mockito)
│
├── assets/
│   ├── models/                            # Modelos ML (TFLite)
│   ├── images/
│   ├── fonts/
│   └── i18n/                              # Archivos de traducción
│
├── ml/                                    # Pipeline ML (separado del mobile)
│   ├── notebooks/                         # Jupyter notebooks de exploración
│   ├── src/
│   │   ├── data/                          # Scripts de procesamiento de datos
│   │   ├── training/                      # Scripts de entrenamiento
│   │   ├── evaluation/                    # Scripts de evaluación
│   │   └── export/                        # Scripts de conversión/exportación
│   ├── configs/                           # Hiperparámetros, configs de training
│   ├── tests/                             # Tests del pipeline ML
│   └── dvc.yaml                           # Pipeline DVC
│
├── docs/                                  # Documentación del proyecto
│   ├── architecture/                      # ADRs, diagramas
│   ├── api/                               # Documentación de API
│   └── runbooks/                          # Guías operacionales
│
├── .github/
│   ├── workflows/                         # CI/CD pipelines
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│
├── pubspec.yaml                           # Dependencias Flutter
├── analysis_options.yaml                  # Linting rules
├── .env.example                           # Template de variables de entorno
└── Makefile                               # Comandos comunes simplificados
```



### 12.2 CI/CD Pipeline

```
┌─────────────────────── CI/CD PIPELINE ────────────────────────────┐
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  TRIGGER: Push a branch / Pull Request                       │  │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│                             ▼                                      │
│  ┌─────────────────── STAGE 1: QUALITY ───────────────────────┐   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │  Lint    │  │  Format  │  │ Analyze  │  │  Secret  │  │   │
│  │  │ (dart    │  │ (dart    │  │ (custom  │  │  Scan    │  │   │
│  │  │  analyze)│  │  format) │  │  rules)  │  │(gitleaks)│  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │   │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                             │ ✅ Pass                              │
│                             ▼                                      │
│  ┌─────────────────── STAGE 2: TEST ──────────────────────────┐   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │  Unit    │  │  Widget  │  │  Integr. │  │ Coverage │  │   │
│  │  │  Tests   │  │  Tests   │  │  Tests   │  │  Report  │  │   │
│  │  │          │  │          │  │          │  │  (≥80%)  │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │   │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                             │ ✅ Pass                              │
│                             ▼                                      │
│  ┌─────────────────── STAGE 3: SECURITY ──────────────────────┐   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │   │
│  │  │  SAST    │  │  Dep.    │  │  License │                 │   │
│  │  │ (Semgrep)│  │  Audit   │  │  Check   │                 │   │
│  │  │          │  │(OSV/Snyk)│  │          │                 │   │
│  │  └──────────┘  └──────────┘  └──────────┘                 │   │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                             │ ✅ Pass                              │
│                             ▼                                      │
│  ┌─────────────────── STAGE 4: BUILD ─────────────────────────┐   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │   │
│  │  │  Build APK   │  │  Build IPA   │  │  Size Analysis  │  │   │
│  │  │  (Release)   │  │  (Release)   │  │  (< 150MB)      │  │   │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │   │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                             │ ✅ Pass (solo en merge a main)       │
│                             ▼                                      │
│  ┌─────────────────── STAGE 5: DEPLOY ────────────────────────┐   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │   │
│  │  │  Deploy to   │  │  Deploy to   │  │  Notify Team    │  │   │
│  │  │  TestFlight  │  │  Internal    │  │  (Slack/Teams)  │  │   │
│  │  │  / Firebase  │  │  Track       │  │                 │  │   │
│  │  │  App Distrib.│  │  (Play Store)│  │                 │  │   │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 12.3 Estrategia de Testing

#### 12.3.1 Pirámide de Tests

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲         ← 5-10 tests críticos (flujo completo)
                 ╱______╲
                ╱        ╲
               ╱Integration╲    ← ~50 tests (repositorios, servicios, BLoC)
              ╱____________╲
             ╱              ╲
            ╱   Unit Tests   ╲  ← ~200+ tests (entities, use cases, utils)
           ╱__________________╲
```

#### 12.3.2 Tipos de Test por Capa

| Capa | Tipo de Test | Qué se Prueba | Herramientas |
|------|-------------|---------------|--------------|
| **Domain** | Unit | Lógica de negocio pura; use cases; validaciones | `test`, `mockito` |
| **Data** | Unit + Integration | Serialización; mapeo de modelos; repository con mocks | `test`, `mockito`, `fake_async` |
| **Presentation** | Widget + Unit | Renderizado correcto; interacciones; estados del BLoC | `flutter_test`, `bloc_test` |
| **ML Pipeline** | Unit + Integration | Preprocessing; postprocessing; métricas del modelo | `pytest`, `numpy testing` |
| **E2E** | Integration | Flujo completo: escanear → perfil → menú sugerido | `integration_test`, `patrol` |

#### 12.3.3 Tests Específicos para ML

| Test | Propósito | Criterio de Éxito |
|------|-----------|-------------------|
| Model accuracy test | Validar mAP en test set tras export | mAP@0.5 ≥ 85% |
| Quantization regression | Comparar modelo original vs. quantizado | Degradación < 2% mAP |
| Latency benchmark | Medir tiempo de inferencia en device target | P95 < 2s |
| Input boundary test | Inputs extremos (imagen negra, blanca, ruido) | No crash; retorna lista vacía |
| Memory leak test | Inferencia repetida (100x) sin memory growth | Delta memoria < 10MB |



### 12.4 Versionamiento y Git Workflow

#### 12.4.1 Branching Strategy (Git Flow Simplificado)

```
main ─────────●────────────────●────────────────●──── (releases estables)
              │                │                │
              │   release/1.0 ─┤   release/1.1 ─┤
              │                │                │
develop ──●───┼──●──●──●──────┼──●──●──────────┼──── (integración)
           │  │  │  │  │      │  │  │
           │  │  │  │  │      │  │  └─ feature/RF-15-history
           │  │  │  │  └──────│──┘
           │  │  │  └─ feature/RF-08-menu-engine
           │  │  └─── feature/RF-04-allergies
           │  └────── feature/RF-01-detection
           └───────── feature/setup-architecture
```

#### 12.4.2 Convenciones de Commits (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| `feat` | Nueva funcionalidad | `feat(detection): add YOLOv8n inference pipeline` |
| `fix` | Corrección de bug | `fix(health): prevent crash when allergy list is empty` |
| `refactor` | Reestructuración sin cambio funcional | `refactor(menu): extract scoring logic to strategy pattern` |
| `test` | Agregar o modificar tests | `test(detection): add unit tests for NMS post-processor` |
| `docs` | Documentación | `docs(api): update recipe endpoint documentation` |
| `ci` | Cambios en CI/CD | `ci: add model size check to build pipeline` |
| `perf` | Mejora de rendimiento | `perf(inference): enable GPU delegate for TFLite` |
| `security` | Fix de seguridad | `security(auth): rotate exposed API key` |

#### 12.4.3 Code Review Guidelines

| Aspecto | Criterio de Aprobación |
|---------|----------------------|
| **Funcionalidad** | Cumple criterios de aceptación del RF/RNF asociado |
| **Tests** | Incluye tests unitarios para lógica nueva; coverage no disminuye |
| **SOLID** | No introduce acoplamiento innecesario; responsabilidades claras |
| **Seguridad** | No expone secrets; valida inputs; no introduce vulnerabilidades |
| **Performance** | No introduce N+1; no bloquea UI thread; recursos liberados |
| **Naming** | Nombres descriptivos en inglés; consistentes con el dominio |
| **Documentación** | APIs públicas documentadas; ADR si es decisión arquitectónica |

### 12.5 Estándares de Código

#### 12.5.1 Linting y Formato

```yaml
# analysis_options.yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  strong-mode:
    implicit-casts: false
    implicit-dynamic: false
  errors:
    missing_return: error
    dead_code: warning

linter:
  rules:
    - always_declare_return_types
    - avoid_print
    - avoid_relative_lib_imports
    - prefer_const_constructors
    - prefer_final_locals
    - require_trailing_commas
    - sort_constructors_first
    - unawaited_futures
    - unnecessary_await_in_return
```

#### 12.5.2 Convenciones de Naming

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Clases | PascalCase | `IngredientDetector`, `HealthProfile` |
| Archivos | snake_case | `ingredient_detector.dart`, `health_profile.dart` |
| Variables / funciones | camelCase | `detectedIngredients`, `generateMenu()` |
| Constantes | lowerCamelCase (con `const`) | `const maxDetectionCount = 10;` |
| Enums | PascalCase + values camelCase | `enum Severity { mild, moderate, severe }` |
| Private | Prefijo `_` | `_confidenceThreshold`, `_processFrame()` |
| Interfaces/Ports | Sufijo descriptivo | `IngredientDetectorPort`, `RecipeRepositoryPort` |
| Implementations | Sufijo `Impl` o prefijo tecnología | `TFLiteIngredientDetector`, `SQLiteHealthRepo` |
| BLoC Events | PascalCase + verbo | `IngredientsDetected`, `MenuRequested` |
| BLoC States | PascalCase + adjetivo/estado | `DetectionInProgress`, `MenuLoaded` |

### 12.6 Gestión de Dependencias

#### 12.6.1 Políticas de Dependencias

| Política | Regla |
|----------|-------|
| **Actualización** | Dependabot semanal; review manual de major versions |
| **Licencias permitidas** | MIT, BSD, Apache 2.0. Prohibidas: GPL, AGPL (en mobile) |
| **Lockfile** | `pubspec.lock` siempre commiteado; `requirements.txt` con pinning exacto (ML) |
| **Evaluación pre-adopción** | Verificar: mantenimiento activo, >500 stars, no vulnerabilidades conocidas, licencia compatible |
| **Dependencias mínimas** | Preferir stdlib cuando sea posible; justificar cada nueva dependencia en PR |

#### 12.6.2 Stack Tecnológico (Dependencies Principales)

| Categoría | Dependencia | Propósito | Versión |
|-----------|-------------|-----------|---------|
| Framework | Flutter | UI cross-platform | ^3.20 |
| State Management | flutter_bloc | Gestión de estado predecible | ^8.x |
| DI | get_it + injectable | Inyección de dependencias | ^7.x |
| ML Runtime | tflite_flutter | Inferencia on-device | ^0.10 |
| Cámara | camera | Acceso a cámara nativa | ^0.11 |
| DB Local | drift (SQLite) | Persistencia estructurada | ^2.x |
| Cifrado | encrypt / flutter_secure_storage | Cifrado de datos sensibles | latest |
| HTTP | dio | Cliente HTTP con interceptors | ^5.x |
| Navigation | go_router | Routing declarativo | ^13.x |
| Testing | mockito, bloc_test | Mocking y testing de BLoC | latest |



### 12.7 Documentación de Código

#### 12.7.1 Niveles de Documentación

| Nivel | Qué Documentar | Formato |
|-------|----------------|---------|
| **Paquete/Feature** | Propósito del módulo, dependencias, cómo usarlo | `README.md` en cada feature |
| **Clase** | Responsabilidad, invariantes, ejemplo de uso | Dartdoc (`///`) en la clase |
| **Método público** | Qué hace, parámetros, retorno, excepciones, ejemplo | Dartdoc con `@param`, `@returns`, `@throws` |
| **Lógica compleja** | Por qué (no qué) — decisiones no obvias | Comentarios inline (`//`) |
| **API** | Endpoints, request/response, errores | OpenAPI 3.0 spec |
| **Arquitectura** | Decisiones significativas | ADR (Architecture Decision Record) |

#### 12.7.2 Template de Documentación de Clase

```dart
/// Servicio responsable de generar sugerencias de menú personalizadas.
///
/// Combina los ingredientes detectados con el catálogo de recetas,
/// filtrando según las restricciones de salud del usuario y ordenando
/// por relevancia (score de match).
///
/// ## Uso
/// ```dart
/// final useCase = GenerateMenuUseCase(detector, health, recipes, scoring);
/// final result = await useCase.execute(ingredients, userId);
/// ```
///
/// ## Principios
/// - No sugiere recetas con ingredientes que violen restricciones de salud
/// - Ante ambigüedad, prioriza seguridad (excluir) sobre variedad (incluir)
/// - Mínimo 3 sugerencias o indica que no hay suficientes ingredientes
///
/// See also:
/// - [HealthRestriction] para el modelo de restricciones
/// - [MenuScoringPort] para el algoritmo de ranking
class GenerateMenuUseCase {
  // ...
}
```

### 12.8 Monitoreo y Observabilidad en Producción

#### 12.8.1 Estrategia de Logging

| Nivel | Cuándo Usar | Ejemplo | Destino |
|-------|-------------|---------|---------|
| `ERROR` | Fallo que afecta funcionalidad del usuario | Model inference crash | Crashlytics + alerta inmediata |
| `WARN` | Situación anómala pero recuperable | Confidence score inusualmente bajo | Logging service + dashboard |
| `INFO` | Eventos de negocio significativos | Menu generated successfully; Profile updated | Analytics pipeline |
| `DEBUG` | Detalle técnico para debugging | Inference time: 1.2s; NMS removed 3 boxes | Solo en builds de debug |

#### 12.8.2 Métricas de Producto (Analytics)

| Métrica | Tipo | Propósito |
|---------|------|-----------|
| Sesiones de escaneo por usuario/día | Counter | Engagement |
| Tasa de éxito de detección | Ratio | Calidad del modelo |
| Tiempo hasta primer menú sugerido | Histogram | Performance UX |
| % de menús aceptados vs. descartados | Ratio | Relevancia de sugerencias |
| Completion rate del health wizard | Funnel | UX del onboarding |
| Ingredientes más escaneados | Top-N | Priorización de dataset |
| Recetas más seleccionadas | Top-N | Content strategy |
| Crash-free sessions | Percentage | Estabilidad (target: >99.5%) |

### 12.9 Estrategia de Release

| Fase | Audiencia | Duración | Criterio de Avance |
|------|-----------|----------|-------------------|
| **Alpha** | Equipo interno | 1-2 semanas | Zero critical bugs; >80% test pass |
| **Beta cerrada** | 50-100 testers invitados | 2-3 semanas | NPS > 7; crash-free > 98% |
| **Beta abierta** | Público opt-in | 2-4 semanas | Crash-free > 99%; feedback incorporado |
| **Release (GA)** | Todos los usuarios | Ongoing | Todas las métricas en target |
| **Hotfix** | Todos (emergencia) | < 24h desde detección | Critical/security fix validado |

### 12.10 Definition of Done (DoD)

Un feature se considera "terminado" cuando cumple TODOS los siguientes criterios:

- [ ] Código implementado siguiendo principios SOLID y estructura Clean Architecture
- [ ] Tests unitarios escritos y pasando (coverage ≥ 80% del nuevo código)
- [ ] Tests de widget/integración para flujos de UI afectados
- [ ] Linting sin warnings ni errors
- [ ] Code review aprobado por al menos 1 peer
- [ ] Documentación de APIs públicas actualizada
- [ ] Sin secrets hardcodeados (verificado por pipeline)
- [ ] Strings externalizados para localización
- [ ] Accesibilidad verificada (labels, contraste, navegación)
- [ ] Performance verificada (no regresiones en métricas clave)
- [ ] ADR creado si incluye decisión arquitectónica significativa
- [ ] Feature flag implementado si es release gradual
- [ ] QA manual de flujo feliz + edge cases principales

---


## 13. Apéndices

### Apéndice A: Catálogo de Ingredientes v1.0

| ID | Ingrediente | Categoría | Alérgenos Asociados | Variantes de Nombre |
|----|-------------|-----------|--------------------|--------------------|
| ING-001 | Palta | Fruta | — | Aguacate, avocado |
| ING-002 | Pollo | Proteína animal | — | Chicken, gallina |
| ING-003 | Papa | Tubérculo | Solanáceas (raro) | Patata, potato |
| ING-004 | Carne de cerdo | Proteína animal | — | Pork, chancho |
| ING-005 | Tomate | Verdura/Fruta | Solanáceas, histamina | Jitomate, tomato |
| ING-006 | Cebolla | Verdura | FODMAP | Onion |
| ING-007 | Ajo | Verdura | FODMAP | Garlic |
| ING-008 | Arroz | Cereal | — | Rice |
| ING-009 | Huevo | Proteína animal | **Huevo (alérgeno mayor)** | Egg |
| ING-010 | Limón | Fruta cítrica | Cítricos | Lemon, lime |
| ING-011 | Zanahoria | Verdura | — | Carrot |
| ING-012 | Pimiento | Verdura | Solanáceas | Bell pepper, ají |
| ING-013 | Brócoli | Verdura crucífera | — | Broccoli |
| ING-014 | Queso | Lácteo | **Lácteo (alérgeno mayor)** | Cheese |
| ING-015 | Leche | Lácteo | **Lácteo (alérgeno mayor)** | Milk |

### Apéndice B: Catálogo de Restricciones de Salud

#### B.1 Alergias (14 Alérgenos Principales — Regulación EU 1169/2011)

| # | Alérgeno | Ingredientes Relacionados |
|---|----------|--------------------------|
| 1 | Gluten | Trigo, cebada, centeno, avena |
| 2 | Crustáceos | Camarón, langosta, cangrejo |
| 3 | Huevos | Huevo, mayonesa, merengue |
| 4 | Pescado | Cualquier especie de pescado |
| 5 | Maní/Cacahuate | Maní, mantequilla de maní |
| 6 | Soya | Soya, tofu, salsa de soya |
| 7 | Lácteos | Leche, queso, yogurt, mantequilla |
| 8 | Frutos de cáscara | Almendra, nuez, avellana, pistacho |
| 9 | Apio | Apio, sal de apio |
| 10 | Mostaza | Mostaza, semillas de mostaza |
| 11 | Sésamo | Semillas de sésamo, tahini |
| 12 | Sulfitos | Vino, frutos secos, vinagre |
| 13 | Altramuces | Lupino, harina de lupino |
| 14 | Moluscos | Mejillón, ostra, calamar, pulpo |

#### B.2 Intolerancias Comunes

| Intolerancia | Sustancia a Evitar | Nivel de Tolerancia Configurable |
|--------------|-------------------|----------------------------------|
| Lactosa | Lactosa en lácteos | Ninguno / Bajo / Moderado |
| Gluten (no celíaco) | Gluten | Ninguno / Bajo |
| Fructosa | Fructosa en frutas/miel | Bajo / Moderado |
| Histamina | Histamina en fermentados | Bajo |
| FODMAP | Oligosacáridos, disacáridos, etc. | Según fase de dieta |

#### B.3 Contraindicaciones Médicas

| Condición | Ingredientes a Limitar/Evitar |
|-----------|------------------------------|
| Diabetes tipo 2 | Alto índice glucémico; azúcares añadidos; harinas refinadas |
| Hipertensión | Sal excesiva; embutidos; enlatados altos en sodio |
| Enfermedad celíaca | Gluten (exclusión total) |
| Gota | Carnes rojas; vísceras; mariscos; alcohol |
| Insuficiencia renal | Potasio alto; fósforo; proteínas excesivas |
| Embarazo | Pescado crudo; embutidos no cocidos; alcohol; cafeína excesiva |

### Apéndice C: Algoritmo de Scoring de Menú (v1)

```
SCORE(receta, ingredientes_detectados, perfil_salud) =
  
  // Factor 1: Match de ingredientes (40% del peso)
  ingredient_match = |ingredientes_receta ∩ ingredientes_detectados| / |ingredientes_receta|
  
  // Factor 2: Seguridad alimentaria (BLOQUEANTE)
  IF any ingrediente_receta violates perfil_salud.restrictions:
      RETURN -1  // Receta excluida completamente
  
  // Factor 3: Complejidad vs. preferencia (20% del peso)
  complexity_match = 1 - |receta.difficulty - perfil.preferred_difficulty| / max_difficulty
  
  // Factor 4: Preferencia de cocina (20% del peso)  
  cuisine_match = receta.cuisine IN perfil.preferred_cuisines ? 1.0 : 0.5
  
  // Factor 5: Historial (20% del peso) — boost o penalización
  history_factor = 
    IF receta fue descartada recientemente: 0.3
    IF receta similar fue aceptada: 1.2
    ELSE: 1.0
  
  // Score final
  FINAL_SCORE = (
    0.40 * ingredient_match +
    0.20 * complexity_match +
    0.20 * cuisine_match +
    0.20 * base_score
  ) * history_factor
  
  RETURN FINAL_SCORE  // Rango [0, 1.2]
```

### Apéndice D: Glosario de Dominio (Ubiquitous Language)

| Término del Dominio | Definición en Contexto MenuAI |
|--------------------|-----------------------------|
| **Sesión de escaneo** | Período desde que el usuario abre la cámara hasta que confirma la lista de ingredientes |
| **Ingrediente detectado** | Item alimentario identificado por el modelo ML con confianza > umbral |
| **Perfil de salud** | Conjunto de restricciones (alergias + intolerancias + contraindicaciones + preferencias) |
| **Menú sugerido** | Conjunto ordenado de recetas que maximizan match con ingredientes y respetan restricciones |
| **Score de match** | Valor numérico [0,1] que indica qué tan compatible es una receta con los ingredientes disponibles |
| **Restricción bloqueante** | Alergia o condición que excluye completamente una receta (no negociable) |
| **Restricción preferencial** | Preferencia dietética que reduce score pero no excluye (negociable) |
| **Drift del modelo** | Degradación gradual de la precisión del modelo por cambios en los datos de entrada |
| **Canary release** | Despliegue gradual a un subconjunto de usuarios para validar antes de release completo |

---

## Historial de Revisiones

| Versión | Fecha | Autor | Cambios |
|---------|-------|-------|---------|
| 1.0.0 | 2026-07-22 | Equipo MenuAI | Documento inicial completo |

---

*Fin del documento — SDD MenuAI v1.0.0*
