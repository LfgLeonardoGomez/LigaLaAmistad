import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { ThemeToggle } from '../theme/ThemeToggle'

/**
 * Which edges of a horizontal scroller still hide content.
 *
 * On a narrow phone the nav scrolls, and nothing tells the reader that there
 * are more tabs past the edge. This is what lets the CSS fade exactly the side
 * that has something left to reveal, instead of dimming an edge for no reason.
 */
function useScrollEdges<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [edges, setEdges] = useState({ start: false, end: false })

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const update = () => {
      const max = element.scrollWidth - element.clientWidth
      // The 1px slack absorbs the fractional scroll positions a zoomed or
      // high-DPI viewport produces, which would otherwise fade a nav that is
      // already at its end.
      setEdges({ start: element.scrollLeft > 1, end: element.scrollLeft < max - 1 })
    }

    update()
    element.addEventListener('scroll', update, { passive: true })
    // A resize changes what fits, so the fade has to be recomputed on rotation
    // and on the breakpoints that grow the type.
    const observer = new ResizeObserver(update)
    observer.observe(element)

    return () => {
      element.removeEventListener('scroll', update)
      observer.disconnect()
    }
  }, [])

  return [ref, edges] as const
}

const NAV_ITEMS = [
  { to: '/', label: 'Inicio', end: true },
  { to: '/parejas', label: 'Parejas', end: false },
  { to: '/tabla', label: 'Tabla', end: false },
  { to: '/cruces', label: 'Cruces', end: false },
  { to: '/resultados', label: 'Resultados', end: false },
]

export function PublicLayout() {
  const [navRef, navEdges] = useScrollEdges<HTMLElement>()

  return (
    <div className="public-shell flex min-h-full flex-col">
      <header
        className="sticky top-0 z-20 backdrop-blur-md"
        style={{
          backgroundColor: 'color-mix(in srgb, var(--color-canvas) 86%, transparent)',
          borderBottom: '1px solid var(--color-rule)',
        }}
      >
        <div className="mx-auto flex w-full max-w-[1180px] items-center justify-between gap-4 px-4 py-3.5 sm:px-8">
          {/* `flex-none`, no `min-w-0`: con cinco items el nav no cede ancho y
              antes aplastaba la marca hasta dejarla en cero, con el texto
              desbordando encima. El que se adapta es el nav, no la marca. */}
          <NavLink
            to="/"
            aria-label="Liga La Amistad, ir al inicio"
            className="flex flex-none items-center gap-2.5"
          >
            <span
              className="display grid h-[34px] w-[34px] flex-none place-items-center rounded-full text-sm"
              style={{ border: '2px solid var(--color-accent)', color: 'var(--color-accent)' }}
            >
              LA
            </span>
            {/* En mobile queda solo el circulo: los 100px que libera el nombre
                son los que necesitan las cinco pestanas para entrar. No se
                pierde identidad, el circulo ya la lleva y la home la repite
                entera en el hero. El nombre vuelve donde hay lugar. */}
            <span className="display hidden text-[13px] leading-tight sm:block sm:text-[15px]">
              Liga
              <br />
              La Amistad
            </span>
          </NavLink>

          <div className="flex min-w-0 flex-1 items-center justify-end gap-4">
            {/* Si los items no entran, el nav scrollea en lugar de invadir la
                marca. Es el mismo patron que ya usa el panel de admin. */}
            <nav
              ref={navRef}
              className="nav-fade min-w-0 overflow-x-auto"
              data-fade-start={navEdges.start || undefined}
              data-fade-end={navEdges.end || undefined}
            >
              <ul className="flex items-center gap-2 sm:gap-3 lg:gap-5">
                {NAV_ITEMS.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.end}
                      className="display text-[11px] whitespace-nowrap lg:text-[13px]"
                      style={({ isActive }) => ({
                        color: isActive ? 'var(--color-accent)' : 'var(--color-fg)',
                        borderBottom: isActive
                          ? '2px solid var(--color-accent)'
                          : '2px solid transparent',
                        paddingBottom: '2px',
                      })}
                    >
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </nav>
            {/* Recien en `lg` hay lugar para marca + nav + selector a la vez.
                Mostrarlo desde `sm` era lo que reventaba el nav en tablet. */}
            <div className="hidden lg:block">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Full width on purpose: each page wraps its own content in
          `.container-page`, which lets a hero or a photo band break out. */}
      <main className="w-full flex-1">
        <Outlet />
      </main>

      <footer className="mt-16" style={{ borderTop: '1px solid var(--color-rule)' }}>
        <div className="mx-auto w-full max-w-[1180px] px-4 py-6 sm:px-8">
          <div className="flex flex-col gap-3 text-xs sm:flex-row sm:items-center sm:justify-between">
            <span className="display" style={{ color: 'var(--color-accent)' }}>
              Liga La Amistad · Temporada 2026
            </span>
            <span style={{ color: 'var(--color-fg-muted)' }}>
              Pádel amateur · Dos zonas · Al mejor de tres sets
            </span>
            <div className="lg:hidden">
              <ThemeToggle />
            </div>
          </div>

          <div
            className="mt-5 pt-4 text-xs"
            style={{ borderTop: '1px solid var(--color-rule)', color: 'var(--color-fg-muted)' }}
          >
            <DeveloperCredit />
          </div>
        </div>
      </footer>
    </div>
  )
}

// The prefilled message says where the lead came from, so an enquiry that
// starts on this site is recognisable without asking.
const WHATSAPP = 'https://wa.me/5492612094262'
const GREETING = encodeURIComponent(
  'Hola Leonardo, vi la web de Liga La Amistad y quería consultarte por un sitio.',
)

function DeveloperCredit() {
  return (
    <p>
      Desarrollo web ·{' '}
      <a
        href={`${WHATSAPP}?text=${GREETING}`}
        target="_blank"
        rel="noopener noreferrer"
        className="font-semibold transition-opacity hover:opacity-80"
        style={{ color: 'var(--color-accent)' }}
      >
        Leonardo Gomez
        <svg
          viewBox="0 0 24 24"
          aria-hidden="true"
          className="ml-1 inline-block h-[0.9em] w-[0.9em] align-[-0.05em]"
          fill="currentColor"
        >
          <path d="M12.04 2A9.9 9.9 0 0 0 2.13 11.9c0 1.75.46 3.45 1.32 4.95L2 22l5.3-1.39a9.86 9.86 0 0 0 4.74 1.21h.01a9.9 9.9 0 0 0 0-19.82Zm5.77 14.06c-.24.67-1.4 1.29-1.94 1.34-.5.05-.98.22-3.3-.69-2.78-1.1-4.55-3.94-4.69-4.12-.14-.19-1.13-1.5-1.13-2.87s.72-2.04.97-2.32c.25-.28.55-.35.73-.35h.53c.17 0 .4-.06.63.48.24.58.8 1.99.87 2.13.07.14.12.31.02.5-.09.19-.14.31-.28.47l-.42.49c-.14.14-.28.29-.12.57.16.28.71 1.17 1.52 1.89 1.04.93 1.92 1.22 2.2 1.36.28.14.44.12.6-.07.17-.19.7-.81.88-1.09.19-.28.37-.23.63-.14.25.09 1.62.76 1.9.9.28.14.46.21.53.33.07.12.07.68-.17 1.34Z" />
        </svg>
      </a>
    </p>
  )
}
