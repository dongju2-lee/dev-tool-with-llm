import React from 'react';
import { cn } from '@/utils/cn';

type LayoutProps = {
  children: React.ReactNode;
  className?: string;
};

export const Layout = ({ children, className }: LayoutProps) => {
  return (
    <div className={cn(
      'min-h-screen bg-background-primary',
      'text-text-primary font-sans antialiased',
      className
    )}>
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
};

export const Card = ({ children, className }: LayoutProps) => {
  return (
    <div className={cn(
      'bg-white rounded-lg shadow-md p-6',
      'border border-gray-100',
      'transition-all duration-200',
      'hover:shadow-lg',
      className
    )}>
      {children}
    </div>
  );
};

export const Button = ({ 
  children, 
  className,
  variant = 'primary',
  ...props
}: LayoutProps & { 
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
} & React.ButtonHTMLAttributes<HTMLButtonElement>) => {
  return (
    <button
      className={cn(
        'px-4 py-2 rounded-md font-medium',
        'transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        {
          'bg-primary text-white hover:bg-primary/90 focus:ring-primary/50': variant === 'primary',
          'bg-secondary text-text-primary hover:bg-secondary/90 focus:ring-secondary/50': variant === 'secondary',
          'border-2 border-primary text-primary hover:bg-primary/10 focus:ring-primary/50': variant === 'outline',
          'text-primary hover:bg-primary/10 focus:ring-primary/50': variant === 'ghost',
        },
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & { className?: string }
>(({ className, ...props }, ref) => {
  return (
    <input
      className={cn(
        'w-full px-4 py-2 rounded-md',
        'border border-gray-200',
        'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent',
        'placeholder:text-text-disabled',
        className
      )}
      ref={ref}
      {...props}
    />
  );
});

Input.displayName = 'Input'; 