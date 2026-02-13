# IndustriConnect Whitepaper Technical Figures

This directory contains a comprehensive suite of technical diagrams for the IndustriConnect whitepaper, illustrating the system's architecture, operation, and integration patterns.

## Figure Overview

### 01_architecture_diagram.png
**Complete System Topology**

Shows the full four-layer architecture of IndustriConnect:

1. **User Interface Layer**: Human operators interact through MCP Manager UI (React + TypeScript), Claude Desktop, or other MCP clients
2. **AI Coordination Layer**: Local LLMs (Ollama) and cloud providers (OpenAI, Anthropic, Gemini) work with the MCP Client Manager for tool discovery and routing
3. **MCP Protocol Layer**: 9 protocol-specific MCP servers (OPC UA, Modbus, MQTT, S7comm, BACnet, DNP3, EtherNet/IP, EtherCAT, PROFIBUS) provide standardized interfaces
4. **Industrial Equipment Layer**: PLCs, sensors, DCS/SCADA systems, IoT gateways, and actuators from major vendors

**Key Elements:**
- Security layer with authentication, authorization, and audit logging
- Write protection and system command controls
- Environment-based configuration management
- WebSocket communication (ws://localhost:3001)
- stdio transport between MCP Client and Servers

### 02_use_case_diagram.png
**Primary Interaction Patterns**

Illustrates four main use cases showing interaction between human operators, AI agents, and industrial equipment:

1. **Real-Time Monitoring** (Blue)
   - Continuous data collection and trend analysis
   - Example: "What's the current tank level?"
   - Tools: `read_opcua_node`, `read_tag`, `browse_nodes`

2. **Predictive Maintenance** (Orange)
   - Vibration analysis and failure prediction
   - Example: "Analyze motor M-205 vibration patterns"
   - Tools: `read_multiple_registers`, `trend_analysis`, `read_szl`

3. **Process Optimization** (Green)
   - Setpoint adjustments and efficiency improvements
   - Example: "Optimize reactor temperature"
   - Tools: `write_register`, `call_method`, `process_analysis`

4. **Anomaly Detection** (Red)
   - Real-time alarm detection and automated response
   - Example: Temperature threshold exceeded → emergency cooling
   - Tools: `write_coil`, `notify_operator`, `detect_anomaly`

### 03_process_flow_diagram.png
**Request Flow Through System**

Depicts the complete 14-step data flow from user query to response:

**Request Path:**
1. User Query → Natural language question
2. Intent Analysis → LLM parses and identifies intent
3. Tool Selection → Match to available MCP tools
4. MCP Request → Format tool call with parameters
5. Server Routing → Route to appropriate MCP server
6. Protocol Translation → Convert MCP to industrial protocol
7. Device Communication → TCP/Serial connection
8. Sensor Reading → Physical device polling

**Response Path:**
9. Response Data → Raw binary/integer values
10. Data Transformation → Scaling and offset application
11. MCP Response → JSON formatted result
12. Tool Result → Parse and validate
13. LLM Integration → Incorporate into natural language
14. User Response → Formatted answer

### 04_connection_topology_diagram.png
**MCP Protocol Translation & Communication**

Shows how MCP facilitates communication between locally deployed LLMs and diverse industrial machinery:

**Left Side - LLM Clients:**
- Ollama (Local deployment)
- OpenAI GPT-4 (Cloud)
- Anthropic Claude (Cloud)
- Google Gemini (Cloud)

**Right Side - Protocol Adapters:**
Python libraries that handle protocol specifics:
- `opcua` - OPC UA client
- `pymodbus` - Modbus master
- `paho-mqtt` - MQTT client
- `python-snap7` - S7 protocol
- `BAC0` - BACnet/IP
- `dnp3` - DNP3 master
- `pycomm3` - EtherNet/IP
- `PySOEM` - EtherCAT master

**Key Features:**
- Real-time data streaming via WebSocket
- Publish/Subscribe patterns with MQTT
- Protocol translation: MCP JSON ↔ Binary protocols
- Security layer with authentication and audit logging

### 05_agent_interaction_diagram.png
**Multi-Agent Collaboration Patterns**

Illustrates how multiple AI agents collaborate to handle complex industrial operations:

**Orchestrator Agent** (Center)
- Task analysis and decomposition
- Agent selection and coordination
- Result aggregation and synthesis

**Specialized Agents:**
1. **Monitoring Agent** - Real-time data collection
2. **Maintenance Agent** - Predictive analysis
3. **Optimization Agent** - Process tuning
4. **Safety Agent** - Anomaly detection

**Collaboration Patterns:**
- Sequential: Agent A → Agent B → Agent C
- Parallel: Agents A, B, C simultaneously
- Hierarchical: Orchestrator delegates to specialized agents
- Consensus: Multiple agents vote on critical decisions

## Technical Specifications

- **Format**: PNG (300 DPI print quality)
- **Color Mode**: RGB
- **Size**: Each figure is approximately 500KB-700KB

### Color Scheme
- Primary Blue (#2563EB): Main coordination layer
- Secondary Green (#059669): AI components
- Accent Red (#DC2626): Alerts and safety
- Warning Orange (#D97706): Predictive maintenance
- Industrial Blue (#1E40AF): Equipment and protocols
- Protocol Orange (#D97706): MCP protocol layer
- Purple (#7C3AED): Orchestrator and special components

## Regenerating Figures

To regenerate all figures:

```bash
cd /Users/mx/Documents/Work/industriAgents/IndustriConnect-MCPs/whitepaper/figures
python3 generate_figures.py
```

Requirements:
- Python 3.8+
- matplotlib
- numpy

Install dependencies:
```bash
pip install matplotlib numpy
```

## Figure Checklist

- [x] Architecture diagram - Complete system topology
- [x] Use case diagram - Primary interaction patterns  
- [x] Process flow diagram - Request flow through system
- [x] Connection topology - MCP protocol translation
- [x] Agent interaction diagram - Multi-agent collaboration