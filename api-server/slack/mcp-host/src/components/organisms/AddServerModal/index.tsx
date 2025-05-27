import { useState, FormEvent } from 'react';
import { Modal } from '../../molecules/Modal';
import { EMcpServerStatus, EMcpServerType, TMcpServer } from '../../../types/mcp.type';

interface AddServerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (server: Omit<TMcpServer, 'id'>) => void;
}

export const AddServerModal = ({ isOpen, onClose, onSubmit }: AddServerModalProps) => {
  const [serverType, setServerType] = useState<EMcpServerType>(EMcpServerType.LOCAL);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [command, setCommand] = useState('');
  const [args, setArgs] = useState<string[]>([]);
  const [argsInput, setArgsInput] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    
    const serverData: Omit<TMcpServer, 'id'> = {
      name,
      desc: '', // Optional description can be added later
      type: serverType,
      status: EMcpServerStatus.STOPPED,
      
      tools: [],
      url: serverType === EMcpServerType.LOCAL ? '' : url,
      args: serverType === EMcpServerType.LOCAL ? args : [],
      histories: [],
      command: serverType === EMcpServerType.LOCAL ? command : '',
    };

    onSubmit(serverData);
    handleReset();
  };

  const handleReset = () => {
    setName('');
    setUrl('');
    setCommand('');
    setArgs([]);
    setArgsInput('');
  };

  const handleArgsChange = (value: string) => {
    setArgsInput(value);
    setArgs(value.split(' ').filter(arg => arg.trim() !== ''));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Server"
      footer={
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            form="add-server-form"
            type="submit"
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Add Server
          </button>
        </div>
      }
    >
      <form id="add-server-form" onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Server Type</label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                value={EMcpServerType.LOCAL}
                checked={serverType === EMcpServerType.LOCAL}
                onChange={(e) => setServerType(e.target.value as EMcpServerType)}
                className="mr-2"
              />
              Local
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value={EMcpServerType.REMOTE}
                checked={serverType === EMcpServerType.REMOTE}
                onChange={(e) => setServerType(e.target.value as EMcpServerType)}
                className="mr-2"
              />
              SSE
            </label>
          </div>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {serverType === EMcpServerType.LOCAL ? (
          <>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Command</label>
              <input
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                required
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Arguments</label>
              <input
                type="text"
                value={argsInput}
                onChange={(e) => handleArgsChange(e.target.value)}
                placeholder="Space-separated arguments"
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {args.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {args.map((arg, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-gray-100 rounded text-sm"
                    >
                      {arg}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">URL</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}
      </form>
    </Modal>
  );
};

export default AddServerModal; 