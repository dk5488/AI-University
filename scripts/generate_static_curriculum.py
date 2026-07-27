"""Generate a deterministic UPSC Polity curriculum cache.

This is a fallback for local development when Gemini quota prevents LLM
curriculum generation. It writes the same JSON shape consumed by the app.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "curriculum_polity.json"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "node"


def add_node(
    nodes: list[dict[str, Any]],
    *,
    node_id: str,
    parent_id: str | None,
    level: str,
    title: str,
    prerequisites: list[str] | None = None,
) -> dict[str, Any]:
    node = {
        "id": node_id,
        "parent_id": parent_id,
        "level": level,
        "title": title,
        "subject_code": "polity",
        "learning_order": len(nodes) + 1,
        "prerequisites": prerequisites or [],
        "dependencies": [],
        "child_ids": [],
    }
    nodes.append(node)
    return node


def link_children(nodes: list[dict[str, Any]]) -> None:
    by_id = {node["id"]: node for node in nodes}
    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id and parent_id in by_id:
            by_id[parent_id]["child_ids"].append(node["id"])

    leaves = [node for node in nodes if not node["child_ids"]]
    for current, next_node in zip(leaves, leaves[1:]):
        current["dependencies"] = [next_node["id"]]
        next_node["prerequisites"] = list(dict.fromkeys(
            [*next_node["prerequisites"], current["id"]]
        ))


CURRICULUM = [
    (
        "Foundation",
        [
            (
                "Constitutional Evolution and Making",
                [
                    (
                        "Constitutional History and Historical Acts",
                        [
                            (
                                "Company Rule to Crown Rule",
                                [
                                    "Regulating Act 1773",
                                    "Pitt's India Act 1784",
                                    "Charter Acts 1813 1833 1853",
                                    "Government of India Act 1858",
                                ],
                            ),
                            (
                                "Representative Institutions Before 1947",
                                [
                                    "Indian Councils Acts 1861 1892",
                                    "Morley-Minto Reforms 1909",
                                    "Montagu-Chelmsford Reforms 1919",
                                    "Government of India Act 1935",
                                    "Indian Independence Act 1947",
                                ],
                            ),
                        ],
                    ),
                    (
                        "Making of the Constitution",
                        [
                            (
                                "Constituent Assembly",
                                [
                                    "Cabinet Mission Plan",
                                    "Composition and Working",
                                    "Committees of Constituent Assembly",
                                    "Adoption Enactment and Enforcement",
                                ],
                            ),
                            (
                                "Sources and Design",
                                [
                                    "Borrowed Features of Constitution",
                                    "Objectives Resolution",
                                    "Constitutional Morality",
                                    "Salient Features of Indian Constitution",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Constitutional Philosophy and Basic Framework",
                [
                    (
                        "Identity of the Constitution",
                        [
                            (
                                "Preamble and Constitutional Values",
                                ["Preamble", "Sovereign Socialist Secular Democratic Republic"],
                            ),
                            (
                                "State and Nation",
                                ["Union and its Territory", "Citizenship", "Official Language"],
                            ),
                        ],
                    ),
                    (
                        "Constitutional Architecture",
                        [
                            (
                                "Structure and Classification",
                                ["Federal Unitary and Parliamentary Features", "Schedules and Parts"],
                            ),
                            (
                                "Constitutional Change",
                                ["Amendment Procedure", "Basic Structure Doctrine"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    (
        "Core Rights Duties and Directive Principles",
        [
            (
                "Fundamental Rights",
                [
                    (
                        "Rights Framework",
                        [
                            ("Equality and Liberty", ["Article 14", "Article 19", "Article 21"]),
                            (
                                "Protection and Remedies",
                                ["Articles 20 to 22", "Article 32 and Writs", "Rights of Accused"],
                            ),
                        ],
                    ),
                    (
                        "Social Rights and Limits",
                        [
                            (
                                "Social Justice Rights",
                                ["Articles 23 and 24", "Articles 25 to 28", "Articles 29 and 30"],
                            ),
                            (
                                "Rights Limitations",
                                ["Reasonable Restrictions", "Emergency Impact on Rights"],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "DPSP and Fundamental Duties",
                [
                    (
                        "Directive Principles",
                        [
                            (
                                "DPSP Classification",
                                ["Socialistic Principles", "Gandhian Principles", "Liberal Principles"],
                            ),
                            (
                                "DPSP Rights Relationship",
                                ["FR versus DPSP", "Minerva Mills Doctrine"],
                            ),
                        ],
                    ),
                    (
                        "Duties and Civic Constitutionalism",
                        [
                            (
                                "Fundamental Duties",
                                ["Swaran Singh Committee", "Article 51A", "Enforcement of Duties"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    (
        "Union Institutions",
        [
            (
                "Union Executive",
                [
                    (
                        "Constitutional Executive",
                        [
                            (
                                "President and Vice President",
                                ["Election of President", "Powers of President", "Vice President"],
                            ),
                            (
                                "Emergency and Discretion",
                                ["Ordinance Power", "Pardoning Power", "President's Discretion"],
                            ),
                        ],
                    ),
                    (
                        "Political Executive",
                        [
                            (
                                "Prime Minister and Cabinet",
                                ["Prime Minister", "Council of Ministers", "Cabinet Committees"],
                            ),
                            (
                                "Executive Law Officers",
                                ["Attorney General", "Solicitor General", "Cabinet Secretariat"],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Parliament",
                [
                    (
                        "Parliamentary Structure",
                        [
                            (
                                "Houses of Parliament",
                                ["Lok Sabha", "Rajya Sabha", "Presiding Officers"],
                            ),
                            (
                                "Membership and Sessions",
                                ["Qualifications and Disqualifications", "Sessions", "Anti-Defection Law"],
                            ),
                        ],
                    ),
                    (
                        "Parliamentary Functioning",
                        [
                            (
                                "Legislative Procedure",
                                ["Ordinary Bill", "Money Bill", "Constitution Amendment Bill"],
                            ),
                            (
                                "Financial Control",
                                ["Budget", "Demand for Grants", "Public Accounts Committee"],
                            ),
                            (
                                "Accountability Devices",
                                ["Question Hour", "Motions", "Parliamentary Committees"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    (
        "Judiciary and Legal Constitutionalism",
        [
            (
                "Judicial System",
                [
                    (
                        "Supreme Court and High Courts",
                        [
                            (
                                "Supreme Court",
                                ["Jurisdiction", "Judicial Review", "Advisory Jurisdiction"],
                            ),
                            (
                                "High Courts",
                                ["High Court Jurisdiction", "Writ Jurisdiction", "Subordinate Judiciary"],
                            ),
                        ],
                    ),
                    (
                        "Judicial Independence",
                        [
                            (
                                "Appointments and Tenure",
                                ["Collegium System", "NJAC Case", "Removal of Judges"],
                            ),
                            (
                                "Judicial Behaviour",
                                ["Judicial Activism", "Judicial Restraint", "Public Interest Litigation"],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Doctrines Important Judgments and Landmark Cases",
                [
                    (
                        "Core Doctrines",
                        [
                            (
                                "Constitutional Doctrines",
                                ["Basic Structure", "Due Process", "Separation of Powers"],
                            ),
                            (
                                "Rights Jurisprudence",
                                [
                                    "Maneka Gandhi Case",
                                    "Kesavananda Bharati Case",
                                    "Puttaswamy Case",
                                    "Important Judgments",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    (
        "State Government Federalism and Emergencies",
        [
            (
                "State Government",
                [
                    (
                        "State Executive",
                        [
                            (
                                "Governor and Chief Minister",
                                ["Governor", "Governor's Discretion", "Chief Minister"],
                            ),
                            (
                                "State Council of Ministers",
                                ["State Cabinet", "Advocate General", "State Secretariat"],
                            ),
                        ],
                    ),
                    (
                        "State Legislature",
                        [
                            (
                                "Legislative Structure",
                                ["Vidhan Sabha", "Vidhan Parishad", "State Legislative Procedure"],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Federal Relations",
                [
                    (
                        "Centre-State Relations",
                        [
                            (
                                "Distribution of Powers",
                                ["Legislative Relations", "Administrative Relations", "Financial Relations"],
                            ),
                            (
                                "Federal Institutions",
                                ["Inter-State Council", "Zonal Councils", "GST Council"],
                            ),
                        ],
                    ),
                    (
                        "Emergency Provisions",
                        [
                            (
                                "Types of Emergency",
                                ["National Emergency", "President's Rule", "Financial Emergency"],
                            ),
                            (
                                "Federal Impact",
                                ["Article 356", "SR Bommai Case", "Emergency Safeguards"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    (
        "Local Governance Bodies and Special Provisions",
        [
            (
                "Local Government",
                [
                    (
                        "Rural Local Bodies",
                        [
                            (
                                "Panchayati Raj",
                                ["73rd Amendment", "Gram Sabha", "Eleventh Schedule"],
                            ),
                            (
                                "Tribal Local Governance",
                                ["PESA Act", "Fifth Schedule Areas", "Sixth Schedule Areas"],
                            ),
                        ],
                    ),
                    (
                        "Urban Local Bodies",
                        [
                            (
                                "Municipal Governance",
                                ["74th Amendment", "Municipalities", "Twelfth Schedule"],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Constitutional and Statutory Bodies",
                [
                    (
                        "Constitutional Bodies",
                        [
                            (
                                "Accountability and Elections",
                                ["Election Commission", "CAG", "Finance Commission"],
                            ),
                            (
                                "Service and Social Justice Bodies",
                                ["UPSC", "SPSC", "NCSC NCST NCBC"],
                            ),
                        ],
                    ),
                    (
                        "Statutory and Regulatory Bodies",
                        [
                            (
                                "Governance Watchdogs",
                                [
                                    "CVC",
                                    "CIC",
                                    "NHRC",
                                    "Lokpal and Lokayukta",
                                    "Regulatory Bodies",
                                    "Non-Constitutional Bodies",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Special and Transitional Provisions",
                [
                    (
                        "Territorial Language and Scheduled Areas Provisions",
                        [
                            (
                                "Special Provisions",
                                [
                                    "Union Territories",
                                    "Special Provisions for States",
                                    "Scheduled Areas",
                                    "Official Language",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    (
        "Governance Current Affairs and UPSC Integration",
        [
            (
                "Governance Concepts",
                [
                    (
                        "Good Governance",
                        [
                            (
                                "Accountability and Transparency",
                                ["RTI", "Citizen Charter", "Social Audit"],
                            ),
                            (
                                "Administrative Ethics Linkages",
                                ["Civil Services", "Pressure Groups", "NGOs and SHGs"],
                            ),
                        ],
                    ),
                    (
                        "Digital and Welfare Governance",
                        [
                            (
                                "Service Delivery",
                                ["E-Governance", "DBT", "Grievance Redressal"],
                            ),
                        ],
                    ),
                ],
            ),
            (
                "Exam Integration",
                [
                    (
                        "Prelims Integration",
                        [
                            (
                                "Static Recall and Elimination",
                                [
                                    "Constitutional Articles Mapping",
                                    "Constitutional Schedules Mapping",
                                    "Important Amendments",
                                    "Bodies Mapping",
                                ],
                            ),
                        ],
                    ),
                    (
                        "Mains Integration",
                        [
                            (
                                "Analytical Answer Writing",
                                [
                                    "Constitutional Values",
                                    "Institutional Reforms",
                                    "Current Affairs Linkage",
                                    "Contemporary Constitutional Developments",
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
]


def generate() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    prep = add_node(
        nodes,
        node_id="polity-preparation",
        parent_id=None,
        level="preparation",
        title="Indian Polity and Constitution for UPSC",
    )

    previous_topic_id: str | None = None
    for phase_index, (phase_title, modules) in enumerate(CURRICULUM, start=1):
        phase = add_node(
            nodes,
            node_id=f"phase-{phase_index}-{slugify(phase_title)}",
            parent_id=prep["id"],
            level="phase",
            title=phase_title,
        )
        for module_index, (module_title, units) in enumerate(modules, start=1):
            module = add_node(
                nodes,
                node_id=f"module-{phase_index}-{module_index}-{slugify(module_title)}",
                parent_id=phase["id"],
                level="module",
                title=module_title,
            )
            for unit_index, (unit_title, chapters) in enumerate(units, start=1):
                unit = add_node(
                    nodes,
                    node_id=f"unit-{phase_index}-{module_index}-{unit_index}-{slugify(unit_title)}",
                    parent_id=module["id"],
                    level="unit",
                    title=unit_title,
                )
                for chapter_index, (chapter_title, topics) in enumerate(chapters, start=1):
                    chapter = add_node(
                        nodes,
                        node_id=(
                            f"chapter-{phase_index}-{module_index}-{unit_index}-"
                            f"{chapter_index}-{slugify(chapter_title)}"
                        ),
                        parent_id=unit["id"],
                        level="chapter",
                        title=chapter_title,
                    )
                    for topic_index, topic_title in enumerate(topics, start=1):
                        topic = add_node(
                            nodes,
                            node_id=(
                                f"topic-{phase_index}-{module_index}-{unit_index}-"
                                f"{chapter_index}-{topic_index}-{slugify(topic_title)}"
                            ),
                            parent_id=chapter["id"],
                            level="topic",
                            title=topic_title,
                            prerequisites=[previous_topic_id] if previous_topic_id else [],
                        )
                        previous_topic_id = topic["id"]
                        for concept_index, concept_title in enumerate(
                            (
                                "Core meaning and constitutional location",
                                "UPSC-relevant provisions and keywords",
                                "Application, exceptions, and recall hooks",
                            ),
                            start=1,
                        ):
                            add_node(
                                nodes,
                                node_id=(
                                    f"concept-{phase_index}-{module_index}-{unit_index}-"
                                    f"{chapter_index}-{topic_index}-{concept_index}-"
                                    f"{slugify(topic_title)}-{slugify(concept_title)}"
                                ),
                                parent_id=topic["id"],
                                level="concept",
                                title=f"{topic_title}: {concept_title}",
                            )

    link_children(nodes)
    return nodes


def main() -> None:
    nodes = generate()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(nodes, indent=2), encoding="utf-8")
    print(f"Generated {len(nodes)} curriculum nodes at {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
