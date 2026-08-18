import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-ink-900 text-surface hover:bg-ink-700',
  secondary: 'bg-surface text-ink-700 ring-1 ring-ink-300 hover:bg-ink-50',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'text-ink-600 hover:bg-ink-100',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

export function Button({ variant = 'primary', className = '', ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm
        font-medium transition-colors focus:outline-none focus-visible:ring-2
        focus-visible:ring-ink-400 focus-visible:ring-offset-2
        disabled:cursor-not-allowed disabled:opacity-50
        ${BUTTON_STYLES[variant]} ${className}`}
    />
  )
}

interface FieldProps {
  label: string
  hint?: string
  children: ReactNode
}

export function Field({ label, hint, children }: FieldProps) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-500">{hint}</span>}
    </label>
  )
}

const CONTROL_STYLES = `w-full rounded-md border-0 bg-surface px-3 py-2 text-sm text-ink-900
  ring-1 ring-ink-300 placeholder:text-ink-400
  focus:outline-none focus:ring-2 focus:ring-ink-800 disabled:bg-ink-100`

export function Input({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${CONTROL_STYLES} ${className}`} />
}

export function Select({ className = '', ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${CONTROL_STYLES} ${className}`} />
}

export function Textarea({
  className = '',
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${CONTROL_STYLES} resize-y ${className}`} />
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg bg-surface ring-1 ring-ink-200 ${className}`}>{children}</div>
  )
}

export function PageHeader({ title, description, action }: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-500">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Table({ head, children }: { head: ReactNode; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-ink-200 bg-ink-50 text-left text-xs font-medium uppercase tracking-wide text-ink-500">
          {head}
        </thead>
        <tbody className="divide-y divide-ink-100">{children}</tbody>
      </table>
    </div>
  )
}

export function Th({ children, className = '' }: { children?: ReactNode; className?: string }) {
  return <th className={`px-4 py-2.5 font-medium ${className}`}>{children}</th>
}

export function Td({ children, className = '' }: { children?: ReactNode; className?: string }) {
  return <td className={`px-4 py-3 ${className}`}>{children}</td>
}

const BADGE_STYLES: Record<string, string> = {
  active: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  withdrawn: 'bg-ink-100 text-ink-600 ring-ink-300',
  played: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  pending: 'bg-amber-50 text-amber-700 ring-amber-200',
}

const BADGE_LABELS: Record<string, string> = {
  active: 'Activa',
  withdrawn: 'Dada de baja',
  played: 'Jugado',
  pending: 'Pendiente',
}

export function Badge({ value }: { value: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset
        ${BADGE_STYLES[value] ?? 'bg-ink-100 text-ink-600 ring-ink-300'}`}
    >
      {BADGE_LABELS[value] ?? value}
    </span>
  )
}

export function Alert({ children, tone = 'error' }: { children: ReactNode; tone?: 'error' | 'info' }) {
  const styles =
    tone === 'error'
      ? 'bg-red-50 text-red-700 ring-red-200'
      : 'bg-blue-50 text-blue-700 ring-blue-200'
  return (
    <div role="alert" className={`rounded-md px-3 py-2 text-sm ring-1 ring-inset ${styles}`}>
      {children}
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="px-4 py-10 text-center text-sm text-ink-500">{children}</p>
}

export function Spinner({ label = 'Cargando…' }: { label?: string }) {
  return <p className="px-4 py-10 text-center text-sm text-ink-400">{label}</p>
}
