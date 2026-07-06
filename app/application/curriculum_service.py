from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.domain.curriculum import CurriculumLevel, CurriculumNode, CurriculumProgress, NodeStatus
from app.memory.contracts import MemoryService

logger = logging.getLogger(__name__)

# Path for JSON file cache
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CURRICULUM_CACHE_FILE = DATA_DIR / "curriculum_{subject_code}.json"


# ---- Pydantic schemas for structured LLM output ----

class LLMCurriculumNode(BaseModel):
    """Schema for a single node returned by the LLM."""
    id: str = Field(description="Unique identifier for this node.")
    parent_id: str | None = Field(description="ID of the parent node, null for root.")
    level: str = Field(description="Hierarchy level: preparation, phase, module, unit, chapter, topic, or concept.")
    title: str = Field(description="Title of this node.")
    learning_order: int = Field(description="Global sequential learning order.")
    prerequisites: list[str] = Field(default_factory=list, description="IDs of prerequisite nodes.")
    dependencies: list[str] = Field(default_factory=list, description="IDs of nodes that depend on this.")
    child_nodes: list[str] = Field(default_factory=list, description="IDs of direct child nodes.")


class LLMCurriculumResponse(BaseModel):
    """Schema for the full curriculum response from the LLM."""
    nodes: list[LLMCurriculumNode] = Field(description="Complete list of curriculum nodes.")


# ---- The mega prompt (from user) ----

CURRICULUM_GENERATION_PROMPT = """You are an expert UPSC mentor, instructional designer, curriculum architect, cognitive scientist, learning scientist, and knowledge graph designer.

Your task is to generate a **scientifically optimized teaching structure and learning roadmap** for **Indian Polity & Constitution** for the **UPSC Civil Services Examination (Prelims + Mains)**.

Your objective is **NOT** to teach the subject.

Your objective is to design **the optimal learning sequence**.

The output will be stored directly in a database and later consumed by an adaptive learning platform.

## Objective

Design the most efficient teaching structure possible that minimizes study effort while maximizing:

* Long-term retention
* Conceptual clarity
* Learning speed
* Knowledge transfer
* Recall accuracy
* Inter-topic connections
* Exam performance
* Cognitive efficiency
* Mastery
* Learning throughput

The roadmap must be based on evidence from:

* Cognitive Science
* Learning Science
* Educational Psychology
* Instructional Design
* Neuroscience
* Expertise Development
* Deliberate Practice
* Memory Research

Apply principles such as:

* Active Recall
* Retrieval Practice
* Spaced Repetition
* Spiral Learning
* Interleaving
* Chunking
* Cognitive Load Theory
* Scaffolding
* Mastery Learning
* Progressive Complexity
* Desirable Difficulties
* Testing Effect
* Knowledge Graph Learning
* Adaptive Learning
* Error-Based Learning
* Elaboration
* Feynman Technique

The roadmap should optimize for understanding before memorization.

Never introduce a concept before all of its prerequisites have been taught.

---

# Scope

Generate the complete learning structure for **Indian Polity & Constitution** covering the entire UPSC syllabus, including (but not limited to):

* Constitutional History
* Making of the Constitution
* Historical Acts
* Constituent Assembly
* Philosophy of the Constitution
* Preamble
* Union and its Territory
* Citizenship
* Fundamental Rights
* Directive Principles of State Policy
* Fundamental Duties
* Amendment Process
* Basic Structure Doctrine
* Union Executive
* President
* Vice President
* Prime Minister
* Council of Ministers
* Cabinet
* Parliament
* Legislative Procedure
* Parliamentary Committees
* Parliamentary Privileges
* Judiciary
* Supreme Court
* High Courts
* Subordinate Judiciary
* Judicial Review
* Judicial Activism
* Judicial Independence
* Federalism
* Centre-State Relations
* Inter-State Relations
* Emergency Provisions
* State Executive
* Governor
* Chief Minister
* State Legislature
* Local Government
* Panchayati Raj
* Municipalities
* Union Territories
* Constitutional Bodies
* Statutory Bodies
* Regulatory Bodies
* Non-Constitutional Bodies
* Election Commission
* UPSC
* Finance Commission
* CAG
* Attorney General
* Advocate General
* Special Provisions
* Scheduled Areas
* Tribes
* Official Language
* Constitutional Schedules
* Constitutional Articles
* Important Amendments
* Important Judgments
* Governance concepts relevant to Polity
* Contemporary Constitutional Developments relevant to UPSC

No topic required for UPSC should be omitted.

---

# Curriculum Design Rules

Design the curriculum based on prerequisite relationships rather than book order.

Every concept must appear only after all foundational concepts required to understand it have already been introduced.

If multiple learning paths exist, choose the one that minimizes total cognitive load.

Group concepts into logical learning modules.

Avoid unnecessary context switching.

Create the shortest possible path to mastery.

---

# Hierarchy

Create a strict hierarchical structure.

Preparation

→ Phase

→ Module

→ Unit

→ Chapter

→ Topic

→ Concept

Every node must clearly reference its parent.

---

# For Every Node Return

* id
* parent_id
* level
* title
* learning_order
* prerequisites
* dependencies
* child_nodes

No additional fields.

---

# Learning Progression

The roadmap should naturally move through stages like:

Foundation

↓

Core Concepts

↓

Concept Connections

↓

Institutional Understanding

↓

Constitutional Framework

↓

Governance Applications

↓

Advanced Constitutional Interpretation

↓

Judicial Doctrines

↓

Integrated Polity

↓

UPSC-Level Mastery

---

# Dependency Mapping

Every topic should explicitly define:

* what must already be known
* which future topics depend upon it

Dependencies should form a Directed Acyclic Graph (DAG).

Avoid circular dependencies.

---

# Ordering Constraints

Always introduce:

* simpler before complex
* concrete before abstract
* static before dynamic
* constitutional foundations before institutions
* institutions before governance
* governance before current constitutional issues
* concepts before exceptions
* theory before application

---

# Coverage

The roadmap must include every concept necessary for:

* UPSC Prelims
* UPSC Mains GS-II
* Polity-related Current Affairs integration
* Constitutional analysis
* Governance understanding

---

# Output Format

Return only the hierarchical teaching structure as a JSON object with a "nodes" array.

Do not teach any topic.

Do not define concepts.

Do not summarize.

Do not explain ordering.

Do not provide descriptions.

Do not include notes.

Do not include study tips.

Do not include examples.

The response must consist exclusively of the complete teaching structure for Indian Polity & Constitution, optimized for UPSC preparation and ready for direct storage in a database."""


class CurriculumService:
    def __init__(
        self,
        memory_service: MemoryService,
        model: str = "gemini-2.5-pro",
        api_key: str | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._model = model
        kwargs: dict[str, object] = {
            "model": model,
            "temperature": 0.1,
            "max_retries": 5,
            "timeout": 300,
        }
        if api_key:
            kwargs["google_api_key"] = api_key

        self._llm = ChatGoogleGenerativeAI(**kwargs)

        self._structured_llm = self._llm.with_structured_output(LLMCurriculumResponse)
        logger.info("curriculum_service_initialized model=%s", model)

    # ---- Public API ----

    async def ensure_curriculum(self, subject_code: str) -> list[CurriculumNode]:
        """Ensure curriculum exists: load from memory, then file cache, then generate."""
        # 1. Check in-memory store
        existing = await self._memory_service.get_curriculum(subject_code)
        if existing:
            logger.info("curriculum_loaded source=memory subject=%s node_count=%d", subject_code, len(existing))
            return existing

        # 2. Check file cache
        nodes = self._load_from_file(subject_code)
        if nodes:
            await self._memory_service.store_curriculum(subject_code, nodes)
            logger.info("curriculum_loaded source=file subject=%s node_count=%d", subject_code, len(nodes))
            return nodes

        # 3. Generate from LLM
        logger.info("curriculum_generate_start subject=%s", subject_code)
        nodes = await self._generate_curriculum(subject_code)
        await self._memory_service.store_curriculum(subject_code, nodes)
        self._save_to_file(subject_code, nodes)
        logger.info("curriculum_generate_complete subject=%s node_count=%d", subject_code, len(nodes))
        return nodes

    async def get_curriculum_tree(self, subject_code: str) -> list[dict[str, Any]]:
        """Return the curriculum as a nested tree structure."""
        nodes = await self._memory_service.get_curriculum(subject_code)
        if not nodes:
            nodes = await self.ensure_curriculum(subject_code)

        # Build tree from flat list
        node_map = {n.id: n for n in nodes}
        root_nodes = [n for n in nodes if n.parent_id is None]

        def build_tree(node: CurriculumNode) -> dict[str, Any]:
            children = [node_map[cid] for cid in node.child_ids if cid in node_map]
            return {
                "id": node.id,
                "level": node.level,
                "title": node.title,
                "learning_order": node.learning_order,
                "prerequisites": list(node.prerequisites),
                "children": [build_tree(c) for c in sorted(children, key=lambda x: x.learning_order)],
            }

        return [build_tree(r) for r in sorted(root_nodes, key=lambda x: x.learning_order)]

    async def get_user_progress_summary(
        self, user_id: UUID, subject_code: str,
    ) -> dict[str, Any]:
        """Get a summary of user's curriculum progress."""
        nodes = await self._memory_service.get_curriculum(subject_code)
        leaf_nodes = await self._memory_service.get_leaf_nodes(subject_code)
        progress_list = await self._memory_service.get_curriculum_progress(user_id, subject_code)
        current_node, current_progress = await self._memory_service.get_current_curriculum_position(
            user_id, subject_code,
        )

        completed = [p for p in progress_list if p.status == NodeStatus.COMPLETED]
        in_progress = [p for p in progress_list if p.status == NodeStatus.IN_PROGRESS]

        total_leaf = len(leaf_nodes)
        completed_leaf = sum(
            1 for ln in leaf_nodes
            if any(p.node_id == ln.id and p.status == NodeStatus.COMPLETED for p in progress_list)
        )

        # Build breadcrumb path for current position
        current_path = []
        if current_node:
            node_map = {n.id: n for n in nodes}
            walk = current_node
            while walk:
                current_path.insert(0, {"id": walk.id, "title": walk.title, "level": walk.level})
                walk = node_map.get(walk.parent_id) if walk.parent_id else None

        return {
            "subject_code": subject_code,
            "total_nodes": len(nodes),
            "total_leaf_nodes": total_leaf,
            "completed_leaf_nodes": completed_leaf,
            "in_progress_count": len(in_progress),
            "completion_percent": round(completed_leaf / total_leaf * 100) if total_leaf else 0,
            "current_position": {
                "node_id": current_node.id if current_node else None,
                "title": current_node.title if current_node else None,
                "level": current_node.level if current_node else None,
                "status": current_progress.status if current_progress else NodeStatus.NOT_STARTED,
                "path": current_path,
            } if current_node else None,
        }

    async def get_studied_topics_count(self, user_id: UUID, subject_code: str) -> int:
        """Count topics (leaf nodes) the user has actually started or completed."""
        leaf_nodes = await self._memory_service.get_leaf_nodes(subject_code)
        progress_list = await self._memory_service.get_curriculum_progress(user_id, subject_code)
        progress_ids = {p.node_id for p in progress_list if p.status != NodeStatus.NOT_STARTED}
        return sum(1 for ln in leaf_nodes if ln.id in progress_ids)

    # ---- Private methods ----

    async def _generate_curriculum(self, subject_code: str) -> list[CurriculumNode]:
        """Call the LLM to generate the curriculum."""
        start_time = time.perf_counter()

        messages = [
            SystemMessage(content=CURRICULUM_GENERATION_PROMPT),
            HumanMessage(content=(
                "Generate the complete hierarchical teaching structure for Indian Polity & Constitution. "
                "Return ONLY the JSON structure with a 'nodes' array."
            )),
        ]

        try:
            result: LLMCurriculumResponse = await self._structured_llm.ainvoke(messages)
            duration = (time.perf_counter() - start_time) * 1000
            logger.info(
                "curriculum_llm_complete subject=%s node_count=%d duration_ms=%.2f",
                subject_code, len(result.nodes), duration,
            )
        except Exception:
            logger.exception("curriculum_llm_failed subject=%s", subject_code)
            raise

        # Convert LLM output to domain objects
        return self._parse_llm_nodes(subject_code, result.nodes)

    def _parse_llm_nodes(
        self, subject_code: str, llm_nodes: list[LLMCurriculumNode],
    ) -> list[CurriculumNode]:
        """Convert LLM Pydantic nodes to domain CurriculumNode objects."""
        level_map = {
            "preparation": CurriculumLevel.PREPARATION,
            "phase": CurriculumLevel.PHASE,
            "module": CurriculumLevel.MODULE,
            "unit": CurriculumLevel.UNIT,
            "chapter": CurriculumLevel.CHAPTER,
            "topic": CurriculumLevel.TOPIC,
            "concept": CurriculumLevel.CONCEPT,
        }

        nodes = []
        for llm_node in llm_nodes:
            level = level_map.get(llm_node.level.lower(), CurriculumLevel.TOPIC)
            nodes.append(CurriculumNode(
                id=llm_node.id,
                parent_id=llm_node.parent_id,
                level=level,
                title=llm_node.title,
                subject_code=subject_code,
                learning_order=llm_node.learning_order,
                prerequisites=tuple(llm_node.prerequisites),
                dependencies=tuple(llm_node.dependencies),
                child_ids=tuple(llm_node.child_nodes),
            ))

        return nodes

    def _save_to_file(self, subject_code: str, nodes: list[CurriculumNode]) -> None:
        """Cache curriculum to a JSON file."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            file_path = DATA_DIR / f"curriculum_{subject_code}.json"
            data = [
                {
                    "id": n.id,
                    "parent_id": n.parent_id,
                    "level": n.level.value,
                    "title": n.title,
                    "subject_code": n.subject_code,
                    "learning_order": n.learning_order,
                    "prerequisites": list(n.prerequisites),
                    "dependencies": list(n.dependencies),
                    "child_ids": list(n.child_ids),
                }
                for n in nodes
            ]
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("curriculum_saved_to_file path=%s node_count=%d", file_path, len(nodes))
        except Exception:
            logger.exception("curriculum_save_failed subject=%s", subject_code)

    def _load_from_file(self, subject_code: str) -> list[CurriculumNode] | None:
        """Load curriculum from JSON file cache."""
        file_path = DATA_DIR / f"curriculum_{subject_code}.json"
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            level_map = {v.value: v for v in CurriculumLevel}
            nodes = []
            for item in data:
                nodes.append(CurriculumNode(
                    id=item["id"],
                    parent_id=item.get("parent_id"),
                    level=level_map.get(item["level"], CurriculumLevel.TOPIC),
                    title=item["title"],
                    subject_code=item.get("subject_code", subject_code),
                    learning_order=item["learning_order"],
                    prerequisites=tuple(item.get("prerequisites", [])),
                    dependencies=tuple(item.get("dependencies", [])),
                    child_ids=tuple(item.get("child_ids", [])),
                ))
            logger.info("curriculum_loaded_from_file path=%s node_count=%d", file_path, len(nodes))
            return nodes
        except Exception:
            logger.exception("curriculum_load_failed path=%s", file_path)
            return None
