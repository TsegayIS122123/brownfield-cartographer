#!/usr/bin/env python
"""Dashboard for Brownfield Cartographer - Visualize knowledge graph and analytics."""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
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
    # Try knowledge_graph.json first
    graph_file = CART_PATH / "knowledge_graph.json"
    if graph_file.exists():
        with open(graph_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    
    # Fallback to module_graph.json
    module_file = CART_PATH / "module_graph.json"
    if module_file.exists():
        with open(module_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify(data)
    
    # Return empty graph structure if nothing exists
    return jsonify({"nodes": [], "edges": [], "metadata": {"node_count": 0, "edge_count": 0}})

@app.route('/api/lineage')
def get_lineage():
    """Return lineage graph with cleaned display names."""
    # Try lineage_graph.json first
    lineage_file = CART_PATH / "lineage_graph.json"
    if lineage_file.exists():
        with open(lineage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Clean the data for display
            cleaned_data = clean_lineage_data(data)
            return jsonify(cleaned_data)
    
    # Try lineage_stats.json for summary
    stats_file = CART_PATH / "lineage_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
            return jsonify({
                "nodes": [],
                "edges": [],
                "sources": stats.get("sources", []),
                "sinks": stats.get("sinks", []),
                "summary": stats
            })
    
    return jsonify({"nodes": [], "edges": [], "sources": [], "sinks": []})

def clean_lineage_data(data):
    """Clean lineage data for display - shorten paths and remove duplicates."""
    if not isinstance(data, dict):
        return data
    
    cleaned = data.copy()
    
    # Clean nodes
    if 'nodes' in cleaned:
        cleaned['nodes'] = clean_node_list(cleaned['nodes'])
    
    # Clean sources and sinks
    if 'sources' in cleaned:
        cleaned['sources'] = clean_name_list(cleaned['sources'])
    if 'sinks' in cleaned:
        cleaned['sinks'] = clean_name_list(cleaned['sinks'])
    
    return cleaned

def clean_node_list(nodes):
    """Clean a list of nodes."""
    cleaned = []
    seen = set()
    
    for node in nodes:
        if isinstance(node, dict):
            # Get the node ID
            node_id = node.get('id', '')
            # Create a display name
            display_name = get_display_name(node_id)
            
            # Avoid duplicates
            if display_name not in seen:
                seen.add(display_name)
                node['display_name'] = display_name
                node['short_id'] = node_id.split('\\')[-1].split('/')[-1][:30]
                cleaned.append(node)
        elif isinstance(node, str):
            display_name = get_display_name(node)
            if display_name not in seen:
                seen.add(display_name)
                cleaned.append({
                    'id': node,
                    'display_name': display_name,
                    'short_id': node.split('\\')[-1].split('/')[-1][:30]
                })
    
    return cleaned

def clean_name_list(names):
    """Clean a list of names for display."""
    cleaned = []
    seen = set()
    
    for name in names:
        display_name = get_display_name(name)
        if display_name not in seen and display_name:
            seen.add(display_name)
            cleaned.append(display_name)
    
    return sorted(cleaned)[:50]  # Limit to 50, sorted

def get_display_name(name):
    """Extract a clean display name from a path or ID."""
    if not name:
        return ""
    
    # Handle Python paths
    if 'python:' in name:
        # Extract just the filename and line number
        parts = name.split('\\')[-1].split('/')[-1]
        if '.py:' in parts:
            file_line = parts.split('.py:')
            if len(file_line) > 1:
                return f"{file_line[0]}.py:L{file_line[1]}"
        return parts
    
    # Handle dataset: prefix
    if name.startswith('dataset:'):
        inner = name[8:]
        if inner.startswith('${') and inner.endswith('}'):
            # Variable references
            return f"${{{inner[2:-1]}}}"
        if 'FSTRING' in inner:
            # F-strings - extract a short version
            return inner.split(':')[-1][:30] + "..."
        return inner
    
    # Handle model: prefix
    if name.startswith('model:'):
        return name[6:]
    
    # Handle source: prefix
    if name.startswith('source:'):
        return name[7:]
    
    # Handle sql: prefix
    if name.startswith('sql:'):
        return name[4:].split('\\')[-1].split('/')[-1]
    
    # Just return the last part of the path
    return name.split('\\')[-1].split('/')[-1]

@app.route('/api/stats')
def get_stats():
    """Return all statistics from analysis."""
    stats = {}
    
    # Surveyor results
    surveyor_file = CART_PATH / "surveyor_results.json"
    modules = 0
    imports = 0
    languages = {}
    top_modules = []
    
    if surveyor_file.exists():
        with open(surveyor_file, 'r', encoding='utf-8') as f:
            surveyor_data = json.load(f)
            stats['surveyor'] = surveyor_data
            
            # Get modules from metadata
            if surveyor_data.get('metadata'):
                metadata = surveyor_data['metadata']
                modules = metadata.get('total_modules', 0)
                languages = metadata.get('languages', {})
                top_modules = metadata.get('top_modules_by_pagerank', [])
    
    # Module graph for additional import count
    module_graph = CART_PATH / "module_graph.json"
    if module_graph.exists():
        with open(module_graph, 'r', encoding='utf-8') as f:
            mg_data = json.load(f)
            # Count imports from edges
            imports = len(mg_data.get('edges', []))
            # If no edges, try to count from nodes
            if imports == 0:
                for node in mg_data.get('nodes', []):
                    imports += len(node.get('imports', []))
    
    # Lineage stats
    lineage_stats = CART_PATH / "lineage_stats.json"
    sources = []
    sinks = []
    python_ops = 0
    sql_queries = 0
    
    if lineage_stats.exists():
        with open(lineage_stats, 'r', encoding='utf-8') as f:
            ls_data = json.load(f)
            sources = ls_data.get('sources', [])
            sinks = ls_data.get('sinks', [])
            python_ops = ls_data.get('python_operations', 0)
            sql_queries = ls_data.get('sql_queries', 0)
            stats['lineage'] = ls_data
    else:
        # Try lineage_graph.json for sources/sinks
        lineage_graph = CART_PATH / "lineage_graph.json"
        if lineage_graph.exists():
            with open(lineage_graph, 'r', encoding='utf-8') as f:
                lg_data = json.load(f)
                sources = lg_data.get('sources', [])
                sinks = lg_data.get('sinks', [])
    
    # Semanticist results
    semanticist_file = CART_PATH / "semanticist_results.json"
    if semanticist_file.exists():
        with open(semanticist_file, 'r', encoding='utf-8') as f:
            stats['semanticist'] = json.load(f)
    
    # Add summary stats
    stats['summary'] = {
        'modules': modules,
        'imports': imports,
        'sources': len(sources),
        'sinks': len(sinks),
        'source_list': sources[:50],  # Limit to 50 for display
        'sink_list': sinks[:50],
        'python_ops': python_ops,
        'sql_queries': sql_queries,
        'languages': languages,
        'top_modules': top_modules[:10]
    }
    
    return jsonify(stats)

@app.route('/api/codebase')
def get_codebase():
    """Return CODEBASE.md content."""
    codebase_file = CART_PATH / "CODEBASE.md"
    if codebase_file.exists():
        with open(codebase_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return jsonify({"content": content})
    
    # Try alternative locations
    alt_file = Path(__file__).parent.parent / "CODEBASE.md"
    if alt_file.exists():
        with open(alt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return jsonify({"content": content})
    
    return jsonify({"content": "# CODEBASE.md\n\nNo CODEBASE.md found. Generated files should be in `.cartography/` directory.\n\nPlease run analysis first:\n```bash\npython -m src.cli analyze ../jaffle-shop\n```"})

@app.route('/api/brief')
def get_brief():
    """Return onboarding_brief.md content."""
    brief_file = CART_PATH / "onboarding_brief.md"
    if brief_file.exists():
        with open(brief_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return jsonify({"content": content})
    
    return jsonify({"content": "# Onboarding Brief\n\nNo onboarding brief generated yet. Run analysis first."})

@app.route('/api/trace')
def get_trace():
    """Return trace logs as JSON array."""
    trace_file = CART_PATH / "cartography_trace.jsonl"
    traces = []
    if trace_file.exists():
        with open(trace_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        traces.append(json.loads(line))
                    except:
                        continue
    return jsonify(traces)

@app.route('/api/debug')
def debug():
    """Debug endpoint to see what files exist."""
    files = []
    if CART_PATH.exists():
        for f in CART_PATH.glob('*'):
            files.append({
                'name': f.name,
                'size': f.stat().st_size,
                'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    
    return jsonify({
        'cartography_path': str(CART_PATH),
        'exists': CART_PATH.exists(),
        'files': files
    })

@app.route('/api/export/dot')
def export_dot():
    """Export graph as DOT format for Graphviz."""
    graph_file = CART_PATH / "knowledge_graph.json"
    if not graph_file.exists():
        graph_file = CART_PATH / "module_graph.json"
    
    if not graph_file.exists():
        return "Graph not found", 404
    
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    dot_lines = ['digraph KnowledgeGraph {']
    dot_lines.append('  rankdir=LR;')
    dot_lines.append('  node [style=filled, shape=box];')
    
    # Add nodes
    node_ids = {}
    for node in data.get('nodes', []):
        node_id = node.get('id', '').replace('-', '_').replace('.', '_').replace(':', '_')
        node_ids[node.get('id')] = node_id
        
        node_type = node.get('type', 'unknown')
        color = {
            'module': '#ff9999',
            'dataset': '#99ff99',
            'transformation': '#9999ff',
            'function': '#ffff99'
        }.get(node_type, '#cccccc')
        
        label = node.get('id', '').split('/')[-1][:20]
        dot_lines.append(f'  {node_id} [label="{label}", fillcolor="{color}"];')
    
    # Add edges
    for edge in data.get('edges', []):
        source = edge.get('source', '')
        target = edge.get('target', '')
        if source in node_ids and target in node_ids:
            edge_type = edge.get('type', 'depends')
            dot_lines.append(f'  {node_ids[source]} -> {node_ids[target]} [label="{edge_type}"];')
    
    dot_lines.append('}')
    
    return '\n'.join(dot_lines)

@app.route('/api/export/mermaid')
def export_mermaid():
    """Export graph as Mermaid diagram."""
    graph_file = CART_PATH / "knowledge_graph.json"
    if not graph_file.exists():
        graph_file = CART_PATH / "module_graph.json"
    
    if not graph_file.exists():
        return "Graph not found", 404
    
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    mermaid = ['graph TD']
    
    # Add nodes
    node_ids = {}
    for i, node in enumerate(data.get('nodes', [])):
        node_id = f'N{i}'
        node_ids[node.get('id')] = node_id
        node_label = node.get('id', '').split('/')[-1][:20]
        node_type = node.get('type', 'unknown')
        
        # Style based on type
        if node_type == 'module':
            mermaid.append(f'  {node_id}[{node_label}]')
        elif node_type == 'dataset':
            mermaid.append(f'  {node_id}(({node_label}))')
        else:
            mermaid.append(f'  {node_id}[{node_label}]')
    
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