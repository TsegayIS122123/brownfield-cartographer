"""Navigator Agent - LangGraph-based query interface."""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import networkx as nx

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool  # 👈 ADD THIS IMPORT
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logging.warning("LangGraph not installed. Install with: uv pip install langgraph langchain-core")
    # Define a dummy decorator when LangGraph not available
    def tool(func):
        return func

logger = logging.getLogger(__name__)


class NavigatorAgent:
    """Navigator Agent - LangGraph-powered query interface."""
    
    def __init__(self, 
                 knowledge_graph: Any,
                 lineage_graph: Any,
                 semanticist_results: Dict,
                 archivist: Any):
        self.kg = knowledge_graph
        self.lg = lineage_graph
        self.semanticist = semanticist_results
        self.archivist = archivist
        self.tools = self._create_tools()
        self.graph = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
    
    def _create_tools(self) -> List[Callable]:
        """Create the four core tools."""
        
        @tool
        def find_implementation(concept: str) -> str:
            """Find where a concept is implemented in the codebase.
            
            Args:
                concept: The business concept to search for (e.g., "revenue calculation")
            """
            results = []
            
            # Search in purpose statements
            purposes = self.semanticist.get("purpose_statements", {})
            for path, data in purposes.items():
                purpose = data.get("purpose", "").lower()
                if concept.lower() in purpose:
                    results.append({
                        "path": path,
                        "evidence": f"Purpose statement: {data.get('purpose', '')}",
                        "method": "LLM inference",
                        "confidence": 0.85
                    })
            
            # Search in module names
            if self.kg and hasattr(self.kg, 'graph'):
                for node in self.kg.graph.nodes():
                    if concept.lower() in node.lower():
                        results.append({
                            "path": node,
                            "evidence": "Module name match",
                            "method": "static analysis",
                            "confidence": 0.7
                        })
            
            if not results:
                return f"No implementation found for '{concept}'"
            
            # Format results
            output = f"Found {len(results)} implementations for '{concept}':\n\n"
            for r in results[:5]:
                output += f"📁 **{r['path']}**\n"
                output += f"   - Evidence: {r['evidence']}\n"
                output += f"   - Method: {r['method']} (confidence: {r['confidence']:.2f})\n\n"
            
            self.archivist.log_action(
                "find_implementation",
                "success",
                {"concept": concept, "results": len(results)},
                confidence=0.85
            )
            
            return output
        
        @tool
        def trace_lineage(dataset: str, direction: str = "both") -> str:
            """Trace data lineage upstream or downstream from a dataset.
            
            Args:
                dataset: The dataset name to trace
                direction: "upstream", "downstream", or "both"
            """
            if not self.lg:
                return "Lineage graph not available"
            
            # Try to find the dataset in the graph
            found = None
            for node in self.lg.graph.nodes():
                if dataset.lower() in node.lower():
                    found = node
                    break
            
            if not found:
                return f"Dataset '{dataset}' not found in lineage graph"
            
            result = self.lg.trace_lineage(found, direction)
            
            if "error" in result:
                return result["error"]
            
            output = f"📊 Lineage trace for `{found}` ({direction}):\n\n"
            
            if result.get("upstream"):
                output += f"**Upstream dependencies ({len(result['upstream'])}):**\n"
                for u in result["upstream"][:10]:
                    output += f"- `{u}`\n"
                if len(result["upstream"]) > 10:
                    output += f"- *... and {len(result['upstream']) - 10} more*\n"
                output += "\n"
            
            if result.get("downstream"):
                output += f"**Downstream dependents ({len(result['downstream'])}):**\n"
                for d in result["downstream"][:10]:
                    output += f"- `{d}`\n"
                if len(result["downstream"]) > 10:
                    output += f"- *... and {len(result['downstream']) - 10} more*\n"
                output += "\n"
            
            if result.get("transformations"):
                output += f"**Transformations using this dataset ({len(result['transformations'])}):**\n"
                for t in result["transformations"][:5]:
                    output += f"- `{t['name']}` (operation: {t.get('operation', 'unknown')})\n"
            
            self.archivist.log_action(
                "trace_lineage",
                "success",
                {"dataset": dataset, "direction": direction, "found": found}
            )
            
            return output
        
        @tool
        def blast_radius(module: str) -> str:
            """Calculate the blast radius if a module fails.
            
            Args:
                module: The module path to analyze
            """
            if not self.lg:
                return "Lineage graph not available"
            
            # Try to find the module
            found = None
            for node in self.lg.graph.nodes():
                if module.lower() in node.lower():
                    found = node
                    break
            
            if not found:
                # Try in knowledge graph
                if self.kg and hasattr(self.kg, 'graph'):
                    for node in self.kg.graph.nodes():
                        if module.lower() in node.lower():
                            found = node
                            break
            
            if not found:
                return f"Module '{module}' not found"
            
            result = self.lg.blast_radius(found)
            
            if "error" in result:
                return result["error"]
            
            output = f"💥 Blast Radius Analysis for `{found}`\n\n"
            output += f"**Node type:** {result.get('node_type', 'unknown')}\n"
            output += f"**Direct dependents:** {len(result.get('direct_dependents', []))}\n"
            output += f"**Total downstream dependents:** {result.get('dependent_count', 0)}\n\n"
            
            if result.get("dependents_detail"):
                output += "**Dependents by type:**\n"
                type_counts = {}
                for dep in result["dependents_detail"]:
                    dep_type = dep.get('node_type', 'unknown')
                    type_counts[dep_type] = type_counts.get(dep_type, 0) + 1
                
                for dep_type, count in type_counts.items():
                    output += f"- {dep_type}: {count}\n"
                
                output += "\n**Sample dependents:**\n"
                for dep in result["dependents_detail"][:5]:
                    path = dep.get('path', [])
                    if path:
                        path_str = ' → '.join(path)
                    else:
                        path_str = dep.get('node', 'unknown')
                    output += f"- `{path_str}`\n"
            
            self.archivist.log_action(
                "blast_radius",
                "success",
                {"module": module, "found": found, "dependents": result.get('dependent_count', 0)}
            )
            
            return output
        
        @tool
        def explain_module(path: str) -> str:
            """Explain what a module does, its purpose, and dependencies.
            
            Args:
                path: The file path of the module
            """
            output = f"📖 Module Explanation: `{path}`\n\n"
            
            # Get purpose statement
            purposes = self.semanticist.get("purpose_statements", {})
            if path in purposes:
                purpose_data = purposes[path]
                output += f"**Purpose:** {purpose_data.get('purpose', 'N/A')}\n"
                output += f"*(generated by {purpose_data.get('model', 'LLM')}, "
                output += f"cost: ${purpose_data.get('cost', 0):.4f})*\n\n"
            else:
                output += "**Purpose:** No purpose statement available\n\n"
            
            # Get domain
            domains = self.semanticist.get("domain_clusters", {}).get("labels", {})
            cluster_names = self.semanticist.get("domain_clusters", {}).get("cluster_names", {})
            if path in domains:
                label = domains[path]
                domain = cluster_names.get(label, f"Domain_{label}")
                output += f"**Domain:** {domain}\n\n"
            
            # Get dependencies from knowledge graph
            if self.kg and hasattr(self.kg, 'graph'):
                deps = []
                for _, target, data in self.kg.graph.out_edges(path, data=True):
                    if data.get('type') == 'imports':
                        deps.append(target)
                
                if deps:
                    output += f"**Dependencies ({len(deps)}):**\n"
                    for dep in deps[:10]:
                        output += f"- `{dep}`\n"
                    if len(deps) > 10:
                        output += f"- *... and {len(deps) - 10} more*\n"
                    output += "\n"
                
                dependents = []
                for source, _, data in self.kg.graph.in_edges(path, data=True):
                    if data.get('type') == 'imports':
                        dependents.append(source)
                
                if dependents:
                    output += f"**Dependents ({len(dependents)}):**\n"
                    for dep in dependents[:10]:
                        output += f"- `{dep}`\n"
                    if len(dependents) > 10:
                        output += f"- *... and {len(dependents) - 10} more*\n"
                    output += "\n"
            
            # Get docstring drift info
            drift = self.semanticist.get("docstring_drift", {})
            if path in drift and drift[path].get("has_drift"):
                output += "⚠️ **Documentation Drift Detected**\n"
                output += f"  - Docstring: {drift[path].get('docstring', 'N/A')}\n"
                output += f"  - Actual: {drift[path].get('code_purpose', 'N/A')}\n"
                output += f"  - Confidence: {drift[path].get('confidence', 0):.2f}\n\n"
            
            self.archivist.log_action(
                "explain_module",
                "success",
                {"path": path}
            )
            
            return output
        
        return [find_implementation, trace_lineage, blast_radius, explain_module]
    
    def _build_graph(self):
        """Build the LangGraph state graph."""
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available - Navigator will use simple mode")
            return
        
        from langgraph.graph import StateGraph, END
        from langgraph.prebuilt import ToolExecutor
        
        # Define state schema
        class GraphState(dict):
            messages: List[Any]
            next: str
        
        # Create tool executor
        tool_executor = ToolExecutor(self.tools)
        
        # Define nodes
        def call_tool(state):
            messages = state["messages"]
            last_message = messages[-1]
            
            # Parse the last message to determine tool and args
            # This is simplified - in production, use proper parsing
            text = last_message.content.lower()
            
            if "find_implementation" in text or "where is" in text:
                concept = text.replace("find_implementation", "").replace("where is", "").strip()
                result = self.tools[0].func(concept)
            elif "trace_lineage" in text or "lineage" in text:
                # Simplified parsing
                result = "Please specify dataset and direction"
            elif "blast_radius" in text or "blast radius" in text:
                result = "Please specify module path"
            elif "explain_module" in text or "explain" in text:
                result = "Please specify module path"
            else:
                result = "I can help with: find_implementation, trace_lineage, blast_radius, explain_module"
            
            return {"messages": messages + [AIMessage(content=result)]}
        
        # Build graph
        workflow = StateGraph(GraphState)
        
        workflow.add_node("agent", call_tool)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        
        self.graph = workflow.compile()
    
    def query(self, user_input: str) -> str:
        """Process a user query and return response."""
        if not LANGGRAPH_AVAILABLE or not self.graph:
            # Simple fallback mode
            return self._simple_query(user_input)
        
        # Use LangGraph
        state = {
            "messages": [HumanMessage(content=user_input)],
            "next": "agent"
        }
        
        try:
            result = self.graph.invoke(state)
            last_message = result["messages"][-1]
            return last_message.content
        except Exception as e:
            logger.error(f"LangGraph error: {e}")
            return self._simple_query(user_input)
    
    def _simple_query(self, user_input: str) -> str:
        """Simple fallback query handler."""
        text = user_input.lower()
        
        if "where is" in text or "find" in text:
            for word in text.split():
                if len(word) > 3:
                    return self.tools[0].func(word)
        
        if "lineage" in text:
            return "Please specify dataset name with: trace_lineage <dataset>"
        
        if "blast radius" in text:
            return "Please specify module path with: blast_radius <module>"
        
        if "explain" in text:
            return "Please specify module path with: explain_module <path>"
        
        return ("Available commands:\n"
                "- find_implementation <concept>\n"
                "- trace_lineage <dataset> [upstream|downstream|both]\n"
                "- blast_radius <module>\n"
                "- explain_module <path>")
    
    def interactive_mode(self):
        """Run interactive query mode."""
        print("\n" + "=" * 60)
        print("🎮 NAVIGATOR AGENT - Interactive Query Mode")
        print("=" * 60)
        print("Type 'help' for commands, 'exit' to quit\n")
        
        while True:
            try:
                user_input = input("\n🔍 > ").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    print("\nAvailable commands:")
                    print("  find_implementation <concept>   - Find where concept is implemented")
                    print("  trace_lineage <dataset> [dir]   - Trace data lineage (dir: upstream/downstream/both)")
                    print("  blast_radius <module>           - Calculate impact of changing module")
                    print("  explain_module <path>           - Explain what module does")
                    print("  exit                            - Exit query mode")
                    continue
                
                response = self.query(user_input)
                print(f"\n{response}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                print(f"❌ Error: {e}")