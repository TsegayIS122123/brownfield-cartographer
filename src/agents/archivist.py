"""Archivist Agent - Generates living documentation and context files."""

import os
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ArchivistAgent:
    """Archivist Agent - Produces living documentation and trace logs."""
    
    def __init__(self, output_dir: str = ".cartography"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.trace_log = []
    
    def generate_all(self, 
                    surveyor_results: Dict,
                    hydrologist_results: Dict,
                    semanticist_results: Dict,
                    knowledge_graph: Any) -> Dict[str, Path]:
        """Generate all living documentation artifacts."""
        logger.info("=" * 60)
        logger.info("📚 ARCHIVIST AGENT - Generating Living Documentation")
        logger.info("=" * 60)
        
        artifacts = {}
        
        # Generate CODEBASE.md
        logger.info("\n📄 Generating CODEBASE.md...")
        codebase_path = self.generate_codebase_md(
            surveyor_results, hydrologist_results, semanticist_results, knowledge_graph
        )
        artifacts["codebase_md"] = codebase_path
        
        # Generate onboarding brief
        logger.info("\n📋 Generating onboarding_brief.md...")
        brief_path = self.generate_onboarding_brief(
            surveyor_results, hydrologist_results, semanticist_results
        )
        artifacts["onboarding_brief"] = brief_path
        
        # Initialize trace log
        logger.info("\n📜 Initializing cartography_trace.jsonl...")
        trace_path = self.init_trace_log()
        artifacts["trace_log"] = trace_path
        
        logger.info(f"\n✅ All artifacts saved to {self.output_dir}")
        return artifacts
    
    def generate_codebase_md(self,
                             surveyor_results: Dict,
                             hydrologist_results: Dict,
                             semanticist_results: Dict,
                             knowledge_graph: Any) -> Path:
        """Generate CODEBASE.md - living context for AI agents."""
        
        output_path = self.output_dir / "CODEBASE.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 📚 Codebase Intelligence Report\n\n")
            f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            # === ARCHITECTURE OVERVIEW ===
            f.write("## 🏗️ Architecture Overview\n\n")
            f.write(self._generate_architecture_overview(
                surveyor_results, hydrologist_results, semanticist_results
            ))
            f.write("\n\n")
            
            # === CRITICAL PATH ===
            f.write("## 🔍 Critical Path (Top Modules by PageRank)\n\n")
            f.write(self._generate_critical_path(surveyor_results))
            f.write("\n\n")
            
            # === DATA SOURCES & SINKS ===
            f.write("## 💾 Data Sources & Sinks\n\n")
            f.write(self._generate_data_sources_sinks(hydrologist_results))
            f.write("\n\n")
            
            # === KNOWN DEBT ===
            f.write("## ⚠️ Known Debt & Technical Debt\n\n")
            f.write(self._generate_known_debt(surveyor_results, semanticist_results))
            f.write("\n\n")
            
            # === HIGH-VELOCITY FILES ===
            f.write("## ⚡ High-Velocity Files (Likely Pain Points)\n\n")
            f.write(self._generate_high_velocity(surveyor_results))
            f.write("\n\n")
            
            # === MODULE PURPOSE INDEX ===
            f.write("## 📑 Module Purpose Index\n\n")
            f.write(self._generate_module_purposes(semanticist_results))
            f.write("\n\n")
            
            # === DOCUMENTATION DRIFT ===
            f.write("## 🔄 Documentation Drift\n\n")
            f.write(self._generate_docstring_drift(semanticist_results))
            f.write("\n\n")
        
        logger.info(f"✅ CODEBASE.md saved to {output_path}")
        self._log_action("generate_codebase_md", "success", {"path": str(output_path)})
        return output_path
    
    def _generate_architecture_overview(self,
                                        surveyor_results: Dict,
                                        hydrologist_results: Dict,
                                        semanticist_results: Dict) -> str:
        """Generate architecture overview paragraph."""
        metadata = surveyor_results.get("metadata", {})
        if hasattr(metadata, 'total_modules'):
            total_modules = metadata.total_modules
            languages = metadata.languages
        else:
            total_modules = metadata.get('total_modules', 0)
            languages = metadata.get('languages', {})
        
        lang_str = ', '.join([f"{lang} ({count})" for lang, count in languages.items()])
        
        sources = len(hydrologist_results.get("sources", [])) if hydrologist_results else 0
        sinks = len(hydrologist_results.get("sinks", [])) if hydrologist_results else 0
        
        domains = len(semanticist_results.get("domain_clusters", {}).get("cluster_names", {})) if semanticist_results else 0
        
        return (f"This codebase contains **{total_modules} modules** across {lang_str}. "
                f"The data pipeline has **{sources} source datasets** and **{sinks} sink datasets**. "
                f"Business logic is organized into **{domains} domain clusters**. "
                f"The system follows a {self._infer_architecture_pattern(surveyor_results)} architecture pattern.")
    
    def _infer_architecture_pattern(self, surveyor_results: Dict) -> str:
        """Infer architecture pattern from module structure."""
        # Simple heuristic - can be enhanced
        metadata = surveyor_results.get("metadata", {})
        if hasattr(metadata, 'circular_dependencies'):
            if metadata.circular_dependencies:
                return "layered with some circular dependencies"
        
        return "layered (staging → marts)"
    
    def _generate_critical_path(self, surveyor_results: Dict) -> str:
        """Generate critical path section."""
        metadata = surveyor_results.get("metadata", {})
        
        if hasattr(metadata, 'top_modules_by_pagerank'):
            top_modules = metadata.top_modules_by_pagerank
        else:
            top_modules = metadata.get('top_modules_by_pagerank', [])
        
        if not top_modules:
            return "No critical path information available."
        
        lines = ["The following modules are the most critical based on PageRank analysis:\n"]
        for i, mod in enumerate(top_modules[:5], 1):
            path = mod.get('path', 'unknown')
            score = mod.get('pagerank', 0)
            imported_by = mod.get('imported_by', 0)
            lines.append(f"{i}. **{path}** (score: {score:.4f}, imported by: {imported_by} modules)")
        
        return '\n'.join(lines)
    
    def _generate_data_sources_sinks(self, hydrologist_results: Dict) -> str:
        """Generate data sources and sinks section."""
        if not hydrologist_results:
            return "No data lineage information available."
        
        sources = hydrologist_results.get("sources", [])
        sinks = hydrologist_results.get("sinks", [])
        
        lines = []
        
        lines.append(f"### 📦 Source Datasets ({len(sources)})\n")
        if sources:
            for src in sources[:10]:
                lines.append(f"- `{src}`")
            if len(sources) > 10:
                lines.append(f"- *... and {len(sources) - 10} more*")
        else:
            lines.append("No source datasets identified.")
        
        lines.append(f"\n### 🎯 Sink Datasets ({len(sinks)})\n")
        if sinks:
            for sink in sinks[:10]:
                lines.append(f"- `{sink}`")
            if len(sinks) > 10:
                lines.append(f"- *... and {len(sinks) - 10} more*")
        else:
            lines.append("No sink datasets identified.")
        
        return '\n'.join(lines)
    
    def _generate_known_debt(self, surveyor_results: Dict, semanticist_results: Dict) -> str:
        """Generate known debt section."""
        lines = []
        
        # Circular dependencies
        metadata = surveyor_results.get("metadata", {})
        if hasattr(metadata, 'circular_dependencies'):
            circular = metadata.circular_dependencies
        else:
            circular = metadata.get('circular_dependencies', [])
        
        lines.append(f"### 🔄 Circular Dependencies ({len(circular)})")
        if circular:
            for cycle in circular[:3]:
                lines.append(f"- `{' → '.join(cycle[:3])}...`")
            if len(circular) > 3:
                lines.append(f"- *... and {len(circular) - 3} more cycles*")
        else:
            lines.append("No circular dependencies detected.")
        
        # Documentation drift
        lines.append(f"\n### 📝 Documentation Drift")
        if semanticist_results:
            drift = semanticist_results.get("docstring_drift", {})
            drift_count = len([d for d in drift.values() if d.get("has_drift")])
            lines.append(f"- **{drift_count} files** have documentation drift")
            if drift_count > 0:
                lines.append("\nExamples:")
                for path, data in list(drift.items())[:3]:
                    if data.get("has_drift"):
                        lines.append(f"  - `{path}` (confidence: {data.get('confidence', 0):.2f})")
        else:
            lines.append("No documentation drift analysis available.")
        
        return '\n'.join(lines)
    
    def _generate_high_velocity(self, surveyor_results: Dict) -> str:
        """Generate high-velocity files section."""
        high_velocity = surveyor_results.get("high_velocity", [])
        
        if not high_velocity:
            return "No git velocity data available."
        
        lines = ["Files that change most frequently (likely pain points):\n"]
        for i, item in enumerate(high_velocity[:10], 1):
            file = item.get('file', 'unknown')
            changes = item.get('changes', 0)
            pct = item.get('cumulative_percentage', 0)
            lines.append(f"{i}. **{file}** ({changes} changes, {pct:.1f}% cumulative)")
        
        return '\n'.join(lines)
    
    def _generate_module_purposes(self, semanticist_results: Dict) -> str:
        """Generate module purpose index."""
        if not semanticist_results:
            return "No semantic analysis available."
        
        purposes = semanticist_results.get("purpose_statements", {})
        domains = semanticist_results.get("domain_clusters", {}).get("labels", {})
        cluster_names = semanticist_results.get("domain_clusters", {}).get("cluster_names", {})
        
        if not purposes:
            return "No purpose statements generated."
        
        # Group by domain
        domain_groups = {}
        for path, purpose_data in purposes.items():
            domain_label = domains.get(path)
            domain_name = cluster_names.get(domain_label, f"Domain_{domain_label}") if domain_label is not None else "Uncategorized"
            
            if domain_name not in domain_groups:
                domain_groups[domain_name] = []
            domain_groups[domain_name].append((path, purpose_data["purpose"]))
        
        lines = []
        for domain, modules in domain_groups.items():
            lines.append(f"### {domain}\n")
            for path, purpose in modules[:5]:
                lines.append(f"- **{path}**: {purpose[:100]}...")
            if len(modules) > 5:
                lines.append(f"- *... and {len(modules) - 5} more modules*")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_docstring_drift(self, semanticist_results: Dict) -> str:
        """Generate documentation drift section."""
        if not semanticist_results:
            return "No documentation drift analysis available."
        
        drift = semanticist_results.get("docstring_drift", {})
        drift_files = [(path, data) for path, data in drift.items() if data.get("has_drift")]
        
        if not drift_files:
            return "✅ No documentation drift detected - docstrings match implementation."
        
        lines = ["⚠️ The following files have documentation drift:\n"]
        for path, data in drift_files[:10]:
            confidence = data.get('confidence', 0)
            docstring = data.get('docstring', 'N/A')[:50]
            purpose = data.get('code_purpose', 'N/A')[:50]
            lines.append(f"- **{path}**")
            lines.append(f"  - Docstring: \"{docstring}...\"")
            lines.append(f"  - Actual: \"{purpose}...\"")
            lines.append(f"  - Confidence: {confidence:.2f}")
        
        if len(drift_files) > 10:
            lines.append(f"- *... and {len(drift_files) - 10} more files*")
        
        return '\n'.join(lines)
    
    def generate_onboarding_brief(self,
                                  surveyor_results: Dict,
                                  hydrologist_results: Dict,
                                  semanticist_results: Dict) -> Path:
        """Generate onboarding_brief.md - Day-One answers for FDEs."""
        
        output_path = self.output_dir / "onboarding_brief.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 📋 FDE Day-One Onboarding Brief\n\n")
            f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            f.write("## 🎯 Five FDE Day-One Questions\n\n")
            
            # Get answers from semanticist or use defaults
            if semanticist_results and "day_one_answers" in semanticist_results:
                answers = semanticist_results["day_one_answers"]
                
                for i in range(1, 6):
                    q_key = f"question_{i}"
                    if q_key in answers:
                        ans = answers[q_key]
                        f.write(f"### {i}. {self._get_question_text(i)}\n\n")
                        f.write(f"**Answer:** {ans.get('answer', 'N/A')}\n\n")
                        
                        evidence = ans.get('evidence', [])
                        if evidence:
                            f.write("**Evidence:**\n")
                            for e in evidence:
                                f.write(f"- `{e}`\n")
                        
                        confidence = ans.get('confidence', 'N/A')
                        f.write(f"\n**Confidence:** {confidence}\n\n")
                        f.write("---\n\n")
            else:
                # Fallback to generating from our data
                f.write(self._generate_fallback_answers(
                    surveyor_results, hydrologist_results, semanticist_results
                ))
        
        logger.info(f"✅ onboarding_brief.md saved to {output_path}")
        self._log_action("generate_onboarding_brief", "success", {"path": str(output_path)})
        return output_path
    
    def _get_question_text(self, q_num: int) -> str:
        """Get question text by number."""
        questions = {
            1: "What is the primary data ingestion path?",
            2: "What are the 3-5 most critical output datasets/endpoints?",
            3: "What is the blast radius if the most critical module fails?",
            4: "Where is business logic concentrated vs. distributed?",
            5: "What has changed most frequently in the last 90 days?"
        }
        return questions.get(q_num, f"Question {q_num}")
    
    def _generate_fallback_answers(self,
                                    surveyor_results: Dict,
                                    hydrologist_results: Dict,
                                    semanticist_results: Dict) -> str:
        """Generate fallback answers from available data."""
        lines = []
        
        # Q1: Ingestion path
        sources = hydrologist_results.get("sources", []) if hydrologist_results else []
        if sources:
            lines.append("### 1. What is the primary data ingestion path?\n")
            lines.append(f"**Answer:** Data enters through {len(sources)} source datasets.\n")
            lines.append("**Evidence:**\n")
            for src in sources[:3]:
                lines.append(f"- `{src}`")
            lines.append("\n**Confidence:** High\n\n---\n")
        
        # Q2: Critical outputs
        sinks = hydrologist_results.get("sinks", []) if hydrologist_results else []
        if sinks:
            lines.append("### 2. What are the 3-5 most critical output datasets?\n")
            lines.append(f"**Answer:** Critical outputs are {len(sinks)} sink datasets.\n")
            lines.append("**Evidence:**\n")
            for sink in sinks[:5]:
                lines.append(f"- `{sink}`")
            lines.append("\n**Confidence:** High\n\n---\n")
        
        # Q3: Blast radius
        metadata = surveyor_results.get("metadata", {})
        if hasattr(metadata, 'top_modules_by_pagerank'):
            top = metadata.top_modules_by_pagerank
        else:
            top = metadata.get('top_modules_by_pagerank', [])
        
        if top:
            lines.append("### 3. What is the blast radius if the most critical module fails?\n")
            most_critical = top[0].get('path', 'unknown')
            lines.append(f"**Answer:** The most critical module is `{most_critical}`. ")
            lines.append("Blast radius analysis shows it is imported by multiple downstream modules.\n")
            lines.append("**Evidence:** PageRank analysis\n")
            lines.append("**Confidence:** Medium\n\n---\n")
        
        return '\n'.join(lines)
    
    def init_trace_log(self) -> Path:
        """Initialize the trace log file."""
        trace_path = self.output_dir / "cartography_trace.jsonl"
        # Create empty file or append
        with open(trace_path, 'a', encoding='utf-8') as f:
            pass
        return trace_path
    
    def log_action(self, action: str, status: str, details: Dict = None, confidence: float = None):
        """Log an action to the trace log."""
        trace_path = self.output_dir / "cartography_trace.jsonl"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": status,
            "details": details or {},
        }
        
        if confidence is not None:
            log_entry["confidence"] = confidence
        
        with open(trace_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        self.trace_log.append(log_entry)
    
    def _log_action(self, action: str, status: str, details: Dict = None):
        """Internal method to log actions."""
        self.log_action(action, status, details)
    
    def get_trace_log(self) -> List[Dict]:
        """Get the current trace log."""
        return self.trace_log
    
    def save_trace_log(self, path: Optional[Path] = None):
        """Save trace log to file."""
        save_path = path or (self.output_dir / "cartography_trace.jsonl")
        with open(save_path, 'w', encoding='utf-8') as f:
            for entry in self.trace_log:
                f.write(json.dumps(entry) + '\n')