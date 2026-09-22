import { useEffect, useState } from 'react'

import type { Sponsor } from '../api/types'
import { imageUrl } from '../api/images'

/** Below this count the strip stays still. A moving track for one or two
    logos would read as a glitch, not as a marquee. */
const MARQUEE_THRESHOLD = 5

/**
 * Tracks the media query instead of reading it once at mount: a visitor can
 * flip "reduce motion" in system settings without leaving the tab, and the
 * band has to catch up without a reload.
 */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReduced(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  return reduced
}

/**
 * "Nos acompañan": sponsor logos as light frosted-glass cards.
 *
 * The glass stays light in every theme on purpose. `.card` has no fill at
 * all, which is exactly what made a transparent-background logo disappear
 * against `--color-canvas` on velada and lima — a themed dark tint here
 * would just relocate the same bug. This is only ever meant to sit inside a
 * `.photo-band`/`.photo__veil` pair, which is what keeps the glass reading
 * the same no matter which part of the photo happens to be behind it.
 */
export function SponsorBand({ sponsors }: { sponsors: Sponsor[] }) {
  const reducedMotion = usePrefersReducedMotion()

  if (sponsors.length === 0) return null

  const rotates = sponsors.length >= MARQUEE_THRESHOLD && !reducedMotion
  // A static row still needs to scroll once there are enough logos that
  // shrinking them to fit would break the size the brief asks for — this is
  // also where reduced motion lands once rotation is turned off.
  const wide = sponsors.length >= MARQUEE_THRESHOLD

  return (
    <div>
      {/* Centred, unlike every other section heading on the site, which sits
          left. This band is not a section of content: it is a sign, and the
          logos under it are centred so that two sponsors do not strand
          themselves across the full width. A left heading over centred logos
          reads as two unrelated things. */}
      <h2
        className="mb-5 text-center text-xs font-semibold tracking-widest uppercase"
        style={{ color: 'var(--color-fg-muted)' }}
      >
        Nos acompañan
      </h2>

      {/* `--scroll` is the only modifier with its own rules: it is what
          turns on horizontal scrolling for the reduced-motion fallback. The
          marquee gets its clipping from the base viewport class, and the
          static row needs nothing beyond it either — see the comment on
          `.sponsor-band__row` for why no width cap belongs here. */}
      <div
        className={
          wide && !rotates
            ? 'sponsor-band__viewport sponsor-band__viewport--scroll'
            : 'sponsor-band__viewport'
        }
      >
        {rotates ? (
          // Two copies back to back, animated as one strip that shifts left
          // by exactly one copy's width: the seam where it resets never
          // shows because the second copy is already sitting where the
          // first one started.
          <div
            className="sponsor-band__marquee"
            style={{ animationDuration: `${sponsors.length * 4}s` }}
          >
            <SponsorRow sponsors={sponsors} />
            <SponsorRow sponsors={sponsors} duplicate />
          </div>
        ) : (
          <SponsorRow sponsors={sponsors} />
        )}
      </div>
    </div>
  )
}

/**
 * `duplicate` marks the second, purely decorative copy used by the marquee:
 * hidden from the accessibility tree and pulled out of tab order, so a
 * keyboard or screen-reader pass meets every sponsor once, not twice.
 */
function SponsorRow({ sponsors, duplicate = false }: { sponsors: Sponsor[]; duplicate?: boolean }) {
  return (
    <ul className="sponsor-band__row" aria-hidden={duplicate || undefined}>
      {sponsors.map((sponsor) => (
        <li key={duplicate ? `dup-${sponsor.id}` : sponsor.id} className="flex-none">
          <SponsorCard sponsor={sponsor} tabIndex={duplicate ? -1 : undefined} />
        </li>
      ))}
    </ul>
  )
}

function SponsorCard({ sponsor, tabIndex }: { sponsor: Sponsor; tabIndex?: number }) {
  const image = (
    <img
      src={imageUrl(sponsor.logo_url, { width: 320 })}
      alt={sponsor.name}
      loading="lazy"
      className="sponsor-card__logo"
    />
  )

  if (!sponsor.url) {
    // No link means no hover or cursor affordance either — a plate that
    // looks clickable but goes nowhere is worse than one that never claimed
    // to be a button.
    return <div className="sponsor-card">{image}</div>
  }

  return (
    <a
      href={sponsor.url}
      target="_blank"
      rel="noopener noreferrer"
      tabIndex={tabIndex}
      className="sponsor-card sponsor-card--link"
    >
      {image}
    </a>
  )
}

/**
 * The footer placement: its own `.photo-band`, built the same way HomePage
 * builds its hero photo, so the glass has a consistent backdrop to sit on
 * outside the home page too. Renders nothing when there are no sponsors —
 * the alternative is an empty strip with a hairline that explains nothing.
 */
export function SponsorFooterBand({ sponsors }: { sponsors: Sponsor[] }) {
  if (sponsors.length === 0) return null

  return (
    <section className="photo-band">
      <div className="photo-band__media" />
      <div className="photo__veil" />
      <div className="container-page py-[clamp(28px,5vw,52px)]">
        <SponsorBand sponsors={sponsors} />
      </div>
    </section>
  )
}
