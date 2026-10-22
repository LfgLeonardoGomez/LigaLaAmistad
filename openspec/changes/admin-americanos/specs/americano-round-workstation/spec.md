# Puesto de carga por ronda

## Purpose

Permitir una operación de escritorio rápida y segura, con una sola ronda visible, resultados explícitos y tablas consultables sin abandonar la carga.

## ADDED Requirements

### Requirement: RW-01 Una ronda visible y navegación progresiva

La pantalla MUST mostrar evento activo, ronda `n/N`, hasta seis filas con zona, parejas y marcadores, descansos y navegación anterior/siguiente. MUST comenzar en la primera ronda al generar y MUST mantener bloqueadas las rondas posteriores a la primera no guardada. MUST permitir volver a todas las rondas jugadas y a la siguiente habilitada sin volcar el fixture entero en pantalla. Los números de cancha opcionales MUST ser solo posiciones de visualización.

#### Scenario: Primera apertura y desbloqueo
- **GIVEN** un fixture recién generado con N rondas
- **WHEN** se abre el puesto de carga
- **THEN** solo se ve ronda 1; tras guardarla correctamente se habilita ronda 2 y ronda 3 permanece bloqueada hasta guardar 2.

#### Scenario: Volver a una ronda anterior
- **GIVEN** rondas 1 y 2 guardadas, ronda 3 habilitada
- **WHEN** se navega hacia atrás y luego hacia adelante
- **THEN** se muestran los resultados persistidos y se puede llegar hasta 3, sin habilitar 4 ni perder el contexto del evento.

#### Scenario: Salto directo a una ronda bloqueada
- **WHEN** se intenta abrir o guardar por URL/API una ronda posterior a la primera no guardada
- **THEN** no se aceptan resultados fuera de secuencia y la UI dirige a una ronda habilitada.

### Requirement: RW-02 Marcadores de grupos de un dígito

Los marcadores de grupos MUST aceptar solo enteros de 0 a 9 inclusive. Un campo vacío MUST distinguirse de cero y 0-0 MUST ser un empate completo válido. El sistema MUST rechazar negativos, decimales, booleanos, texto o valores fuera de rango tanto en cliente como en API, sin transformar entradas inválidas en cero.

#### Scenario: Cero no es vacío
- **GIVEN** un partido nuevo con ambos campos vacíos
- **WHEN** se ingresa `0` en ambos
- **THEN** ambos quedan completos y 0-0 puede guardarse; limpiar cualquiera vuelve a dejar el resultado incompleto.

#### Scenario: Entrada inválida
- **WHEN** se escribe o pega `10`, `-1`, `1.5`, `a` o se envía `true` como marcador
- **THEN** se impide aceptar ese valor y no se guarda ni sustituye silenciosamente por un marcador válido.

### Requirement: RW-03 Teclado predecible sin guardado automático

El sistema MUST avanzar el foco al completar un campo antes vacío con un dígito válido en el orden estable fila1-A, fila1-B, fila2-A, fila2-B. MUST respetar Tab, Shift+Tab, borrado y selección/corrección de campos existentes. Corregir un valor ya completo MUST mantener el foco salvo navegación explícita. El último campo MUST NOT guardar ni cambiar de ronda automáticamente.

#### Scenario: Carga continua
- **WHEN** se completan sucesivamente los campos vacíos de una ronda
- **THEN** el foco avanza en el orden visual, y completar el último conserva el foco y deja visible `Sin guardar` con botón de guardado explícito.

#### Scenario: Corrección y retroceso
- **GIVEN** un valor ya cargado
- **WHEN** se vuelve con Shift+Tab, se selecciona y se reemplaza o borra
- **THEN** el foco no salta inesperadamente; Tab/Shift+Tab y vuelta a campos anteriores siguen funcionando.

### Requirement: RW-04 Guardado íntegro y atómico de ronda

El sistema MUST guardar mediante acción explícita todos y solo los partidos de la ronda en una única operación atómica. MUST exigir ambos marcadores en cada partido, destacar todos los faltantes y enfocar el primero. Un fallo MUST preservar los valores locales y MUST NOT producir persistencia parcial, tabla parcial ni desbloqueo local de la ronda siguiente. La respuesta exitosa MUST actualizar revisión, estado guardado y tabla.

#### Scenario: Falta un campo entre doce
- **GIVEN** seis partidos, once campos completos y uno vacío
- **WHEN** se pulsa guardar
- **THEN** se destaca el vacío, se mantiene cero como válido en los otros campos y no se persiste ningún partido ni se habilita la próxima ronda.

#### Scenario: Guardado completo
- **WHEN** se guardan todos los partidos válidos de una ronda habilitada
- **THEN** todos quedan persistidos juntos, la tabla se recalcula desde resultados guardados y se habilita la siguiente ronda o revisión final.

#### Scenario: Payload duplicado, parcial o de otra ronda
- **WHEN** se envía un partido repetido, se omite uno o se agrega un ID ajeno a la ronda
- **THEN** la API rechaza el payload completo sin mutaciones.

#### Scenario: Fallo durante la transacción
- **GIVEN** resultados válidos de varios partidos
- **WHEN** ocurre un error antes de confirmar la transacción
- **THEN** ninguno queda guardado y la ronda siguiente permanece bloqueada.

#### Scenario: Respuesta perdida después de un posible guardado
- **WHEN** la conexión se pierde al guardar
- **THEN** la UI conserva los valores y no asume éxito ni desbloquea; al reconectar consulta el estado canónico, reconoce si coinciden los resultados guardados o muestra conflicto antes de reintentar.

### Requirement: RW-05 Edición y protección de cambios sin guardar

El sistema MUST permitir corregir rondas completas guardadas hasta confirmar clasificados. MUST mostrar estado guardado/sin guardar y ofrecer guardar, descartar o permanecer al navegar con cambios, incluidos cambios de evento y salida por enlaces del panel. MUST advertir antes de recargar/cerrar con cambios. Descartar MUST restaurar el último estado persistido, no ceros por defecto.

#### Scenario: Navegación con edición pendiente
- **GIVEN** una ronda jugada modificada localmente
- **WHEN** se solicita otra ronda o sección
- **THEN** guardar continúa solo si toda la ronda es válida y persiste; descartar restaura los datos del servidor; permanecer cancela la navegación.

#### Scenario: Dos administradores editan la misma base
- **GIVEN** dos pantallas con la misma revisión
- **WHEN** una guarda y la otra intenta guardar después
- **THEN** la segunda recibe conflicto, conserva su edición para comparar y no sobrescribe silenciosamente la primera.

### Requirement: RW-06 Tablas en cajón dentro de la misma página

`Ver tablas` MUST alternar un cajón lateral temporal dentro del puesto de carga, sin navegación de página ni barra permanente. Con dos zonas MUST permitir alternar A/B y con una MUST mostrar directamente su tabla. MUST conservar ronda y valores locales, indicar que la tabla solo incluye guardados y gestionar foco accesible: entrada, contención mientras esté abierto, cierre por botón/Escape y restauración al elemento previo.

#### Scenario: Consultar y continuar cargando
- **GIVEN** ronda 3 parcialmente escrita y foco en un marcador
- **WHEN** se abre el cajón, alterna zona y se cierra
- **THEN** la ronda y los marcadores se conservan, el foco vuelve al punto previo y no se dispara autoguardado ni autoavance.

#### Scenario: Una sola zona
- **WHEN** se abre el cajón en un evento de una zona
- **THEN** se muestra su tabla sin pestaña B, con columnas principales posición, pareja, puntos y diferencia de games.

### Requirement: RW-07 Recuperación segura de evento y ronda

El sistema MUST poder retomar por URL un evento y ronda válidos usando datos persistidos como autoridad. MUST elegir la primera ronda no guardada como continuación por defecto, o la última si todas están guardadas. MUST recuperar revisión/playoffs/completado según el estado y MUST NOT presentar ediciones no guardadas como persistidas después de refrescar.

#### Scenario: Refresco en una ronda guardada
- **WHEN** se recarga una URL de evento y ronda habilitada
- **THEN** se recuperan los resultados y revisión del servidor y se conserva esa ronda; un ID inválido o bloqueado redirige a la continuación segura.

#### Scenario: Retomar desde el listado
- **WHEN** se abre un evento con rondas pendientes, en revisión, en playoffs o completado
- **THEN** se abre su continuación canónica y se permite consultar las rondas guardadas correspondientes, sin mezclar eventos.
