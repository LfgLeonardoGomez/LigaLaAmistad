# Liga La Amistad — Índice de documentación

Este directorio contiene la definición funcional inicial del proyecto **Liga La Amistad**.

La idea es usar estos documentos como plano antes de programar: primero entendemos el producto, el dominio y las reglas; después escribimos código.

## Documentos

1. [Alcance del producto](./01-alcance-producto.md)
2. [Reglas de negocio](./02-reglas-negocio.md)
3. [Historias de usuario](./03-historias-usuario.md)
4. [Backend MVP con FastAPI](./04-backend-mvp-fastapi.md)
5. [Modelo de datos inicial](./05-modelo-datos.md)
6. [Modo de trabajo](./06-modo-de-trabajo.md)
7. [Prompt para la web pública](./07-prompt-web-publica.md)
8. [Pendientes](./08-pendientes.md)

## Principios del proyecto

- Backend simple con FastAPI.
- Web pública clara y visual.
- Panel administrativo mínimo, solo para administradores.
- Tabla de posiciones calculada automáticamente desde los resultados.
- No persistir datos derivables: si se puede calcular, se calcula.
- Nada se elimina: los datos de la liga se corrigen o se marcan, no se borran.
- Nada de sobreingeniería: primero resolver bien la liga actual.
- Programación manual asistida por IA: la IA ayuda, pero las decisiones y el aprendizaje los lleva el desarrollador.
- El backend se escribe a mano. La IA no toca código sin pedido explícito. Ver [Modo de trabajo](./06-modo-de-trabajo.md).

## Decisiones pendientes

Ver el cierre de [Reglas de negocio](./02-reglas-negocio.md) para las decisiones que todavía no están cerradas.
