#!/usr/bin/env python3
"""
IndustriConnect Whitepaper Technical Figures Generator
Creates comprehensive technical diagrams for the whitepaper.

Requirements:
    pip install matplotlib numpy graphviz pillow

Usage:
    python generate_whitepaper_figures.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
import numpy as np
from matplotlib.lines import Line2D
import os

# Set up output directory
OUTPUT_DIR = "/Users/mx/Documents/Work/industriAgents/IndustriConnect-MCPs/whitepaper/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Professional color scheme
COLORS = {
    'primary': '#2563EB',      # Blue
    'secondary': '#059669',    # Green
    'accent': '#DC2626',       # Red
    'warning': '#D97706',      # Orange
    'neutral': '#6B7280',      # Gray
    'light': '#F3F4F6',        # Light gray
    'dark': '#1F2937',         # Dark gray
    'purple': '#7C3AED',       # Purple
    'teal': '#0891B2',         # Teal
    'pink': '#DB2777',         # Pink
    'industrial': '#1E40AF',   # Industrial blue
    'ai': '#059669',           # AI green
    'protocol': '#D97706',     # Protocol orange
}

def save_figure(fig, filename, dpi=300):
    """Save figure with proper formatting"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    print(f"✓ Saved: {filepath}")
    plt.close(fig)

def create_architecture_diagram():
    """Figure 1: Complete System Architecture Topology - Clean Version"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 12))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Title
    ax.text(10, 11.5, 'IndustriConnect System Architecture', 
            fontsize=20, fontweight='bold', ha='center')
    ax.text(10, 11.1, 'Four-Layer Architecture with IndustriConnect Protocol Integration',
            fontsize=12, ha='center', style='italic', color=COLORS['neutral'])
    
    # Define layer positions and dimensions
    layer_height = 2.2
    layer_spacing = 0.3
    
    # Layer 1: User Interface (Top)
    y1 = 8.5
    rect1 = FancyBboxPatch((0.5, y1), 19, layer_height, boxstyle="round,pad=0.05",
                          facecolor='#E8F4FD', edgecolor='#2563EB', 
                          linewidth=2, alpha=0.9)
    ax.add_patch(rect1)
    ax.text(1.0, y1 + layer_height - 0.3, 'LAYER 1: USER INTERFACE', 
            fontsize=10, fontweight='bold', color='#1E40AF')
    
    # User Interface components
    # Human Operator
    op_box = FancyBboxPatch((1.0, y1 + 0.3), 2.5, 1.5, boxstyle="round,pad=0.03",
                           facecolor='#FEE2E2', edgecolor='#DC2626', linewidth=2)
    ax.add_patch(op_box)
    ax.text(2.25, y1 + 1.2, 'OPERATOR', fontsize=10, ha='center', fontweight='bold', color='#991B1B')
    ax.text(2.25, y1 + 0.7, 'Human User', fontsize=9, ha='center')
    
    # IndustriConnect Manager UI
    ui_box = FancyBboxPatch((4.0, y1 + 0.3), 4.0, 1.5, boxstyle="round,pad=0.03",
                           facecolor='white', edgecolor='#2563EB', linewidth=2)
    ax.add_patch(ui_box)
    ax.text(6.0, y1 + 1.4, 'IndustriConnect Manager UI', fontsize=11, ha='center', fontweight='bold', color='#1E40AF')
    ax.text(6.0, y1 + 1.0, 'React + TypeScript', fontsize=8, ha='center', color=COLORS['neutral'])
    ax.text(6.0, y1 + 0.6, 'Chat & Dashboard', fontsize=8, ha='center')
    
    # Claude Desktop
    claude_box = FancyBboxPatch((8.5, y1 + 0.3), 3.5, 1.5, boxstyle="round,pad=0.03",
                               facecolor='#F3E8FF', edgecolor='#7C3AED', linewidth=2)
    ax.add_patch(claude_box)
    ax.text(10.25, y1 + 1.2, 'Claude Desktop', fontsize=10, ha='center', fontweight='bold', color='#5B21B6')
    ax.text(10.25, y1 + 0.7, 'IndustriConnect Client', fontsize=9, ha='center')
    
    # Other Clients
    other_box = FancyBboxPatch((12.5, y1 + 0.3), 6.5, 1.5, boxstyle="round,pad=0.03",
                              facecolor='#F3F4F6', edgecolor='#6B7280', linewidth=2)
    ax.add_patch(other_box)
    ax.text(15.75, y1 + 1.3, 'Other IndustriConnect Clients', fontsize=10, ha='center', fontweight='bold')
    ax.text(14.0, y1 + 0.9, 'VS Code', fontsize=8, ha='center')
    ax.text(15.75, y1 + 0.9, 'Custom Apps', fontsize=8, ha='center')
    ax.text(17.5, y1 + 0.9, 'APIs', fontsize=8, ha='center')
    ax.text(15.75, y1 + 0.5, 'WebSocket: ws://localhost:3001', fontsize=8, ha='center', 
            family='monospace', color=COLORS['neutral'])
    
    # Connection arrows - Layer 1 to Layer 2
    ax.annotate('', xy=(6.0, y1), xytext=(6.0, y1 + 0.3),
                arrowprops=dict(arrowstyle='->', color='#2563EB', lw=2))
    ax.annotate('', xy=(10.25, y1), xytext=(10.25, y1 + 0.3),
                arrowprops=dict(arrowstyle='->', color='#7C3AED', lw=2))
    
    # Layer 2: AI Coordination
    y2 = y1 - layer_height - layer_spacing
    rect2 = FancyBboxPatch((0.5, y2), 19, layer_height, boxstyle="round,pad=0.05",
                          facecolor='#D1FAE5', edgecolor='#059669', 
                          linewidth=2, alpha=0.9)
    ax.add_patch(rect2)
    ax.text(1.0, y2 + layer_height - 0.3, 'LAYER 2: AI COORDINATION', 
            fontsize=10, fontweight='bold', color='#065F46')
    
    # LLM Models box
    llm_box = FancyBboxPatch((1.0, y2 + 0.3), 5.5, 1.5, boxstyle="round,pad=0.03",
                            facecolor='white', edgecolor='#059669', linewidth=2)
    ax.add_patch(llm_box)
    ax.text(3.75, y2 + 1.4, 'LLM Models', fontsize=11, ha='center', fontweight='bold', color='#065F46')
    ax.text(2.0, y2 + 1.0, 'Ollama', fontsize=9, ha='center')
    ax.text(3.75, y2 + 1.0, 'OpenAI', fontsize=9, ha='center')
    ax.text(5.5, y2 + 1.0, 'Anthropic', fontsize=9, ha='center')
    ax.text(3.75, y2 + 0.6, 'Tool Selection | Function Calling | Response Gen', fontsize=8, 
            ha='center', color=COLORS['neutral'])
    
    # IndustriConnect Client Manager box
    mcp_box = FancyBboxPatch((7.0, y2 + 0.3), 7.0, 1.5, boxstyle="round,pad=0.03",
                            facecolor='white', edgecolor='#2563EB', linewidth=2)
    ax.add_patch(mcp_box)
    ax.text(10.5, y2 + 1.4, 'IndustriConnect Client Manager', fontsize=11, ha='center', fontweight='bold', color='#1E40AF')
    ax.text(8.5, y2 + 1.0, 'Server Lifecycle', fontsize=8, ha='center')
    ax.text(10.5, y2 + 1.0, 'Tool Discovery', fontsize=8, ha='center')
    ax.text(12.5, y2 + 1.0, 'Request Routing', fontsize=8, ha='center')
    ax.text(10.5, y2 + 0.6, 'Node.js Backend + WebSocket Server', fontsize=8, 
            ha='center', color=COLORS['neutral'])
    
    # Security box
    sec_box = FancyBboxPatch((14.5, y2 + 0.3), 4.5, 1.5, boxstyle="round,pad=0.03",
                            facecolor='#FEF3C7', edgecolor='#D97706', linewidth=2)
    ax.add_patch(sec_box)
    ax.text(16.75, y2 + 1.4, 'Security Layer', fontsize=11, ha='center', fontweight='bold', color='#92400E')
    ax.text(16.75, y2 + 1.0, 'Auth | Write Protection | Audit', fontsize=8, ha='center')
    ax.text(16.75, y2 + 0.6, 'Tag Maps | Environment Vars', fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Connection arrows - Layer 2 to Layer 3
    ax.annotate('', xy=(10.5, y2), xytext=(10.5, y2 - 0.1),
                arrowprops=dict(arrowstyle='->', color='#059669', lw=2))
    ax.text(11.2, y2 - 0.15, 'stdio Transport', fontsize=8, color=COLORS['neutral'], family='monospace')
    
    # Layer 3: IndustriConnect Protocol
    y3 = y2 - layer_height - layer_spacing
    rect3 = FancyBboxPatch((0.5, y3), 19, layer_height, boxstyle="round,pad=0.05",
                          facecolor='#FEF3C7', edgecolor='#D97706', 
                          linewidth=2, alpha=0.9)
    ax.add_patch(rect3)
    ax.text(1.0, y3 + layer_height - 0.3, 'LAYER 3: IndustriConnect PROTOCOL SERVERS', 
            fontsize=10, fontweight='bold', color='#92400E')
    
    # Protocol servers - row 1
    protocols_row1 = [
        ('OPC UA', 2.0),
        ('Modbus', 5.0),
        ('MQTT', 8.0),
        ('S7comm', 11.0),
        ('BACnet', 14.0),
    ]
    for name, x in protocols_row1:
        box = FancyBboxPatch((x-1.2, y3 + 0.9), 2.6, 0.9, boxstyle="round,pad=0.02",
                            facecolor='white', edgecolor='#D97706', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x+0.1, y3 + 1.4, name, fontsize=9, ha='center', fontweight='bold')
        ax.text(x+0.1, y3 + 1.1, 'IndustriConnect Server', fontsize=7, ha='center', color=COLORS['neutral'])
    
    # Protocol servers - row 2
    protocols_row2 = [
        ('DNP3', 3.5),
        ('EtherNet/IP', 7.0),
        ('EtherCAT', 10.5),
        ('PROFIBUS', 14.0),
    ]
    for name, x in protocols_row2:
        box = FancyBboxPatch((x-1.3, y3 + 0.2), 2.8, 0.6, boxstyle="round,pad=0.02",
                            facecolor='white', edgecolor='#D97706', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x+0.1, y3 + 0.55, name, fontsize=9, ha='center', fontweight='bold')
    
    ax.text(10, y3 + 0.05, 'Python + FastIndustriConnect Framework | Protocol Translation | Data Transformation',
            fontsize=9, ha='center', style='italic', color=COLORS['neutral'])
    
    # Connection arrows - Layer 3 to Layer 4
    ax.annotate('', xy=(10, y3), xytext=(10, y3 - 0.1),
                arrowprops=dict(arrowstyle='->', color='#D97706', lw=2))
    ax.text(10.8, y3 - 0.15, 'TCP/Serial', fontsize=8, color=COLORS['neutral'], family='monospace')
    
    # Layer 4: Industrial Equipment
    y4 = y3 - layer_height - layer_spacing
    rect4 = FancyBboxPatch((0.5, y4), 19, layer_height, boxstyle="round,pad=0.05",
                          facecolor='#DBEAFE', edgecolor='#1E40AF', 
                          linewidth=2, alpha=0.9)
    ax.add_patch(rect4)
    ax.text(1.0, y4 + layer_height - 0.3, 'LAYER 4: INDUSTRIAL EQUIPMENT (OT Network)', 
            fontsize=10, fontweight='bold', color='#1E3A8A')
    
    # Equipment types
    equipment = [
        ('PLCs', 2.5, ['Siemens S7', 'Rockwell', 'Schneider']),
        ('Sensors', 6.5, ['Temperature', 'Pressure', 'Flow']),
        ('DCS/SCADA', 10.5, ['Honeywell', 'Yokogawa']),
        ('IoT GW', 14.5, ['Edge Devices']),
        ('Actuators', 17.5, ['Motors', 'Valves']),
    ]
    
    for label, x, items in equipment:
        box = FancyBboxPatch((x-1.3, y4 + 0.3), 2.8, 1.5, boxstyle="round,pad=0.02",
                            facecolor='white', edgecolor='#1E40AF', linewidth=1.5)
        ax.add_patch(box)
        ax.text(x+0.1, y4 + 1.5, label, fontsize=10, ha='center', fontweight='bold', color='#1E40AF')
        for i, item in enumerate(items[:2]):  # Show max 2 items
            ax.text(x+0.1, y4 + 1.1 - i*0.35, item, fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Vertical connection lines between layers (showing data flow)
    # Left side flow indicators
    ax.annotate('', xy=(0.3, y2 + 1.0), xytext=(0.3, y1),
                arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.5, linestyle='--'))
    ax.text(0.15, (y1 + y2 + 1.0)/2, 'User\nQuery', fontsize=7, ha='center', color='#6B7280', rotation=90)
    
    ax.annotate('', xy=(0.3, y3 + 1.0), xytext=(0.3, y2),
                arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.5, linestyle='--'))
    ax.text(0.15, (y2 + y3 + 1.0)/2, 'Tool\nCall', fontsize=7, ha='center', color='#6B7280', rotation=90)
    
    ax.annotate('', xy=(0.3, y4 + 1.0), xytext=(0.3, y3),
                arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.5, linestyle='--'))
    ax.text(0.15, (y3 + y4 + 1.0)/2, 'Protocol\nCmd', fontsize=7, ha='center', color='#6B7280', rotation=90)
    
    # Right side flow indicators (response path)
    ax.annotate('', xy=(19.7, y3), xytext=(19.7, y4 + 1.0),
                arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.5, linestyle='--'))
    ax.text(19.85, (y3 + y4 + 1.0)/2, 'Sensor\nData', fontsize=7, ha='center', color='#6B7280', rotation=90)
    
    ax.annotate('', xy=(19.7, y2), xytext=(19.7, y3 + 1.0),
                arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.5, linestyle='--'))
    ax.text(19.85, (y2 + y3 + 1.0)/2, 'IndustriConnect\nResponse', fontsize=7, ha='center', color='#6B7280', rotation=90)
    
    ax.annotate('', xy=(19.7, y1), xytext=(19.7, y2 + 1.0),
                arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.5, linestyle='--'))
    ax.text(19.85, (y1 + y2 + 1.0)/2, 'AI\nResponse', fontsize=7, ha='center', color='#6B7280', rotation=90)
    
    # Layer labels on right side
    layer_labels = [
        (y1 + 1.0, 'UI Layer'),
        (y2 + 1.0, 'AI Layer'),
        (y3 + 1.0, 'IndustriConnect Layer'),
        (y4 + 1.0, 'OT Layer'),
    ]
    
    save_figure(fig, '01_architecture_diagram.png')


def create_use_case_diagram():
    """Figure 2: Use Case Diagram - Primary Interaction Patterns"""
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Title
    ax.text(9, 13.5, 'IndustriConnect Use Cases', 
            fontsize=24, fontweight='bold', ha='center')
    ax.text(9, 13.0, 'Interaction Patterns Between Operators, AI Agents, and Industrial Equipment',
            fontsize=14, ha='center', style='italic', color=COLORS['neutral'])
    
    # Actors (on the sides)
    # Human Operator (left)
    ax.text(1.0, 9.5, '👤', fontsize=50, ha='center')
    ax.text(1.0, 8.5, 'Human\nOperator', fontsize=12, ha='center', fontweight='bold')
    ax.plot([1.0, 1.0], [8.2, 1.5], color=COLORS['accent'], lw=2, linestyle='--')
    
    # AI Agent System (center-left)
    ax.text(5.5, 9.5, '🤖', fontsize=50, ha='center')
    ax.text(5.5, 8.5, 'AI Agent\nSystem', fontsize=12, ha='center', fontweight='bold')
    ax.plot([5.5, 5.5], [8.2, 1.5], color=COLORS['ai'], lw=2, linestyle='--')
    
    # Industrial Equipment (right)
    ax.text(16.0, 9.5, '⚙️', fontsize=50, ha='center')
    ax.text(16.0, 8.5, 'Industrial\nEquipment', fontsize=12, ha='center', fontweight='bold')
    ax.plot([16.0, 16.0], [8.2, 1.5], color=COLORS['industrial'], lw=2, linestyle='--')
    
    # Use Case 1: Real-time Monitoring
    uc1_y = 7.2
    uc1_box = FancyBboxPatch((3.0, uc1_y-0.4), 11.5, 1.0,
                              boxstyle="round,pad=0.05",
                              facecolor=COLORS['primary'] + '15',
                              edgecolor=COLORS['primary'], linewidth=2)
    ax.add_patch(uc1_box)
    ax.text(8.75, uc1_y+0.25, '1. Real-Time Monitoring', fontsize=13, 
            fontweight='bold', color=COLORS['primary'])
    ax.text(8.75, uc1_y-0.15, 'Continuous data collection, trend analysis, and status visualization',
            fontsize=9, ha='center', color=COLORS['neutral'])
    
    # Monitoring details
    mon_details = [
        'Query: "What is the current tank level?"',
        'AI: read_opcua_node("ns=2;i=1001")',
        'Response: "Tank T-101 level is 78.5% (15,700 L)"'
    ]
    for i, detail in enumerate(mon_details):
        ax.text(4.0, uc1_y-0.55-i*0.25, detail, fontsize=8, 
               family='monospace', color=COLORS['dark'])
    
    # Use Case 2: Predictive Maintenance
    uc2_y = 5.5
    uc2_box = FancyBboxPatch((3.0, uc2_y-0.4), 11.5, 1.0,
                              boxstyle="round,pad=0.05",
                              facecolor=COLORS['warning'] + '15',
                              edgecolor=COLORS['warning'], linewidth=2)
    ax.add_patch(uc2_box)
    ax.text(8.75, uc2_y+0.25, '2. Predictive Maintenance', fontsize=13,
            fontweight='bold', color=COLORS['warning'])
    ax.text(8.75, uc2_y-0.15, 'Vibration analysis, temperature trends, failure prediction',
            fontsize=9, ha='center', color=COLORS['neutral'])
    
    maint_details = [
        'Query: "Analyze motor M-205 vibration patterns"',
        'AI: read_multiple_holding_registers(1, 1000, 10) + trend_analysis()',
        'Alert: "Unusual vibration detected. Maintenance recommended within 48 hours"'
    ]
    for i, detail in enumerate(maint_details):
        ax.text(4.0, uc2_y-0.55-i*0.25, detail, fontsize=8,
               family='monospace', color=COLORS['dark'])
    
    # Use Case 3: Process Optimization
    uc3_y = 3.8
    uc3_box = FancyBboxPatch((3.0, uc3_y-0.4), 11.5, 1.0,
                              boxstyle="round,pad=0.05",
                              facecolor=COLORS['secondary'] + '15',
                              edgecolor=COLORS['secondary'], linewidth=2)
    ax.add_patch(uc3_box)
    ax.text(8.75, uc3_y+0.25, '3. Process Optimization', fontsize=13,
            fontweight='bold', color=COLORS['secondary'])
    ax.text(8.75, uc3_y-0.15, 'Setpoint adjustments, control loop tuning, efficiency improvements',
            fontsize=9, ha='center', color=COLORS['neutral'])
    
    opt_details = [
        'Command: "Optimize reactor temperature for energy efficiency"',
        'AI: analyze_process_data() → write_register(1, 40001, 185)',
        'Result: "Temperature adjusted to 185°C. Estimated 12% energy savings"'
    ]
    for i, detail in enumerate(opt_details):
        ax.text(4.0, uc3_y-0.55-i*0.25, detail, fontsize=8,
               family='monospace', color=COLORS['dark'])
    
    # Use Case 4: Anomaly Detection
    uc4_y = 2.1
    uc4_box = FancyBboxPatch((3.0, uc4_y-0.4), 11.5, 1.0,
                              boxstyle="round,pad=0.05",
                              facecolor=COLORS['accent'] + '15',
                              edgecolor=COLORS['accent'], linewidth=2)
    ax.add_patch(uc4_box)
    ax.text(8.75, uc4_y+0.25, '4. Anomaly Detection & Response', fontsize=13,
            fontweight='bold', color=COLORS['accent'])
    ax.text(8.75, uc4_y-0.15, 'Real-time alarm detection, automated responses, incident logging',
            fontsize=9, ha='center', color=COLORS['neutral'])
    
    anom_details = [
        'Event: Temperature exceeds 150°C threshold',
        'AI: detect_anomaly() → write_coil(1, 100, True) → notify_operator()',
        'Action: "Emergency cooling activated. Operator notified via dashboard"'
    ]
    for i, detail in enumerate(anom_details):
        ax.text(4.0, uc4_y-0.55-i*0.25, detail, fontsize=8,
               family='monospace', color=COLORS['dark'])
    
    # Interaction arrows
    # Operator to AI
    ax.annotate('', xy=(4.5, 7.5), xytext=(1.5, 8.0),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=2))
    ax.text(2.8, 8.0, 'Natural\nLanguage', fontsize=8, ha='center', 
           color=COLORS['accent'])
    
    # AI to Equipment
    ax.annotate('', xy=(15.0, 6.5), xytext=(7.0, 6.5),
                arrowprops=dict(arrowstyle='<->', color=COLORS['ai'], lw=2))
    ax.text(11.0, 6.8, 'IndustriConnect Protocol Commands', fontsize=9, ha='center',
           color=COLORS['ai'], fontweight='bold')
    
    # Equipment to AI (data feedback)
    ax.annotate('', xy=(7.0, 5.0), xytext=(15.0, 5.0),
                arrowprops=dict(arrowstyle='->', color=COLORS['industrial'], lw=2))
    ax.text(11.0, 5.3, 'Sensor Data & Status', fontsize=9, ha='center',
           color=COLORS['industrial'], fontweight='bold')
    
    # AI to Operator (insights)
    ax.annotate('', xy=(1.5, 3.0), xytext=(4.5, 3.5),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=2))
    ax.text(2.8, 3.5, 'Insights &\nAlerts', fontsize=8, ha='center',
           color=COLORS['primary'])
    
    # Legend
    legend_elements = [
        Line2D([0], [0], color=COLORS['accent'], lw=2, linestyle='--',
               label='Operator Interactions'),
        Line2D([0], [0], color=COLORS['ai'], lw=2, linestyle='--',
               label='AI Processing'),
        Line2D([0], [0], color=COLORS['industrial'], lw=2, linestyle='--',
               label='Equipment Control'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9,
             framealpha=0.9, fancybox=True)
    
    save_figure(fig, '02_use_case_diagram.png')


def create_process_flow_diagram():
    """Figure 3: Process Flow Diagram - Request Flow Through System"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 12))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Title
    ax.text(10, 11.5, 'IndustriConnect Request Process Flow', 
            fontsize=24, fontweight='bold', ha='center')
    ax.text(10, 11.0, 'Data Flow from Industrial Machines through IndustriConnect to AI Agents and Back',
            fontsize=14, ha='center', style='italic', color=COLORS['neutral'])
    
    # Vertical swimlanes
    lanes = [
        ('User Request', 1.5, COLORS['accent']),
        ('AI Processing', 5.5, COLORS['ai']),
        ('IndustriConnect Layer', 9.5, COLORS['protocol']),
        ('Protocol Translation', 13.5, COLORS['industrial']),
        ('Equipment Response', 17.5, COLORS['primary']),
    ]
    
    for label, x, color in lanes:
        # Lane header
        rect = FancyBboxPatch((x-1.0, 10.2), 2.2, 0.6,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x+0.1, 10.5, label, fontsize=11, ha='center', 
                fontweight='bold', color='white')
        # Lane separator
        ax.plot([x+1.2, x+1.2], [0.5, 10.2], color=COLORS['neutral'], 
               linestyle='--', alpha=0.3, lw=1)
    
    # Process steps
    steps = [
        # (lane_x, y, label, description, color)
        (1.5, 9.0, '1. User Query', '"What is the current\nreactor temperature?"', 
         COLORS['accent']),
        (5.5, 9.0, '2. Intent Analysis', 'LLM parses request\nidentifies intent', 
         COLORS['ai']),
        (5.5, 7.5, '3. Tool Selection', 'Match to read_opcua_node\ntool capability', 
         COLORS['ai']),
        (9.5, 7.5, '4. IndustriConnect Request', 'Format tool call\nwith parameters', 
         COLORS['protocol']),
        (9.5, 6.0, '5. Server Routing', 'Route to OPC UA\nIndustriConnect Server', 
         COLORS['protocol']),
        (13.5, 6.0, '6. Protocol Translation', 'Convert IndustriConnect to\nOPC UA binary', 
         COLORS['industrial']),
        (13.5, 4.5, '7. Device Communication', 'TCP connection\nto OPC UA Server', 
         COLORS['industrial']),
        (17.5, 4.5, '8. Sensor Reading', 'Physical temperature\nsensor polled', 
         COLORS['primary']),
        (17.5, 3.0, '9. Response Data', 'Raw value: 18473\n(16-bit integer)', 
         COLORS['primary']),
        (13.5, 3.0, '10. Data Transformation', 'Scale: ×0.01\nOffset: +0', 
         COLORS['industrial']),
        (13.5, 1.5, '11. IndustriConnect Response', '{"value": 184.73,\n"unit": "°C"}', 
         COLORS['industrial']),
        (9.5, 1.5, '12. Tool Result', 'Parse & validate\nresponse format', 
         COLORS['protocol']),
        (5.5, 1.5, '13. LLM Integration', 'Incorporate into\nnatural language', 
         COLORS['ai']),
        (1.5, 1.5, '14. User Response', '"Reactor temperature\nis 184.7°C"', 
         COLORS['accent']),
    ]
    
    for x, y, label, desc, color in steps:
        box = FancyBboxPatch((x-0.8, y-0.4), 1.8, 0.9,
                             boxstyle="round,pad=0.03",
                             facecolor='white',
                             edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.2, label, fontsize=9, ha='center', 
                fontweight='bold', color=color)
        ax.text(x+0.1, y-0.15, desc, fontsize=7, ha='center',
                color=COLORS['neutral'], family='monospace')
    
    # Flow arrows
    arrows = [
        ((1.5, 8.5), (5.5, 8.5)),
        ((5.5, 9.0), (5.5, 8.0)),
        ((5.5, 7.0), (9.5, 6.5)),
        ((9.5, 7.0), (9.5, 6.5)),
        ((9.5, 5.5), (13.5, 6.0)),
        ((13.5, 5.5), (13.5, 5.0)),
        ((13.5, 4.0), (17.5, 4.5)),
        ((17.5, 4.0), (17.5, 3.5)),
        ((17.5, 2.5), (13.5, 3.0)),
        ((13.5, 2.5), (13.5, 2.0)),
        ((13.5, 1.0), (9.5, 1.5)),
        ((9.5, 1.0), (5.5, 1.5)),
        ((5.5, 1.0), (1.5, 1.5)),
    ]
    
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=COLORS['neutral'], 
                                   lw=1.5, connectionstyle="arc3,rad=0"))
    
    # Data transformation detail box
    detail_box = FancyBboxPatch((12.0, 0.3), 6.0, 1.0,
                                 boxstyle="round,pad=0.03",
                                 facecolor=COLORS['light'],
                                 edgecolor=COLORS['neutral'], linewidth=1)
    ax.add_patch(detail_box)
    ax.text(15.0, 1.0, 'Data Transformation Example:', fontsize=9, 
            fontweight='bold', ha='center')
    ax.text(15.0, 0.6, 'Raw: 0x4829 → Scaled: 184.73°C → Formatted: "184.7°C"',
            fontsize=8, ha='center', family='monospace')
    
    # Legend
    legend_elements = [
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor='white', edgecolor=COLORS['accent'],
                               label='User Interface'),
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor='white', edgecolor=COLORS['ai'],
                               label='AI Processing'),
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor='white', edgecolor=COLORS['protocol'],
                               label='IndustriConnect Layer'),
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor='white', edgecolor=COLORS['industrial'],
                               label='Protocol Translation'),
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor='white', edgecolor=COLORS['primary'],
                               label='Equipment Layer'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9,
             framealpha=0.9, fancybox=True, bbox_to_anchor=(0.98, 0.98))
    
    save_figure(fig, '03_process_flow_diagram.png')


def create_connection_topology_diagram():
    """Figure 4: Connection Topology - IndustriConnect Protocol Translation"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Title
    ax.text(10, 13.5, 'IndustriConnect', 
            fontsize=28, fontweight='bold', ha='center')
    ax.text(10, 13.0, 'Connection Topology & Protocol Translation',
            fontsize=16, ha='center', style='italic', color=COLORS['neutral'])
    
    # Central IndustriConnect Hub
    hub = Circle((10, 8), 2.5, facecolor=COLORS['protocol'] + '30',
                 edgecolor=COLORS['protocol'], linewidth=3)
    ax.add_patch(hub)
    ax.text(10, 8.8, 'IndustriConnect', fontsize=22, ha='center', fontweight='bold',
            color=COLORS['protocol'])
    ax.text(10, 8.0, 'Protocol Hub', fontsize=14, ha='center',
            color=COLORS['protocol'])
    ax.text(10, 7.3, 'FastMCP Framework', fontsize=10, ha='center',
            color=COLORS['neutral'], style='italic')
    
    # Left side - LLM Clients
    llm_clients = [
        ('Ollama', 2.5, 11, COLORS['ai']),
        ('OpenAI', 2.5, 8.5, COLORS['primary']),
        ('Anthropic', 2.5, 6, COLORS['purple']),
        ('Google', 2.5, 3.5, COLORS['warning']),
    ]
    
    for label, x, y, color in llm_clients:
        box = FancyBboxPatch((x-0.8, y-0.5), 1.8, 1.2,
                             boxstyle="round,pad=0.03",
                             facecolor=color + '20',
                             edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.1, label, fontsize=11, ha='center', fontweight='bold')
        ax.text(x+0.1, y-0.25, 'LLM Provider', fontsize=8, ha='center', color=COLORS['neutral'])
        # Connection to hub
        ax.plot([x+1.0, 8.0], [y, 8], color=color, lw=2, alpha=0.6)
    
    ax.text(2.5, 12.5, 'LLM Clients', fontsize=14, ha='center', 
            fontweight='bold', color=COLORS['dark'])
    ax.text(2.5, 12.1, '(IndustriConnect Clients)', fontsize=10, ha='center',
            color=COLORS['neutral'])
    
    # Top - IndustriConnect Server Instances
    ax.text(10, 12.5, 'IndustriConnect Server Instances', fontsize=14, ha='center',
            fontweight='bold', color=COLORS['dark'])
    
    servers = [
        ('OPC UA', 6, 11, COLORS['industrial']),
        ('Modbus', 7.5, 11, COLORS['industrial']),
        ('MQTT', 9, 11, COLORS['industrial']),
        ('S7comm', 10.5, 11, COLORS['industrial']),
        ('BACnet', 12, 11, COLORS['industrial']),
        ('DNP3', 13.5, 11, COLORS['industrial']),
    ]
    
    for name, x, y, color in servers:
        box = FancyBboxPatch((x-0.5, y-0.3), 1.2, 0.7,
                             boxstyle="round,pad=0.02",
                             facecolor=color + '30',
                             edgecolor=color, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.05, name, fontsize=9, ha='center', fontweight='bold')
        # Connection to hub
        ax.plot([x+0.1, 10], [y-0.3, 9.8], color=color, lw=1.5, alpha=0.6)
    

    
    # Right side - Protocol Adapters
    ax.text(17.5, 12.5, 'Protocol Adapters', fontsize=14, ha='center',
            fontweight='bold', color=COLORS['dark'])
    ax.text(17.5, 12.1, '(Python Libraries)', fontsize=10, ha='center',
            color=COLORS['neutral'])
    
    adapters = [
        ('opcua', 'OPC UA Client', 16.5, 10.5),
        ('pymodbus', 'Modbus Master', 18.5, 10.5),
        ('paho-mqtt', 'MQTT Client', 16.5, 9.0),
        ('python-snap7', 'S7 Protocol', 18.5, 9.0),
        ('BAC0', 'BACnet/IP', 16.5, 7.5),
        ('dnp3', 'DNP3 Master', 18.5, 7.5),
        ('pycomm3', 'EtherNet/IP', 16.5, 6.0),
        ('PySOEM', 'EtherCAT Master', 18.5, 6.0),
    ]
    
    for lib, desc, x, y in adapters:
        box = FancyBboxPatch((x-0.7, y-0.35), 1.6, 0.8,
                             boxstyle="round,pad=0.02",
                             facecolor=COLORS['teal'] + '20',
                             edgecolor=COLORS['teal'], linewidth=1.5)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.15, lib, fontsize=8, ha='center', 
                fontweight='bold', family='monospace')
        ax.text(x+0.1, y-0.15, desc, fontsize=7, ha='center', 
                color=COLORS['neutral'])
        # Connection to hub
        ax.plot([12.0, x-0.7], [8, y], color=COLORS['teal'], lw=1.5, alpha=0.6)
    
    # Bottom - Industrial Equipment
    ax.text(10, 2.8, 'Industrial Equipment', fontsize=14, ha='center',
            fontweight='bold', color=COLORS['dark'])
    
    equipment = [
        ('PLC', 4.5, 1.5, ['Siemens S7-1500', 'Allen-Bradley', 'Schneider']),
        ('DCS', 7.5, 1.5, ['Honeywell', 'Yokogawa', 'Emerson']),
        ('Sensors', 10, 1.5, ['Temperature', 'Pressure', 'Flow']),
        ('Actuators', 12.5, 1.5, ['Motors', 'Valves', 'Drives']),
        ('IoT GW', 15.5, 1.5, ['Edge Gateways', 'Protocol Conv']),
    ]
    
    for label, x, y, items in equipment:
        box = FancyBboxPatch((x-1.0, y-0.6), 2.2, 1.4,
                             boxstyle="round,pad=0.02",
                             facecolor=COLORS['industrial'] + '20',
                             edgecolor=COLORS['industrial'], linewidth=2)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.35, label, fontsize=10, ha='center', fontweight='bold')
        for i, item in enumerate(items):
            ax.text(x+0.1, y-0.05-i*0.22, item, fontsize=7, ha='center',
                   color=COLORS['neutral'])
    
    # Connection lines from adapters to equipment
    for x in [4.5, 7.5, 10, 12.5, 15.5]:
        ax.plot([x+0.1, x+0.1], [0.8, 0.3], color=COLORS['industrial'], 
               lw=2, linestyle='--', alpha=0.5)
    
    save_figure(fig, '04_connection_topology_diagram.png')


def create_agent_interaction_diagram():
    """Figure 5: AI Agent Interaction - Multi-Agent Collaboration"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Title
    ax.text(10, 13.5, 'AI Agent Collaboration & Task Delegation', 
            fontsize=24, fontweight='bold', ha='center')
    ax.text(10, 13.0, 'Multi-Agent Patterns for Complex Industrial Operations',
            fontsize=14, ha='center', style='italic', color=COLORS['neutral'])
    
    # Orchestrator Agent (center)
    orch_box = FancyBboxPatch((8.0, 10.5), 4.0, 1.8,
                               boxstyle="round,pad=0.05",
                               facecolor=COLORS['purple'] + '30',
                               edgecolor=COLORS['purple'], linewidth=3)
    ax.add_patch(orch_box)
    ax.text(10, 11.7, '👑 Orchestrator Agent', fontsize=16, ha='center', 
            fontweight='bold', color=COLORS['purple'])
    ax.text(10, 11.2, 'Task Analysis • Agent Selection • Result Aggregation', 
            fontsize=10, ha='center', color=COLORS['neutral'])
    ax.text(10, 10.8, 'Complex Query: "Optimize the entire production line"',
            fontsize=9, ha='center', style='italic', family='monospace')
    
    # Specialized Agents (surrounding orchestrator)
    agents = [
        ('🔍 Monitoring\nAgent', 2.5, 8.5, COLORS['primary'], 
         'Real-time data\ncollection'),
        ('🔧 Maintenance\nAgent', 7.0, 8.5, COLORS['warning'],
         'Predictive analysis\nalerts'),
        ('⚡ Optimization\nAgent', 13.0, 8.5, COLORS['secondary'],
         'Process tuning\nefficiency'),
        ('🚨 Safety\nAgent', 17.5, 8.5, COLORS['accent'],
         'Anomaly detection\nemergency stop'),
    ]
    
    for label, x, y, color, desc in agents:
        box = FancyBboxPatch((x-1.2, y-0.8), 2.6, 1.7,
                             boxstyle="round,pad=0.03",
                             facecolor=color + '20',
                             edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.4, label, fontsize=11, ha='center', 
                fontweight='bold', color=color)
        ax.text(x+0.1, y-0.1, desc, fontsize=8, ha='center',
                color=COLORS['neutral'])
        ax.text(x+0.1, y-0.45, 'IndustriConnect Tools: 8-15', fontsize=7, ha='center',
                style='italic', color=COLORS['neutral'])
        
        # Connection to orchestrator
        ax.annotate('', xy=(10, 10.5), xytext=(x+0.1, y+0.9),
                    arrowprops=dict(arrowstyle='<->', color=COLORS['purple'], 
                                   lw=2, connectionstyle="arc3,rad=0.1"))
    
    ax.text(10, 9.0, 'Specialized AI Agents', fontsize=12, ha='center',
            fontweight='bold', color=COLORS['dark'])
    
    # Task delegation flow (middle section)
    flow_y = 6.5
    
    # Step 1: Task Analysis
    step1_box = FancyBboxPatch((1.5, flow_y-0.5), 3.5, 1.2,
                                boxstyle="round,pad=0.03",
                                facecolor=COLORS['light'],
                                edgecolor=COLORS['neutral'], linewidth=2)
    ax.add_patch(step1_box)
    ax.text(3.25, flow_y+0.4, '1. Task Analysis', fontsize=11, 
            ha='center', fontweight='bold')
    ax.text(3.25, flow_y, 'Decompose complex\nquery into sub-tasks',
            fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Arrow
    ax.annotate('', xy=(5.5, flow_y+0.1), xytext=(5.0, flow_y+0.1),
                arrowprops=dict(arrowstyle='->', color=COLORS['dark'], lw=2))
    
    # Step 2: Agent Selection
    step2_box = FancyBboxPatch((6.0, flow_y-0.5), 3.5, 1.2,
                                boxstyle="round,pad=0.03",
                                facecolor=COLORS['light'],
                                edgecolor=COLORS['neutral'], linewidth=2)
    ax.add_patch(step2_box)
    ax.text(7.75, flow_y+0.4, '2. Agent Selection', fontsize=11,
            ha='center', fontweight='bold')
    ax.text(7.75, flow_y, 'Match sub-tasks to\nspecialized agents',
            fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Arrow
    ax.annotate('', xy=(10.0, flow_y+0.1), xytext=(9.5, flow_y+0.1),
                arrowprops=dict(arrowstyle='->', color=COLORS['dark'], lw=2))
    
    # Step 3: Parallel Execution
    step3_box = FancyBboxPatch((10.5, flow_y-0.5), 3.5, 1.2,
                                boxstyle="round,pad=0.03",
                                facecolor=COLORS['light'],
                                edgecolor=COLORS['neutral'], linewidth=2)
    ax.add_patch(step3_box)
    ax.text(12.25, flow_y+0.4, '3. Parallel Execution', fontsize=11,
            ha='center', fontweight='bold')
    ax.text(12.25, flow_y, 'Execute IndustriConnect tools\nconcurrently',
            fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Arrow
    ax.annotate('', xy=(14.5, flow_y+0.1), xytext=(14.0, flow_y+0.1),
                arrowprops=dict(arrowstyle='->', color=COLORS['dark'], lw=2))
    
    # Step 4: Result Aggregation
    step4_box = FancyBboxPatch((15.0, flow_y-0.5), 3.5, 1.2,
                                boxstyle="round,pad=0.03",
                                facecolor=COLORS['light'],
                                edgecolor=COLORS['neutral'], linewidth=2)
    ax.add_patch(step4_box)
    ax.text(16.75, flow_y+0.4, '4. Result Aggregation', fontsize=11,
            ha='center', fontweight='bold')
    ax.text(16.75, flow_y, 'Synthesize results\ngenerate response',
            fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Collaboration patterns section
    patterns_y = 4.5
    ax.text(10, patterns_y+1.0, 'Collaboration Patterns', fontsize=14,
            ha='center', fontweight='bold', color=COLORS['dark'])
    
    patterns = [
        ('Sequential', 3, patterns_y, [
            'Agent A → Agent B → Agent C',
            'Chain of dependent tasks'
        ]),
        ('Parallel', 8, patterns_y, [
            'Agent A, B, C simultaneously',
            'Independent sub-tasks'
        ]),
        ('Hierarchical', 13, patterns_y, [
            'Orchestrator delegates',
            'Manager-worker pattern'
        ]),
        ('Consensus', 17.5, patterns_y, [
            'Multiple agents vote',
            'Critical decisions'
        ]),
    ]
    
    for label, x, y, desc in patterns:
        box = FancyBboxPatch((x-1.8, y-0.8), 3.8, 1.4,
                             boxstyle="round,pad=0.03",
                             facecolor=COLORS['light'],
                             edgecolor=COLORS['neutral'], linewidth=1)
        ax.add_patch(box)
        ax.text(x+0.1, y+0.4, label, fontsize=11, ha='center', 
                fontweight='bold', color=COLORS['primary'])
        for i, line in enumerate(desc):
            ax.text(x+0.1, y-0.05-i*0.25, line, fontsize=8, ha='center',
                   color=COLORS['neutral'])
    
    # Response handling section
    response_y = 2.2
    ax.text(10, response_y+1.0, 'Response Handling & Error Management', fontsize=14,
            ha='center', fontweight='bold', color=COLORS['dark'])
    
    response_box = FancyBboxPatch((1.5, response_y-0.6), 17, 1.2,
                                   boxstyle="round,pad=0.03",
                                   facecolor=COLORS['accent'] + '10',
                                   edgecolor=COLORS['accent'], linewidth=2)
    ax.add_patch(response_box)
    
    response_steps = [
        ('Result Validation', 3.5, response_y, 'Check tool results\nfor errors'),
        ('Data Integration', 7.5, response_y, 'Merge data from\nmultiple sources'),
        ('Context Building', 11.5, response_y, 'Add operational\ncontext'),
        ('Response Generation', 16, response_y, 'Natural language\noutput'),
    ]
    
    for label, x, y, desc in response_steps:
        ax.text(x, y+0.3, label, fontsize=10, ha='center', 
                fontweight='bold', color=COLORS['accent'])
        ax.text(x, y-0.15, desc, fontsize=8, ha='center',
                color=COLORS['neutral'])
        if x < 16:
            ax.annotate('', xy=(x+1.8, y), xytext=(x+1.0, y),
                        arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5))
    
    # Example scenario box
    scenario_box = FancyBboxPatch((0.5, 0.2), 19, 1.0,
                                   boxstyle="round,pad=0.03",
                                   facecolor=COLORS['secondary'] + '10',
                                   edgecolor=COLORS['secondary'], linewidth=2)
    ax.add_patch(scenario_box)
    ax.text(10, 0.95, 'Example: Production Line Optimization', fontsize=12,
            ha='center', fontweight='bold', color=COLORS['secondary'])
    ax.text(10, 0.6, 'Query: "Optimize the entire production line for maximum throughput"',
            fontsize=9, ha='center', family='monospace')
    ax.text(10, 0.3, 'Response: Monitoring → analyzes current rates | Maintenance → checks equipment health | '
                     'Optimization → adjusts setpoints | Safety → validates limits | Result: 15% throughput increase',
            fontsize=8, ha='center', color=COLORS['neutral'])
    
    # Legend
    legend_elements = [
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor=COLORS['purple'] + '30',
                               edgecolor=COLORS['purple'], label='Orchestrator'),
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor=COLORS['primary'] + '20',
                               edgecolor=COLORS['primary'], label='Specialized Agent'),
        mpatches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                               facecolor=COLORS['light'],
                               edgecolor=COLORS['neutral'], label='Process Step'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9,
             framealpha=0.9, fancybox=True, bbox_to_anchor=(0.02, 0.98))
    
    save_figure(fig, '05_agent_interaction_diagram.png')


def main():
    """Generate all whitepaper figures"""
    print("=" * 60)
    print("IndustriConnect Whitepaper Technical Figures Generator")
    print("=" * 60)
    print()
    
    figures = [
        ('Architecture Diagram', create_architecture_diagram),
        ('Use Case Diagram', create_use_case_diagram),
        ('Process Flow Diagram', create_process_flow_diagram),
        ('Connection Topology Diagram', create_connection_topology_diagram),
        ('Agent Interaction Diagram', create_agent_interaction_diagram),
    ]
    
    for name, func in figures:
        print(f"Generating {name}...")
        try:
            func()
            print(f"  ✓ Complete\n")
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    print("=" * 60)
    print(f"All figures saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
