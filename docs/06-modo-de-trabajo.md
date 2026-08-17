# 06 — Modo de trabajo

## Regla vigente

La IA escribe el código. El desarrollador revisa, decide y corrige el rumbo.

Esta regla reemplaza al modo manual estricto con el que arrancó el proyecto,
donde la IA solo explicaba y el código lo escribía el desarrollador a mano. El
cambio se hizo para acelerar la entrega del MVP.

## Lo que no cambió

**El código se mantiene simple.** Sin Unit of Work, sin patrón Repository, sin
capas de abstracción que nadie pidió. Cada módulo es `schemas.py` +
`service.py` + `router.py`, y los servicios son funciones que reciben una
`Session`.

**Todo se verifica ejecutándolo.** Escribir código no es terminarlo. Una
función sin ejecutar es una hipótesis.

**La documentación manda.** Si el código va a contradecir algo escrito en
`docs/`, primero se actualiza la doc y se deja constancia del cambio. Las dos
fuentes de verdad en desacuerdo son peores que ninguna.

**Las decisiones de dominio las toma el desarrollador.** La IA propone y
señala consecuencias; no cambia una regla del torneo por su cuenta.

## Sobre el frontend

Criterio a acordar cuando se llegue a esa etapa.
