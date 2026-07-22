# SnapMenu — Contexto del Proyecto

## Descripción
SnapMenu es una app móvil que detecta ingredientes por cámara (ML) y sugiere menús personalizados respetando restricciones de salud del usuario.

## Decisiones Arquitectónicas Clave
- **Framework:** Flutter (cross-platform iOS/Android)
- **Arquitectura:** Clean Architecture + MVVM + Repository Pattern
- **ML Model:** YOLOv8n con TFLite para inferencia on-device
- **State Management:** flutter_bloc (BLoC/Cubit)
- **DI:** get_it + injectable
- **Base de datos local:** Drift (SQLite) con cifrado AES-256 para datos de salud
- **Inferencia:** On-device (edge) — imágenes NUNCA salen del dispositivo

## Principios de Diseño
- SOLID estricto en toda la codebase
- Privacy by Design — datos de salud cifrados y locales
- Offline-first — detección y sugerencia básica funcionan sin red
- Seguridad alimentaria — ante duda, excluir ingrediente/receta

## Estructura del Proyecto
- `lib/features/` — Organización feature-first (ingredient_detection, health_profile, menu_suggestion, history)
- `lib/core/` — Utilities compartidas, error handling, network
- `ml/` — Pipeline de entrenamiento ML (Python)
- `docs/` — Documentación de arquitectura y specs

## Estándares de Código
- Dart: snake_case para archivos, PascalCase para clases, camelCase para variables
- Conventional Commits: feat/fix/refactor/test/docs/ci/perf/security
- Coverage mínimo: 80% unitarios
- Todas las APIs públicas documentadas con Dartdoc

## Referencia Completa
#[[file:docs/SDD_SnapMenu_Spec.md]]
