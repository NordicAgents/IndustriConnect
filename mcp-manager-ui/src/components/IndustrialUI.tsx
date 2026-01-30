import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types';
import { MCPServer } from '../types/mcp-types';
import { format } from 'date-fns';

interface IndustrialUIProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  mcpServers: MCPServer[];
  onMCPConnect: (serverId: string) => void;
  onMCPDisconnect: (serverId: string) => void;
  onOpenSettings: () => void;
}

export default function IndustrialUI({
  messages,
  onSendMessage,
  isLoading,
  mcpServers,
  onMCPConnect,
  onMCPDisconnect,
  onOpenSettings
}: IndustrialUIProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSendMessage(input);
        setInput('');
      }
    }
  };

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#f6f7f8] dark:bg-[#101922] text-slate-900 dark:text-slate-100 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 flex flex-col border-r border-slate-200 dark:border-[#233648] bg-[#f6f7f8] dark:bg-[#101922]">
        <div className="p-6 flex items-center gap-3">
          <div className="size-8 bg-[#137fec] rounded flex items-center justify-center text-white">
            <span className="material-symbols-outlined">terminal</span>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight uppercase">Command Center</h1>
            <p className="text-[10px] text-slate-500 dark:text-[#92adc9] uppercase font-medium">Automation OS v2.4</p>
          </div>
        </div>

        <nav className="flex-1 px-4 flex flex-col gap-6 overflow-y-auto custom-scrollbar">
          <div>
            <div className="flex items-center justify-between px-3 mb-2">
                <p className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Active Nodes</p>
                <button
                    onClick={onOpenSettings}
                    className="text-slate-400 hover:text-[#137fec] transition-colors"
                    title="Configure Servers"
                >
                    <span className="material-symbols-outlined text-[16px]">add</span>
                </button>
            </div>
            <div className="flex flex-col gap-1">
              {mcpServers.map(server => (
                <div
                  key={server.id}
                  onClick={() => server.status === 'connected' ? onMCPDisconnect(server.id) : onMCPConnect(server.id)}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                    server.status === 'connected'
                      ? 'bg-[#137fec]/10 text-[#137fec] border border-[#137fec]/20'
                      : 'hover:bg-slate-100 dark:hover:bg-[#233648] text-slate-500'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-[20px]">hard_drive</span>
                    <span className="text-sm font-medium truncate max-w-[120px]">{server.name}</span>
                  </div>
                  <div className={`size-2 rounded-full ${
                    server.status === 'connected'
                      ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
                      : server.status === 'connecting'
                        ? 'bg-yellow-500 animate-pulse'
                        : 'bg-red-500/50'
                  }`}></div>
                </div>
              ))}
              {mcpServers.length === 0 && (
                 <div
                    onClick={onOpenSettings}
                    className="px-3 py-2 text-xs text-slate-500 italic hover:text-[#137fec] cursor-pointer transition-colors"
                 >
                    No servers configured. Click to add +
                 </div>
              )}
            </div>
          </div>

          <div>
            <p className="px-3 text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Automation Tools</p>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors cursor-pointer opacity-70">
                <span className="material-symbols-outlined text-[20px] text-slate-400">settings_input_component</span>
                <p className="text-sm font-medium leading-normal">PLCs</p>
              </div>
              <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors cursor-pointer opacity-70">
                <span className="material-symbols-outlined text-[20px] text-slate-400">sensors</span>
                <p className="text-sm font-medium leading-normal">Sensors</p>
              </div>
              <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors cursor-pointer opacity-70">
                <span className="material-symbols-outlined text-[20px] text-slate-400">account_tree</span>
                <p className="text-sm font-medium leading-normal">Logic Controllers</p>
              </div>
            </div>
          </div>
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-[#233648] flex flex-col gap-1">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors cursor-pointer opacity-70">
            <span className="material-symbols-outlined text-[20px] text-slate-400">help</span>
            <p className="text-sm font-medium">Support</p>
          </div>
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors cursor-pointer opacity-70">
            <span className="material-symbols-outlined text-[20px] text-slate-400">receipt_long</span>
            <p className="text-sm font-medium">System Logs</p>
          </div>
          <div className="mt-2 flex items-center gap-3 px-3 py-2">
            <div className="size-8 rounded-full bg-slate-200 dark:bg-[#233648] bg-center bg-cover flex items-center justify-center">
                <span className="material-symbols-outlined text-slate-400">person</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold truncate">Operator</p>
              <p className="text-[10px] text-slate-500">Shift Active</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative bg-[#f6f7f8] dark:bg-[#101922]">
        {/* Top Header Stats */}
        <header className="flex items-center justify-between px-8 py-4 border-b border-slate-200 dark:border-[#233648]">
          <div className="flex gap-8">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">CPU Load</span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold font-mono">14%</span>
                <span className="text-[10px] font-medium text-orange-500">-2%</span>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Connectivity</span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold font-mono">12ms</span>
                <span className="text-[10px] font-medium text-green-500">+1%</span>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Temperature</span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold font-mono">42°C</span>
                <span className="text-[10px] font-medium text-orange-500">-1%</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="p-2 rounded hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors relative">
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-2 right-2 size-2 bg-[#137fec] rounded-full border-2 border-[#f6f7f8] dark:border-[#101922]"></span>
            </button>
            <button
                onClick={onOpenSettings}
                className="p-2 rounded hover:bg-slate-100 dark:hover:bg-[#233648] transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">settings</span>
            </button>
          </div>
        </header>

        {/* Chat / Message History */}
        <div className="flex-1 overflow-y-auto px-8 py-6 custom-scrollbar space-y-6">
            {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 opacity-50">
                    <span className="material-symbols-outlined text-6xl mb-4">smart_toy</span>
                    <p>System ready. Waiting for commands.</p>
                </div>
            )}

            {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role !== 'user' && (
                        <div className="size-10 rounded-lg bg-slate-200 dark:bg-[#233648] flex items-center justify-center shrink-0">
                            <span className="material-symbols-outlined text-[#137fec]">smart_toy</span>
                        </div>
                    )}

                    <div className={`flex flex-col gap-1.5 pt-1 ${msg.role === 'user' ? 'items-end' : ''}`}>
                        <div className="flex items-center gap-3">
                            {msg.role === 'user' ? (
                                <>
                                    <p className="text-[11px] text-slate-400 font-medium uppercase text-right">{format(msg.timestamp, 'p')}</p>
                                    <p className="text-sm font-bold">Operator</p>
                                </>
                            ) : (
                                <>
                                    <p className="text-sm font-bold">Automation System</p>
                                    <p className="text-[11px] text-slate-400 font-medium uppercase">{format(msg.timestamp, 'p')}</p>
                                </>
                            )}
                        </div>

                        <div className={`text-sm leading-relaxed max-w-2xl ${
                            msg.role === 'user'
                                ? 'bg-[#137fec] text-white rounded-xl rounded-tr-none px-4 py-3 shadow-lg shadow-[#137fec]/10 max-w-lg'
                                : 'text-slate-600 dark:text-slate-300 space-y-3'
                        }`}>
                           {msg.content}

                           {/* Render tool calls if any */}
                           {msg.toolCalls && msg.toolCalls.length > 0 && (
                               <div className="mt-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-lg p-3 font-mono text-xs space-y-1">
                                   {msg.toolCalls.map(tool => (
                                       <div key={tool.id} className="border-b border-slate-200 dark:border-slate-800 last:border-0 pb-1 last:pb-0 mb-1 last:mb-0">
                                           <div className="flex justify-between">
                                               <span className="text-slate-500">Tool: {tool.toolName}</span>
                                               <span className={tool.result?.isError ? "text-red-500" : "text-green-500"}>
                                                   {tool.result?.isError ? 'ERROR' : 'SUCCESS'}
                                               </span>
                                           </div>
                                           {tool.result?.content && (
                                               <div className="text-slate-400 mt-1 whitespace-pre-wrap">
                                                   {JSON.stringify(tool.result.result || tool.result.content, null, 2)}
                                               </div>
                                           )}
                                       </div>
                                   ))}
                               </div>
                           )}

                           {msg.error && (
                               <div className="mt-2 text-red-500 text-xs bg-red-50 dark:bg-red-900/20 p-2 rounded border border-red-200 dark:border-red-900/50">
                                   Error processing request.
                               </div>
                           )}
                        </div>
                    </div>

                    {msg.role === 'user' && (
                        <div className="size-10 rounded-lg bg-slate-800 dark:bg-slate-700 flex items-center justify-center shrink-0 overflow-hidden border border-slate-600">
                             <span className="material-symbols-outlined text-white">person</span>
                        </div>
                    )}
                </div>
            ))}

            {isLoading && (
                 <div className="flex gap-4 max-w-4xl mx-auto">
                    <div className="size-10 rounded-lg bg-slate-200 dark:bg-[#233648] flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[#137fec]">smart_toy</span>
                    </div>
                    <div className="flex flex-col gap-1.5 pt-1">
                        <div className="flex items-center gap-3">
                            <p className="text-sm font-bold">Automation System</p>
                        </div>
                         <div className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
                            <span className="animate-pulse">Processing...</span>
                         </div>
                    </div>
                </div>
            )}
            <div ref={messagesEndRef} />
        </div>

        {/* Command Input Field */}
        <div className="p-8 pt-0">
          <div className="max-w-4xl mx-auto">
            <div className="relative group">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-white dark:bg-[#1a2632] border border-slate-200 dark:border-[#324d67] rounded-xl px-4 py-4 pr-16 focus:ring-1 focus:ring-[#137fec] focus:border-[#137fec] text-sm placeholder-slate-400 dark:placeholder-slate-500 resize-none transition-all shadow-xl shadow-black/5 text-slate-900 dark:text-white"
                placeholder="Type an industrial command or ask for status..."
                rows={1}
              />
              <div className="absolute right-3 bottom-3 flex gap-2">
                <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className="p-2 bg-[#137fec] text-white rounded-lg hover:bg-blue-600 transition-colors shadow-lg shadow-[#137fec]/30 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="material-symbols-outlined text-[20px]">send</span>
                </button>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between px-2">
              <div className="flex gap-4">
                <button className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400 hover:text-[#137fec] transition-colors uppercase tracking-widest">
                  <span className="material-symbols-outlined text-[16px]">attach_file</span>
                  Attach Logic
                </button>
                <button className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400 hover:text-[#137fec] transition-colors uppercase tracking-widest">
                  <span className="material-symbols-outlined text-[16px]">mic</span>
                  Voice Cmd
                </button>
              </div>
              <p className="text-[10px] text-slate-400 italic">Press Enter to dispatch, Shift+Enter for new line</p>
            </div>
          </div>
        </div>

        {/* Background Gradient Overlay (Minimalist Claude style) */}
        <div className="absolute inset-0 pointer-events-none opacity-5 dark:opacity-[0.03] bg-gradient-to-tr from-[#137fec] via-transparent to-transparent"></div>
      </main>
    </div>
  );
}
