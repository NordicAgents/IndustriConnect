import { WebSocketServer, WebSocket } from 'ws';
import { MCPServerManager } from './mcp-manager.js';
import {
    WSMessage,
    SpawnServerMessage,
    ListToolsMessage,
    CallToolMessage,
    DisconnectServerMessage,
    ServerSpawnedMessage,
    ToolsListedMessage,
    ToolResultMessage,
    ErrorMessage,
} from './types.js';

export class MCPWebSocketServer {
    private wss: WebSocketServer;
    private mcpManager: MCPServerManager;

    constructor(serverOrPort: any) {
        if (typeof serverOrPort === 'number') {
             this.wss = new WebSocketServer({ port: serverOrPort });
             console.log(`[WS] WebSocket server started on port ${serverOrPort}`);
        } else {
             this.wss = new WebSocketServer({ server: serverOrPort });
             console.log(`[WS] WebSocket server attached to HTTP server`);
        }

        this.mcpManager = new MCPServerManager();

        this.wss.on('connection', (ws) => {
            console.log('[WS] Client connected');
            this.handleConnection(ws);
        });
    }

    private handleConnection(ws: WebSocket) {
        ws.on('message', async (data) => {
            try {
                const message = JSON.parse(data.toString()) as WSMessage;
                await this.handleMessage(ws, message);
            } catch (error) {
                console.error('[WS] Error handling message:', error);
                this.sendError(ws, 'Invalid message format');
            }
        });

        ws.on('close', () => {
            console.log('[WS] Client disconnected');
            // Optional: Cleanup servers if they should be tied to the connection
            // this.mcpManager.cleanup(); 
        });
    }

    private async handleMessage(ws: WebSocket, message: WSMessage) {
        console.log(`[WS] Received message: ${message.type}`);

        switch (message.type) {
            case 'spawn_server':
                await this.handleSpawnServer(ws, message as SpawnServerMessage);
                break;

            case 'list_tools':
                await this.handleListTools(ws, message as ListToolsMessage);
                break;

            case 'call_tool':
                await this.handleCallTool(ws, message as CallToolMessage);
                break;

            case 'disconnect_server':
                await this.handleDisconnectServer(ws, message as DisconnectServerMessage);
                break;

            default:
                console.warn(`[WS] Unknown message type: ${message.type}`);
                this.sendError(ws, `Unknown message type: ${message.type}`);
        }
    }

    private async handleSpawnServer(ws: WebSocket, message: SpawnServerMessage) {
        const { serverId, serverName, config } = message;

        const result = await this.mcpManager.spawnServer(serverId, serverName, config);

        if (result.success) {
            const response: ServerSpawnedMessage = {
                type: 'server_spawned',
                serverId,
                status: 'connected',
            };
            this.send(ws, response);

            // Also send the initial tools list if available
            if (result.tools) {
                const toolsResponse: ToolsListedMessage = {
                    type: 'tools_listed',
                    serverId,
                    tools: result.tools,
                };
                this.send(ws, toolsResponse);
            }
        } else {
            const response: ServerSpawnedMessage = {
                type: 'server_spawned',
                serverId,
                status: 'error',
                error: result.error,
            };
            this.send(ws, response);
        }
    }

    private async handleListTools(ws: WebSocket, message: ListToolsMessage) {
        const { serverId } = message;

        try {
            const tools = await this.mcpManager.listTools(serverId);
            const response: ToolsListedMessage = {
                type: 'tools_listed',
                serverId,
                tools,
            };
            this.send(ws, response);
        } catch (error) {
            this.sendError(ws, error instanceof Error ? error.message : 'Failed to list tools', serverId);
        }
    }

    private async handleCallTool(ws: WebSocket, message: CallToolMessage) {
        const { serverId, toolName, arguments: args } = message;

        try {
            const result = await this.mcpManager.callTool(serverId, toolName, args);
            const response: ToolResultMessage = {
                type: 'tool_result',
                serverId,
                toolName,
                success: true,
                result,
            };
            this.send(ws, response);
        } catch (error) {
            const response: ToolResultMessage = {
                type: 'tool_result',
                serverId,
                toolName,
                success: false,
                error: error instanceof Error ? error.message : 'Tool execution failed',
            };
            this.send(ws, response);
        }
    }

    private async handleDisconnectServer(ws: WebSocket, message: DisconnectServerMessage) {
        const { serverId } = message;
        await this.mcpManager.disconnectServer(serverId);
        // No response needed, client assumes disconnection
    }

    private send(ws: WebSocket, message: WSMessage) {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    }

    private sendError(ws: WebSocket, errorMessage: string, serverId?: string) {
        const response: ErrorMessage = {
            type: 'error',
            message: errorMessage,
            serverId,
        };
        this.send(ws, response);
    }
}
