import { EMcpServerStatus } from '../../../types/mcp.type';

interface McpServerIndicatorProps {
  status: EMcpServerStatus;
  className?: string;
}

const statusConfig = {
  [EMcpServerStatus.RUNNING]: {
    color: 'bg-green-500',
    label: 'Running',
  },
  [EMcpServerStatus.STOPPED]: {
    color: 'bg-gray-500',
    label: 'Stopped',
  },
  [EMcpServerStatus.ERROR]: {
    color: 'bg-red-500',
    label: 'Error',
  },
};

export const McpServerIndicator = ({ status, className = '' }: McpServerIndicatorProps) => {
  const config = statusConfig[status];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`w-2.5 h-2.5 rounded-full ${config.color} animate-pulse`} />
      <span className="text-sm text-gray-600 font-medium">
        {config.label}
      </span>
    </div>
  );
};

export default McpServerIndicator; 