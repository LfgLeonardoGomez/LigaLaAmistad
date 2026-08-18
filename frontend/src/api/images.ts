/**
 * Cloudinary serves the file exactly as it was uploaded unless the URL says
 * otherwise. A photo straight from a phone is a few megabytes, and a grid of
 * twenty pairs would ship all of it to a visitor who is almost certainly on
 * mobile data.
 *
 * Transformations live in the URL, so the same upload serves every size and
 * nothing has to be re-uploaded or stored twice.
 */

const UPLOAD_MARKER = '/image/upload/'

interface Options {
  /** Width in CSS pixels. The device pixel ratio is handled by Cloudinary. */
  width: number
  /** Height in CSS pixels. Given both, the crop is filled and centred on faces. */
  height?: number
}

export function imageUrl(url: string | null | undefined, { width, height }: Options): string {
  if (!url) return ''

  // Anything that is not a Cloudinary upload — a data URI, a local file, an
  // external logo — is left exactly as it is.
  const marker = url.indexOf(UPLOAD_MARKER)
  if (marker === -1) return url

  const transforms = [
    'f_auto', // WebP or AVIF when the browser takes it
    'q_auto', // quality chosen per image
    'dpr_auto', // one URL covers retina and non-retina
    `w_${width}`,
  ]

  if (height !== undefined) {
    // g_auto keeps faces in frame when the crop has to cut something.
    transforms.push(`h_${height}`, 'c_fill', 'g_auto')
  } else {
    transforms.push('c_limit')
  }

  const cut = marker + UPLOAD_MARKER.length
  return `${url.slice(0, cut)}${transforms.join(',')}/${url.slice(cut)}`
}
