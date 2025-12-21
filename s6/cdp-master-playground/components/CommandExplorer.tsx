
import React, { useState } from 'react';
import { CDP_DOMAINS } from '../constants';
import { CDPCommand } from '../types';

interface CommandExplorerProps {
  onSelectCommand: (cmd: CDPCommand) => void;
}

const CommandExplorer: React.FC<CommandExplorerProps> = ({ onSelectCommand }) => {
  const [search, setSearch] = useState('');
  const [expandedDomains, setExpandedDomains] = useState<Record<string, boolean>>({
    'Page': true,
    'Runtime': true
  });

  const toggleDomain = (name: string) => {
    setExpandedDomains(prev => ({ ...prev, [name]: !prev[name] }));
  };

  const filteredDomains = CDP_DOMAINS.map(domain => ({
    ...domain,
    commands: domain.commands.filter(cmd => 
      cmd.method.toLowerCase().includes(search.toLowerCase()) || 
      domain.name.toLowerCase().includes(search.toLowerCase())
    )
  })).filter(domain => domain.commands.length > 0);

  return (
    <div className="w-80 border-r border-slate-700 bg-slate-900/50 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700">
        <div className="relative">
          <input 
            type="text"
            placeholder="Search commands..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-md py-1.5 px-3 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-slate-500"
          />
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {filteredDomains.map(domain => (
          <div key={domain.name} className="border-b border-slate-800/50">
            <button 
              onClick={() => toggleDomain(domain.name)}
              className="w-full flex items-center gap-2 p-3 hover:bg-slate-800/50 transition-colors text-left"
            >
              <svg 
                className={`w-3 h-3 text-slate-500 transition-transform ${expandedDomains[domain.name] ? 'rotate-90' : ''}`} 
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
              </svg>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{domain.name}</span>
            </button>
            
            {expandedDomains[domain.name] && (
              <div className="pb-2">
                {domain.commands.map(cmd => (
                  <button
                    key={`${cmd.domain}.${cmd.method}`}
                    onClick={() => onSelectCommand(cmd)}
                    className="w-full text-left pl-8 pr-4 py-2 hover:bg-blue-600/10 hover:text-blue-400 text-xs text-slate-300 border-l-2 border-transparent hover:border-blue-500 transition-all"
                  >
                    <span className="opacity-50">{cmd.domain}.</span>
                    <span className="font-semibold">{cmd.method}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default CommandExplorer;
