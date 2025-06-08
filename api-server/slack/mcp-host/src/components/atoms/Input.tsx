import React from 'react'
import { InputProps } from '@/types/common'
import { cn } from '@/utils/cn'

export const Input = ({
  className,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  disabled = false,
  ...props
}: InputProps) => {
  return (
    <div className="relative">
      <input
        type={type}
        className={cn(
          'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed',
          error && 'border-red-500 focus:ring-red-500/50',
          className
        )}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        disabled={disabled}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-500">{error}</p>
      )}
    </div>
  )
}

export default Input 