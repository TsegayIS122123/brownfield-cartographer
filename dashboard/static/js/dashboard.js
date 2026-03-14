// Dashboard JavaScript for Brownfield Cartographer

let graphData = null;
let lineageData = null;
let statsData = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    loadStats();
    loadGraph();
    loadLineage();
    loadDocs();
    loadTrace();
    
    // Refresh stats every 10 seconds
    setInterval(loadStats, 10000);
    setInterval(loadGraph, 30000);
    setInterval(loadLineage, 30000);
});

// Load statistics
function loadStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            console.log('Stats loaded:', data);
            statsData = data;
            updateStatsCards(data);
            updateCharts(data);
        })
        .catch(error => console.error('Error loading stats:', error));
}

// Update stats cards
function updateStatsCards(data) {
    const summary = data.summary || {};
    
    // Update main stats
    document.getElementById('stat-modules').textContent = summary.modules || 0;
    document.getElementById('stat-imports').textContent = summary.imports || 0;
    document.getElementById('stat-sources').textContent = summary.sources || 0;
    document.getElementById('stat-sinks').textContent = summary.sinks || 0;
    
    // Update repo info
    if (data.surveyor?.metadata?.repository) {
        const repo = data.surveyor.metadata.repository.split(/[\\/]/).pop();
        document.getElementById('repo-name').textContent = repo;
    }
    
    if (data.surveyor?.metadata?.analysis_timestamp) {
        const time = new Date(data.surveyor.metadata.analysis_timestamp);
        document.getElementById('analysis-time').textContent = time.toLocaleString();
    }
}

// Update charts
function updateCharts(data) {
    const summary = data.summary || {};
    
    // Language distribution chart
    if (summary.languages && Object.keys(summary.languages).length > 0) {
        const langs = summary.languages;
        const langValues = Object.values(langs);
        const langLabels = Object.keys(langs);
        
        // Check if it's actually distribution or just counts
        const total = langValues.reduce((a, b) => a + b, 0);
        
        const langData = [{
            values: langValues,
            labels: langLabels,
            type: 'pie',
            textinfo: 'label+percent',
            hoverinfo: 'label+value+percent',
            marker: {
                colors: ['#ff9999', '#99ff99', '#9999ff', '#ffff99', '#ff99ff', '#99ffff']
            }
        }];
        
        const layout = {
            title: `Language Distribution (Total: ${total} files)`,
            height: 300,
            margin: { t: 40, b: 40, l: 40, r: 40 },
            showlegend: true
        };
        
        Plotly.newPlot('lang-chart', langData, layout);
    } else {
        document.getElementById('lang-chart').innerHTML = '<p class="text-muted text-center p-5">No language data available</p>';
    }
    
    // PageRank chart
    if (summary.top_modules && summary.top_modules.length > 0) {
        const top = summary.top_modules;
        const rankData = [{
            x: top.map(m => {
                const path = m.path || '';
                return path.split('/').pop() || 'unknown';
            }),
            y: top.map(m => m.pagerank || 0),
            type: 'bar',
            marker: { color: '#667eea' },
            text: top.map(m => (m.pagerank * 100).toFixed(2) + '%'),
            textposition: 'outside'
        }];
        
        const layout = {
            title: 'Top Modules by PageRank',
            xaxis: { 
                tickangle: -45,
                title: 'Module'
            },
            yaxis: {
                title: 'PageRank Score',
                tickformat: '.3f'
            },
            height: 300,
            margin: { t: 40, b: 80, l: 60, r: 20 }
        };
        
        Plotly.newPlot('pagerank-chart', rankData, layout);
    } else {
        document.getElementById('pagerank-chart').innerHTML = '<p class="text-muted text-center p-5">No PageRank data available</p>';
    }
    
    // Budget chart
    if (data.semanticist?.budget_summary) {
        const budget = data.semanticist.budget_summary;
        const budgetData = [{
            values: [budget.total_cost, budget.remaining],
            labels: ['Spent', 'Remaining'],
            type: 'pie',
            marker: { colors: ['#ff6b6b', '#4ecdc4'] },
            textinfo: 'label+percent',
            hoverinfo: 'label+value'
        }];
        
        const layout = {
            title: `Budget: $${budget.total_cost.toFixed(4)} of $${budget.budget_limit}`,
            height: 300,
            margin: { t: 40, b: 40 }
        };
        
        Plotly.newPlot('budget-chart', budgetData, layout);
    } else {
        document.getElementById('budget-chart').innerHTML = '<p class="text-muted text-center p-5">No budget data available</p>';
    }
}

// Load and visualize graph
function loadGraph() {
    fetch('/api/graph')
        .then(response => response.json())
        .then(data => {
            console.log('Graph loaded:', data.nodes?.length, 'nodes');
            graphData = data;
            drawGraph(data);
        })
        .catch(error => console.error('Error loading graph:', error));
}

// Draw graph with D3.js
function drawGraph(data) {
    const container = document.getElementById('graph-container');
    if (!container) return;
    
    const width = container.clientWidth;
    const height = 550;
    
    // Clear previous
    d3.select('#graph-container').html('');
    
    if (!data.nodes || data.nodes.length === 0) {
        d3.select('#graph-container')
            .append('div')
            .attr('class', 'alert alert-info text-center p-5')
            .text('No graph data available. Run analysis first.');
        return;
    }
    
    const svg = d3.select('#graph-container')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Create tooltip
    const tooltip = d3.select('body').append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0);
    
    // Prepare nodes and edges
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    
    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(30));
    
    // Draw edges
    const link = svg.append('g')
        .selectAll('line')
        .data(edges)
        .enter().append('line')
        .attr('class', d => `link link-${d.type || 'default'}`)
        .attr('stroke-width', 1.5);
    
    // Draw nodes
    const node = svg.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', 8)
        .attr('class', d => `node-${d.type || 'unknown'}`)
        .on('mouseover', function(event, d) {
            tooltip.transition().duration(200).style('opacity', 0.9);
            tooltip.html(`
                <strong>${d.id || 'Unknown'}</strong><br>
                Type: ${d.type || 'unknown'}<br>
                ${d.purpose_statement ? 'Purpose: ' + d.purpose_statement.substring(0, 100) + '...' : ''}
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition().duration(500).style('opacity', 0);
        })
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Add labels
    const label = svg.append('g')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .text(d => {
            const id = d.id || '';
            return id.split('/').pop().substring(0, 15);
        })
        .attr('font-size', '10px')
        .attr('dx', 12)
        .attr('dy', 4);
    
    // Simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        
        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });
    
    // Drag functions
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }
}

// Refresh graph
function refreshGraph() {
    loadGraph();
}

// Load lineage data
function loadLineage() {
    console.log('Loading lineage data...');
    fetch('/api/lineage')
        .then(response => response.json())
        .then(data => {
            console.log('Lineage data received:', data);
            lineageData = data;
            
            // Update sources and sinks lists
            updateSourcesSinks(data);
            
            // Draw the graph if nodes exist
            if (data.nodes && data.nodes.length > 0) {
                drawLineageGraph(data);
            } else {
                document.getElementById('lineage-container').innerHTML = 
                    '<div class="alert alert-info text-center p-5">No lineage graph data available</div>';
            }
        })
        .catch(error => console.error('Error loading lineage:', error));
}

// Update sources and sinks lists
function updateSourcesSinks(data) {
    console.log('Updating sources/sinks with:', data);
    
    const sourcesList = document.getElementById('sources-list');
    const sinksList = document.getElementById('sinks-list');
    
    if (!sourcesList || !sinksList) {
        console.error('Source/sink list elements not found');
        return;
    }
    
    // Clear existing lists
    sourcesList.innerHTML = '';
    sinksList.innerHTML = '';
    
    // Get sources and sinks from data (your backend already cleaned them)
    let sources = data.sources || [];
    let sinks = data.sinks || [];
    
    console.log('Sources from backend:', sources);
    console.log('Sinks from backend:', sinks);
    
    // If no sources/sinks in data, try to extract from nodes (fallback)
    if (sources.length === 0 && data.nodes) {
        console.log('No sources in data, extracting from nodes...');
        sources = data.nodes
            .filter(n => {
                const id = typeof n === 'string' ? n : n.id || '';
                return id.includes('source:') || 
                       id.includes('dataset:raw_') ||
                       id.includes('DBT_JOB') ||
                       id.includes('${');
            })
            .map(n => {
                if (typeof n === 'string') return n;
                return n.display_name || n.id || '';
            })
            .filter(id => id);
    }
    
    if (sinks.length === 0 && data.nodes) {
        console.log('No sinks in data, extracting from nodes...');
        sinks = data.nodes
            .filter(n => {
                const id = typeof n === 'string' ? n : n.id || '';
                return id.includes('model:') || 
                       id.includes('customers') ||
                       id.includes('orders') ||
                       id.includes('products') ||
                       id.includes('supplies');
            })
            .map(n => {
                if (typeof n === 'string') return n;
                return n.display_name || n.id || '';
            })
            .filter(id => id);
    }
    
    // Display sources
    if (sources.length > 0) {
        sources.slice(0, 30).forEach(src => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = src; // Your backend already cleaned these
            li.title = src;
            sourcesList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.className = 'list-group-item text-muted';
        li.textContent = 'No source datasets found';
        sourcesList.appendChild(li);
    }
    
    // Display sinks
    if (sinks.length > 0) {
        sinks.slice(0, 30).forEach(sink => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = sink; // Your backend already cleaned these
            li.title = sink;
            sinksList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.className = 'list-group-item text-muted';
        li.textContent = 'No sink datasets found';
        sinksList.appendChild(li);
    }
}

// Draw lineage graph
function drawLineageGraph(data) {
    const container = document.getElementById('lineage-container');
    if (!container) return;
    
    const width = container.clientWidth || 800;
    const height = 450;
    
    // Clear previous
    d3.select('#lineage-container').html('');
    
    if (!data.nodes || data.nodes.length === 0) {
        d3.select('#lineage-container')
            .append('div')
            .attr('class', 'alert alert-info text-center p-5')
            .text('No lineage graph data available');
        return;
    }
    
    const svg = d3.select('#lineage-container')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('background', '#fafafa');
    
    // Create tooltip
    const tooltip = d3.select('body').append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0);
    
    // Prepare nodes with display names
    const nodes = data.nodes.map((node, i) => {
        const nodeId = typeof node === 'string' ? node : node.id;
        const displayName = node.display_name || nodeId.split('\\').pop().split('/').pop() || nodeId;
        return {
            id: nodeId,
            displayName: displayName.substring(0, 25),
            fullName: nodeId,
            type: node.type || 'unknown',
            index: i
        };
    });
    
    const edges = data.edges || [];
    
    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-500))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(50));
    
    // Draw edges
    const link = svg.append('g')
        .selectAll('line')
        .data(edges)
        .enter().append('line')
        .attr('class', 'link-lineage')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.4)
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', d => d.type === 'depends_on' ? '5,5' : 'none');
    
    // Draw nodes
    const node = svg.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', d => d.type === 'dataset' ? 10 : 8)
        .attr('fill', d => {
            if (d.type === 'dataset') return '#4ecdc4';
            if (d.type === 'transformation') return '#ff6b6b';
            if (d.type === 'source') return '#95a5a6';
            if (d.type === 'model') return '#9b59b6';
            return '#3498db';
        })
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .on('mouseover', function(event, d) {
            tooltip.transition().duration(200).style('opacity', 0.9);
            tooltip.html(`
                <strong>${d.displayName}</strong><br>
                Type: ${d.type}<br>
                <small>${d.fullName}</small>
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition().duration(500).style('opacity', 0);
        })
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Add labels
    const label = svg.append('g')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .text(d => d.displayName)
        .attr('font-size', '9px')
        .attr('dx', 12)
        .attr('dy', 4)
        .attr('fill', '#333')
        .style('pointer-events', 'none');
    
    // Simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        
        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });
    
    // Drag functions
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }
}

// Load documentation
function loadDocs() {
    fetch('/api/codebase')
        .then(response => response.json())
        .then(data => {
            const elem = document.getElementById('codebase-content');
            if (elem) elem.textContent = data.content || '';
        })
        .catch(error => console.error('Error loading codebase:', error));
    
    fetch('/api/brief')
        .then(response => response.json())
        .then(data => {
            const elem = document.getElementById('brief-content');
            if (elem) elem.textContent = data.content || '';
        })
        .catch(error => console.error('Error loading brief:', error));
}

// Load trace logs
function loadTrace() {
    fetch('/api/trace')
        .then(response => response.json())
        .then(data => {
            const traceList = document.getElementById('trace-list');
            if (!traceList) return;
            
            traceList.innerHTML = '';
            
            if (data.length === 0) {
                traceList.innerHTML = '<div class="alert alert-info">No trace logs available</div>';
                return;
            }
            
            data.slice(0, 50).forEach(trace => {
                const div = document.createElement('div');
                div.className = `trace-item trace-${trace.status || 'info'}`;
                div.innerHTML = `
                    <small class="text-muted">${new Date(trace.timestamp).toLocaleString()}</small><br>
                    <strong>${trace.action}</strong> - <span class="badge bg-${trace.status === 'success' ? 'success' : trace.status === 'error' ? 'danger' : 'secondary'}">${trace.status}</span><br>
                    ${trace.confidence ? `Confidence: ${trace.confidence}<br>` : ''}
                    ${trace.details ? `<pre>${JSON.stringify(trace.details, null, 2)}</pre>` : ''}
                `;
                traceList.appendChild(div);
            });
        })
        .catch(error => console.error('Error loading trace:', error));
}

// Export functions
function exportDot() {
    window.location.href = '/api/export/dot';
}

function exportMermaid() {
    window.location.href = '/api/export/mermaid';
}

function exportJSON() {
    fetch('/api/graph')
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'knowledge_graph.json';
            a.click();
        });
}

function exportCodebase() {
    fetch('/api/codebase')
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([data.content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'CODEBASE.md';
            a.click();
        });
}

function exportBrief() {
    fetch('/api/brief')
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([data.content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'onboarding_brief.md';
            a.click();
        });
}