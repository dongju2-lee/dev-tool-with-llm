export type Size = 'small' | 'medium' | 'large'
export type Variant = 'primary' | 'secondary' | 'outline' | 'ghost'
export type ColorScheme = 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info'

export interface BaseProps {
  className?: string
  children?: React.ReactNode
}

export interface ButtonProps extends BaseProps {
  variant?: Variant
  size?: Size
  disabled?: boolean
  onClick?: () => void
}

export interface InputProps extends BaseProps {
  type?: string
  placeholder?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  error?: string
  disabled?: boolean
} 