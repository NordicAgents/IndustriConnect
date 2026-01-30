# Build stage for Frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/ui
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Build stage for Backend & Runner
FROM node:18-alpine

# Install python/uv for MCP servers if needed (IndustriConnect requirement)
RUN apk add --no-cache python3 py3-pip
# Install uv (optional, if we want to run python MCP servers inside this container)
RUN pip install uv

WORKDIR /app/mcp-backend

# Copy backend dependencies
COPY mcp-backend/package*.json ./
RUN npm ci

# Copy backend source
COPY mcp-backend/ ./

# Copy built frontend assets to 'public' folder in backend
COPY --from=frontend-build /app/ui/dist ./public

# Build backend (TypeScript -> JS)
RUN npm run build

# Expose ports
# Render usually only respects one PORT env var for the web service.
# But we have HTTP (3002) and WS (3003).
# Ideally, we should run WS on the SAME server (upgrade req) or use a start script.
# For simplicity, we'll expose both but Render might only route to one.
# ACTUALLY, Render websockets work on the main port.
# So we should combine them or just run them as is.
# NOTE: The current code starts two separate servers (Express on 3002, WS on 3003).
# On Render, you get ONE port (env.PORT).
# We need to unify them or use a start script that sets PORT to 3002 and WS_PORT to something else,
# but only the main PORT is public.
#
# Correction: To work on Render standard Web Service, we need One Port.
# I should attach WebSocketServer to the Express HTTP server.

EXPOSE 3002
EXPOSE 3003

# Start command
CMD ["npm", "start"]
