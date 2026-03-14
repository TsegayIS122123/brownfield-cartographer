#!/usr/bin/env python
"""Dashboard for Brownfield Cartographer - Visualize knowledge graph and analytics."""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, send_file

# Add parent directory to path to import cartographer modules
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)

# Path to cartography artifacts
CART_PATH = Path(__file__).parent.parent / ".cartography"

@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('index.html')

@app.route('/api/graph')
def get_graph():
    """Return knowledge graph as JSON."""
    graph_file = CART_PATH / "knowledge_graph.json"
    if graph_file.exists():
        with open(graph_file, 'r') as f:
            return jsonify(json.load(f))
    
    # Fallback to module graph if knowledge graph not available
    module_file = CART_PATH / "module_graph.json"
    if module_file.exists():
        with open(module_file, 'r') as f:
            return jsonify(json.load(f))
    
    return jsonify({"error": "Graph not found"}), 404

@app.route('/api/lineage')
def get_lineage():
    """Return lineage graph."""
    lineage_file = CART_PATH / "lineage_graph.json"
    if lineage_file.exists():
        with open(lineage_file, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Lineage graph not found"}), 404

@app.route('/api/stats')
def get_stats():
    """Return all statistics from analysis."""
    stats = {}
    
    # Collect all JSON files
    for json_file in CART_PATH.glob("*.json"):
        if json_file.name in ['knowledge_graph.json', 'lineage_graph.json']:
            continue  # Skip large graph files for stats endpoint
        try:
            with open(json_file, 'r') as f:
                stats[json_file.stem] = json.load(f)
        except Exception as e:
            stats[json_file.stem] = {"error": str(e)}
    
    return jsonify(stats)

@app.route('/api/codebase')
def get_codebase():
    """Return CODEBASE.md content."""
    codebase_file = CART_PATH / "CODEBASE.md"
    if codebase_file.exists():
        with open(codebase_file, 'r') as f:
            return jsonify({"content": f.read()})
    return jsonify({"error": "CODEBASE.md not found"}), 404

@app.route('/api/brief')
def get_brief():
    """Return onboarding_brief.md content."""
    brief_file = CART_PATH / "onboarding_brief.md"
    if brief_file.exists():
        with open(brief_file, 'r') as f:
            return jsonify({"content": f.read()})
    return jsonify({"error": "onboarding_brief.md not found"}), 404

@app.route('/api/trace')
def get_trace():
    """Return trace logs as JSON array."""
    trace_file = CART_PATH / "cartography_trace.jsonl"
    traces = []
    if trace_file.exists():
        with open(trace_file, 'r') as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
    return jsonify(traces)

@app.route('/api/export/dot')
def export_dot():
    """Export graph as DOT format for Graphviz."""
    graph_file = CART_PATH / "knowledge_graph.json"
    if not graph_file.exists():
        return jsonify({"error": "Graph not found"}), 404
    
    with open(graph_file, 'r') as f:
        data = json.load(f)
    
    dot_lines = ['digraph KnowledgeGraph {']
    dot_lines.append('  rankdir=LR;')
    dot_lines.append('  node [style=filled, shape=box];')
    
    # Add nodes
    for node in data.get('nodes', []):
        node_id = node.get('id', '').replace('-', '_').replace('.', '_')
        node_type = node.get('type', 'unknown')
        color = {
            'module': '#ff9999',
            'dataset': '#99ff99',
            'transformation': '#9999ff',
            'function': '#ffff99'
        }.get(node_type, '#cccccc')
        
        label = node.get('id', '').split('/')[-1]
        dot_lines.append(f'  {node_id} [label="{label}", fillcolor="{color}"];')
    
    # Add edges
    for edge in data.get('edges', []):
        source = edge.get('source', '').replace('-', '_').replace('.', '_')
        target = edge.get('target', '').replace('-', '_').replace('.', '_')
        edge_type = edge.get('type', 'depends')
        dot_lines.append(f'  {source} -> {target} [label="{edge_type}"];')
    
    dot_lines.append('}')
    
    return '\n'.join(dot_lines)

@app.route('/api/export/mermaid')
def export_mermaid():
    """Export graph as Mermaid diagram."""
    graph_file = CART_PATH / "knowledge_graph.json"
    if not graph_file.exists():
        return jsonify({"error": "Graph not found"}), 404
    
    with open(graph_file, 'r') as f:
        data = json.load(f)
    
    mermaid = ['graph TD']
    
    # Add nodes
    node_ids = {}
    for i, node in enumerate(data.get('nodes', [])):
        node_id = f'N{i}'
        node_label = node.get('id', '').split('/')[-1][:20]
        node_type = node.get('type', 'unknown')
        
        # Style based on type
        if node_type == 'module':
            mermaid.append(f'  {node_id}[{node_label}]')
        elif node_type == 'dataset':
            mermaid.append(f'  {node_id}(({node_label}))')
        else:
            mermaid.append(f'  {node_id}{node_label}')
        
        node_ids[node.get('id')] = node_id
    
    # Add edges
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source in node_ids and target in node_ids:
            edge_type = edge.get('type', 'depends')
            mermaid.append(f'  {node_ids[source]} -->|{edge_type}| {node_ids[target]}')
    
    return '\n'.join(mermaid)

if __name__ == '__main__':
    app.run(debug=True, port=5000)