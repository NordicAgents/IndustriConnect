import { ChatMessage, CloudLLMConfig, OllamaConfig } from '../types';
import { MCPTool, MCPToolCall } from '../types/mcp-types';
import { mcpClientManager } from './mcp-client';

const buildToolSystemMessage = (mcpTools: MCPTool[]): string | null => {
  if (mcpTools.length === 0) {
    return null;
  }

  return (
    'You have access to external MCP tools for industrial protocols (MQTT, OPC UA, etc.). ' +
    'Use these tools whenever the user asks you to read, write, browse, or call methods on field devices, PLCs, or other industrial systems, ' +
    'instead of guessing.\n\n' +
    'OPC UA NodeId reminder: numeric ids use the form ns=<namespace>;i=<integer> (for example, ns=2;i=2). ' +
    'String ids must use ns=<namespace>;s=<string> (for example, ns=2;s=TEMP_NODE_ID). ' +
    'Never put non-numeric values after i=.\n\n' +
    'Available tools:\n' +
    mcpTools
      .map(
        (tool) =>
          `- ${tool.name}${tool.description ? `: ${tool.description}` : ''}`,
      )
      .join('\n')
  );
};

const createToolCallId = () =>
  `tool-${Date.now()}-${Math.random().toString(16).slice(2)}`;

const parseToolArguments = (args: unknown): Record<string, any> => {
  if (!args) {
    return {};
  }

  if (typeof args === 'string') {
    try {
      return JSON.parse(args) as Record<string, any>;
    } catch (error) {
      console.warn('Failed to parse tool arguments string', error);
      return {};
    }
  }

  if (typeof args === 'object') {
    return args as Record<string, any>;
  }

  return {};
};

const resolveMCPToolServer = (
  functionName: string,
): { serverId: string; serverName: string } | null => {
  const servers = mcpClientManager.getServers();

  for (const server of servers) {
    if (server.tools?.some((tool) => tool.name === functionName)) {
      return { serverId: server.id, serverName: server.name };
    }
  }

  return null;
};

const executeMCPToolCall = async (
  functionName: string,
  functionArgs: Record<string, any>,
  id?: string,
): Promise<MCPToolCall | null> => {
  const resolvedServer = resolveMCPToolServer(functionName);

  if (!resolvedServer) {
    console.error(`Tool ${functionName} not found in any connected MCP server`);
    return null;
  }

  const result = await mcpClientManager.callTool(
    resolvedServer.serverId,
    functionName,
    functionArgs,
  );

  return {
    id: id || createToolCallId(),
    toolName: functionName,
    serverId: resolvedServer.serverId,
    serverName: resolvedServer.serverName,
    arguments: functionArgs,
    result,
    timestamp: new Date(),
  };
};

const formatToolResults = (toolCalls: MCPToolCall[]) =>
  toolCalls
    .map((toolCall) => {
      const resultText =
        toolCall.result?.content?.[0]?.text ||
        JSON.stringify(toolCall.result);
      return `Tool ${toolCall.toolName} result: ${resultText}`;
    })
    .join('\n\n');

const buildPromptFromMessages = (messages: ChatMessage[]): string => {
  const sorted = [...messages].sort(
    (a, b) => a.timestamp.getTime() - b.timestamp.getTime(),
  );

  return sorted
    .map((message) => {
      const label =
        message.role === 'user'
          ? 'User'
          : message.role === 'assistant'
            ? 'Assistant'
            : 'System';
      return `${label}: ${message.content}`;
    })
    .join('\n\n');
};

const getCloudApiKey = (config: CloudLLMConfig): string => {
  if (config.apiKey) {
    return config.apiKey;
  }

  let envKey: string | undefined;
  if (config.provider === 'openai') {
    envKey = import.meta.env.VITE_OPENAI_API_KEY as string | undefined;
  } else if (config.provider === 'gemini') {
    envKey = import.meta.env.VITE_GEMINI_API_KEY as string | undefined;
  } else if (config.provider === 'anthropic') {
    envKey = import.meta.env.VITE_ANTHROPIC_API_KEY as string | undefined;
  }

  if (!envKey) {
    throw new Error(
      'No API key configured. Set it in a .env file (VITE_OPENAI_API_KEY / VITE_GEMINI_API_KEY / VITE_ANTHROPIC_API_KEY) or enter it in the UI.',
    );
  }

  return envKey;
};

/**
 * Convert MCP tools to OpenAI function format
 */
const convertMCPToolsToOpenAI = (mcpTools: MCPTool[]) => {
  return mcpTools.map(tool => ({
    type: 'function' as const,
    function: {
      name: tool.name,
      description: tool.description || '',
      parameters: tool.inputSchema,
    },
  }));
};

const convertMCPToolsToGemini = (mcpTools: MCPTool[]) => {
  return [
    {
      functionDeclarations: mcpTools.map((tool) => ({
        name: tool.name,
        description: tool.description || '',
        parameters: tool.inputSchema,
      })),
    },
  ];
};

const convertMCPToolsToAnthropic = (mcpTools: MCPTool[]) => {
  return mcpTools.map((tool) => ({
    name: tool.name,
    description: tool.description || '',
    input_schema: tool.inputSchema,
  }));
};

/**
 * Call OpenAI with support for MCP tools
 */
const callOpenAIChat = async (
  messages: ChatMessage[],
  config: CloudLLMConfig,
  mcpTools: MCPTool[] = [],
): Promise<{ content: string; toolCalls?: MCPToolCall[] }> => {
  const baseUrl = (config.baseUrl || 'https://api.openai.com/v1').replace(
    /\/$/,
    '',
  );

  const apiKey = getCloudApiKey(config);

  // Convert chat messages to OpenAI format
  const toolSystemMessage = buildToolSystemMessage(mcpTools);

  const openaiMessages = [
    ...(toolSystemMessage
      ? [{ role: 'system', content: toolSystemMessage }]
      : []),
    ...messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    })),
  ];

  const requestBody: any = {
    model: config.model,
    messages: openaiMessages,
  };

  // Add tools if available
  if (mcpTools.length > 0) {
    requestBody.tools = convertMCPToolsToOpenAI(mcpTools);
    requestBody.tool_choice = 'auto';
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `OpenAI error (${response.status})`);
  }

  const data: any = await response.json();
  const choice = data?.choices?.[0];

  if (!choice) {
    throw new Error('OpenAI returned no choices');
  }

  // Check if the model wants to call tools
  if (choice.message?.tool_calls && choice.message.tool_calls.length > 0) {
    const toolCalls: MCPToolCall[] = [];

    // Execute each tool call
    for (const toolCall of choice.message.tool_calls) {
      const functionName = toolCall.function?.name;

      if (!functionName) {
        continue;
      }

      const functionArgs = parseToolArguments(toolCall.function?.arguments);
      const executed = await executeMCPToolCall(
        functionName,
        functionArgs,
        toolCall.id,
      );

      if (executed) {
        toolCalls.push(executed);
      }
    }

    // Format tool results as text for the response
    const toolResultsText = formatToolResults(toolCalls);

    return {
      content: toolResultsText || 'Tools executed successfully',
      toolCalls,
    };
  }

  // No tool calls, return regular response
  const content = choice.message?.content?.toString().trim() || '';

  if (!content) {
    throw new Error('OpenAI returned an empty response');
  }

  return { content };
};


/**
 * Get all available MCP tools from connected servers
 */
const getAllMCPTools = (): MCPTool[] => {
  const allTools: MCPTool[] = [];
  const servers = mcpClientManager.getServers();

  for (const server of servers) {
    if (server.status === 'connected' && server.tools) {
      allTools.push(...server.tools);
    }
  }

  return allTools;
};

const callGemini = async (
  messages: ChatMessage[],
  config: CloudLLMConfig,
  mcpTools: MCPTool[] = [],
): Promise<{ content: string; toolCalls?: MCPToolCall[] }> => {
  const toolSystemMessage = buildToolSystemMessage(mcpTools);
  const basePrompt = buildPromptFromMessages(messages);
  const prompt = toolSystemMessage
    ? `${toolSystemMessage}\n\n${basePrompt}`
    : basePrompt;
  const apiKey = getCloudApiKey(config);

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
    config.model,
  )}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const requestBody: any = {
    contents: [
      {
        parts: [{ text: prompt }],
      },
    ],
  };

  if (mcpTools.length > 0) {
    requestBody.tools = convertMCPToolsToGemini(mcpTools);
    requestBody.toolConfig = {
      functionCallingConfig: {
        mode: 'AUTO',
      },
    };
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Gemini error (${response.status})`);
  }

  const data: any = await response.json();
  const responseParts = data?.candidates?.[0]?.content?.parts || [];
  const textParts: string[] = responseParts
    .map((part: any) => part?.text)
    .filter(Boolean);

  const toolCalls: MCPToolCall[] = [];

  for (const part of responseParts) {
    if (part?.functionCall?.name) {
      const functionName = part.functionCall.name as string;
      const functionArgs = parseToolArguments(part.functionCall.args);
      const executed = await executeMCPToolCall(functionName, functionArgs);
      if (executed) {
        toolCalls.push(executed);
      }
    }
  }

  const contentParts = [];
  if (textParts.length > 0) {
    contentParts.push(textParts.join(' ').trim());
  }
  if (toolCalls.length > 0) {
    contentParts.push(formatToolResults(toolCalls));
  }

  const content = contentParts.join('\n\n').trim();

  if (!content) {
    throw new Error('Gemini returned an empty response');
  }

  return toolCalls.length > 0 ? { content, toolCalls } : { content };
};

const callAnthropic = async (
  messages: ChatMessage[],
  config: CloudLLMConfig,
  mcpTools: MCPTool[] = [],
): Promise<{ content: string; toolCalls?: MCPToolCall[] }> => {
  const apiKey = getCloudApiKey(config);
  const toolSystemMessage = buildToolSystemMessage(mcpTools);
  const systemMessages = messages
    .filter((message) => message.role === 'system')
    .map((message) => message.content);
  const systemText = [toolSystemMessage, ...systemMessages]
    .filter(Boolean)
    .join('\n\n');
  const filteredMessages = messages.filter(
    (message) => message.role === 'user' || message.role === 'assistant',
  );

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: config.model,
      max_tokens: 1024,
      system: systemText || undefined,
      messages: filteredMessages.map((message) => ({
        role: message.role,
        content: [
          {
            type: 'text',
            text: message.content,
          },
        ],
      })),
      tools: mcpTools.length > 0 ? convertMCPToolsToAnthropic(mcpTools) : undefined,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Anthropic error (${response.status})`);
  }

  const data: any = await response.json();
  const contentBlocks = data?.content || [];
  const textBlocks = contentBlocks
    .filter((block: any) => block?.type === 'text')
    .map((block: any) => block?.text)
    .filter(Boolean);
  const toolCalls: MCPToolCall[] = [];

  for (const block of contentBlocks) {
    if (block?.type === 'tool_use' && block?.name) {
      const functionName = block.name as string;
      const functionArgs = parseToolArguments(block.input);
      const executed = await executeMCPToolCall(
        functionName,
        functionArgs,
        block.id,
      );
      if (executed) {
        toolCalls.push(executed);
      }
    }
  }

  const contentParts = [];
  if (textBlocks.length > 0) {
    contentParts.push(textBlocks.join(' ').trim());
  }
  if (toolCalls.length > 0) {
    contentParts.push(formatToolResults(toolCalls));
  }
  const content = contentParts.join('\n\n').trim();

  if (!content) {
    throw new Error('Anthropic returned an empty response');
  }

  return toolCalls.length > 0 ? { content, toolCalls } : { content };
};

export const callCloudLLM = async (
  messages: ChatMessage[],
  config: CloudLLMConfig,
): Promise<{ content: string; toolCalls?: MCPToolCall[] }> => {
  // Get available MCP tools
  const mcpTools = getAllMCPTools();

  switch (config.provider) {
    case 'openai':
      return callOpenAIChat(messages, config, mcpTools);
    case 'gemini':
      return callGemini(messages, config, mcpTools);
    case 'anthropic':
      return callAnthropic(messages, config, mcpTools);
    default:
      throw new Error(`Unsupported cloud provider: ${config.provider}`);
  }
};

export const callOllama = async (
  messages: ChatMessage[],
  config: OllamaConfig,
): Promise<{ content: string; toolCalls?: MCPToolCall[] }> => {
  const baseUrl = (config.baseUrl || 'http://localhost:11434').replace(
    /\/$/,
    '',
  );
  const mcpTools = getAllMCPTools();
  const toolSystemMessage = buildToolSystemMessage(mcpTools);

  const ollamaMessages = [
    ...(toolSystemMessage
      ? [{ role: 'system', content: toolSystemMessage }]
      : []),
    ...messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
  ];

  const requestBody: any = {
    model: config.model,
    messages: ollamaMessages,
    stream: false,
  };

  if (mcpTools.length > 0) {
    requestBody.tools = convertMCPToolsToOpenAI(mcpTools);
  }

  const response = await fetch(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Ollama error (${response.status})`);
  }

  const data: any = await response.json();
  const toolCallData = data?.message?.tool_calls || [];
  const toolCalls: MCPToolCall[] = [];

  if (Array.isArray(toolCallData) && toolCallData.length > 0) {
    for (const toolCall of toolCallData) {
      const functionName =
        toolCall?.function?.name || toolCall?.name || toolCall?.tool?.name;
      if (!functionName) {
        continue;
      }
      const functionArgs = parseToolArguments(
        toolCall?.function?.arguments || toolCall?.arguments,
      );
      const executed = await executeMCPToolCall(
        functionName,
        functionArgs,
        toolCall?.id,
      );
      if (executed) {
        toolCalls.push(executed);
      }
    }
  }

  if (toolCalls.length > 0) {
    return {
      content: formatToolResults(toolCalls) || 'Tools executed successfully',
      toolCalls,
    };
  }

  const content = data?.message?.content?.toString().trim() || '';

  if (!content) {
    throw new Error('Ollama returned an empty response');
  }

  return { content };
};
