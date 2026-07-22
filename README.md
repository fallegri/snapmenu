# SnapMenu 📷🍽️

> **Transforma los ingredientes disponibles en inspiración culinaria personalizada, accesible con solo apuntar la cámara.**

## ¿Qué es SnapMenu?

SnapMenu es una aplicación móvil que utiliza **visión por computadora** y **aprendizaje automático** para:

1. **Detectar ingredientes** a través de la cámara del dispositivo
2. **Preguntar restricciones de salud** (alergias, intolerancias, contraindicaciones)
3. **Sugerir menús personalizados** basados en lo que tienes disponible

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Mobile | Flutter (iOS + Android) |
| ML Model | YOLOv8n (detección de objetos) |
| ML Runtime | TensorFlow Lite (on-device) |
| State Management | flutter_bloc |
| Base de datos local | Drift (SQLite) |
| Backend | Microservicios (Recipe Service) |
| ML Pipeline | Python + Ultralytics + DVC + MLflow |

## Documentación

- 📄 [Especificaciones de Diseño (SDD)](docs/SDD_SnapMenu_Spec.md) — Documento completo de arquitectura y diseño

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                    SnapMenu App                            │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌───────────┐ │
│  │   UI    │  │  ML      │  │ Perfil  │  │  Motor de │ │
│  │  Layer  │  │  Engine  │  │ Salud   │  │  Menú     │ │
│  └─────────┘  └──────────┘  └─────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Estado del Proyecto

- [x] Documento de especificaciones (SDD)
- [ ] Setup del proyecto Flutter
- [ ] Pipeline de entrenamiento ML
- [ ] MVP funcional

## Licencia

Confidencial — Uso Interno
