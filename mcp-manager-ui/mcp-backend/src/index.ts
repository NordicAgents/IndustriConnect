import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer } from 'http';
import { MCPWebSocketServer } from './websocket-server.js';

// Reconstruct __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// On Render, PORT is provided. Default to 3000 if not.
const PORT = parseInt(process.env.PORT || '3000', 10);

// Start Express server
const app = express();
app.use(cors());
app.use(express.json());

// Create HTTP server
const server = createServer(app);

// Serve static files from the 'public' directory
const publicPath = path.join(process.cwd(), 'public');
app.use(express.static(publicPath));

app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'mcp-backend' });
});

// Fallback to index.html for SPA routing
app.get('*', (req, res) => {
    res.sendFile(path.join(publicPath, 'index.html'));
});

// Start WebSocket server attached to the SAME HTTP server
// We need to modify MCPWebSocketServer to accept an existing server instance
// OR we just pass the server to it.
// Let's modify websocket-server.ts to support attaching to a server.

// Temporarily, let's see how MCPWebSocketServer is implemented.
// It creates a new WebSocketServer({ port }).
// We need it to be WebSocketServer({ server }).

server.listen(PORT, '0.0.0.0', () => {
    console.log(`[HTTP+WS] Server running on http://0.0.0.0:${PORT}`);
});

// Initialize WS server (we'll need to update the class)
new MCPWebSocketServer(server);
