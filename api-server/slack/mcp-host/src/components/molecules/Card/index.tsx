import { ReactNode } from 'react';

interface CardProps {
  title?: string;
  subtitle?: string | ReactNode;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

export const Card = ({
  title,
  subtitle,
  children,
  className = '',
  onClick,
  hoverable = false,
}: CardProps) => {
  return (
    <div
      className={`
        bg-white rounded-lg shadow-md p-4
        ${hoverable ? 'transition-transform hover:scale-[1.02] cursor-pointer' : ''}
        ${className}
      `.trim()}
      onClick={onClick}
    >
      {title && (
        <h3 className="text-lg font-semibold text-gray-800 mb-1">
          {title}
        </h3>
      )}
      {subtitle && (
        <p className="text-sm text-gray-600 mb-3">
          {subtitle}
        </p>
      )}
      <div className="text-gray-700">
        {children}
      </div>
    </div>
  );
};

export default Card; 