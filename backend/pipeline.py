"""LangGraph Pipeline — wires the 4 AI agents together.

Flow:
  Agent 1 (Ingestion) → Agent 2 (Workflow) → Agent 3 (Script) + Agent 4 (Quiz) in parallel
  Then optionally → Agent 5 (Video Generator)
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from agents import ingestion, workflow, script_generator, quiz_generator, video_generator
from models.schemas import (
    UnifiedContent, WorkflowGraph, VideoScriptManifest,
    Assessment, TrainingPackage
)


# --- Pipeline State (flows between nodes) ---
class PipelineState(TypedDict):
    # Inputs
    prd_text: str
    code_text: str
    figma_description: str
    workflow_name: str
    screenshots_dir: str
    generate_video: bool
    # Intermediate outputs
    unified_content: Optional[UnifiedContent]
    workflow_graph: Optional[WorkflowGraph]
    # Final outputs
    manifest: Optional[VideoScriptManifest]
    assessment: Optional[Assessment]
    video_path: Optional[str]


# --- Node functions (each calls one agent) ---

def node_ingestion(state: PipelineState) -> dict:
    """Agent 1: Ingest PRD + code + figma → UnifiedContent."""
    print("🔄 Agent 1: Ingesting artifacts...")
    result = ingestion.run(
        prd_text=state["prd_text"],
        code_text=state["code_text"],
        figma_description=state.get("figma_description", "")
    )
    print(f"✅ Agent 1: Found {len(result.screens)} screens, {len(result.navigation)} nav rules")
    return {"unified_content": result}


def node_workflow(state: PipelineState) -> dict:
    """Agent 2: Extract ordered workflow from unified content."""
    print("🔄 Agent 2: Extracting workflow...")
    result = workflow.run(state["unified_content"])
    print(f"✅ Agent 2: Extracted {len(result.steps)} steps, {len(result.branches)} branches")
    return {"workflow_graph": result}


def node_script(state: PipelineState) -> dict:
    """Agent 3: Generate narration script + overlay data."""
    print("🔄 Agent 3: Generating training script...")
    result = script_generator.run(
        workflow=state["workflow_graph"],
        workflow_name=state.get("workflow_name", "Training Flow")
    )
    print(f"✅ Agent 3: Generated script for {len(result.steps)} steps")
    return {"manifest": result}


def node_quiz(state: PipelineState) -> dict:
    """Agent 4: Generate quiz questions."""
    print("🔄 Agent 4: Generating quiz...")
    result = quiz_generator.run(state["workflow_graph"])
    print(f"✅ Agent 4: Generated {len(result.questions)} questions")
    return {"assessment": result}


def node_video(state: PipelineState) -> dict:
    """Agent 5: Generate MP4 video (optional)."""
    if not state.get("generate_video", False):
        print("⏭️  Agent 5: Video generation skipped")
        return {"video_path": None}
    print("🔄 Agent 5: Generating video...")
    path = video_generator.run(
        manifest=state["manifest"],
        screenshots_dir=state.get("screenshots_dir", "screenshots")
    )
    print(f"✅ Agent 5: Video saved to {path}")
    return {"video_path": path}


# --- Build the graph ---

def build_pipeline() -> StateGraph:
    """Build the LangGraph pipeline."""
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("ingestion", node_ingestion)
    graph.add_node("workflow", node_workflow)
    graph.add_node("script", node_script)
    graph.add_node("quiz", node_quiz)
    graph.add_node("video", node_video)

    # Wire edges: ingestion → workflow → (script + quiz in parallel) → video
    graph.set_entry_point("ingestion")
    graph.add_edge("ingestion", "workflow")
    graph.add_edge("workflow", "script")
    graph.add_edge("workflow", "quiz")
    graph.add_edge("script", "video")
    graph.add_edge("quiz", "video")
    graph.add_edge("video", END)

    return graph.compile()


def run_pipeline(
    prd_text: str,
    code_text: str,
    figma_description: str = "",
    workflow_name: str = "Training Flow",
    screenshots_dir: str = "screenshots",
    generate_video: bool = False,
) -> TrainingPackage:
    """Run the full pipeline end-to-end."""
    pipeline = build_pipeline()

    result = pipeline.invoke({
        "prd_text": prd_text,
        "code_text": code_text,
        "figma_description": figma_description,
        "workflow_name": workflow_name,
        "screenshots_dir": screenshots_dir,
        "generate_video": generate_video,
        "unified_content": None,
        "workflow_graph": None,
        "manifest": None,
        "assessment": None,
        "video_path": None,
    })

    return TrainingPackage(
        manifest=result["manifest"],
        assessment=result["assessment"],
        video_path=result.get("video_path"),
    )
