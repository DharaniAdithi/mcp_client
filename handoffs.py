
import uuid
from typing import Callable, Literal
from typing_extensions import NotRequired

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool, ToolRuntime

from config import get_llm

# ─────────────────────────────────────────────
# Step 1: Custom state with workflow step tracking
# ─────────────────────────────────────────────

SupportStep = Literal["warranty_collector", "issue_classifier", "resolution_specialist"]

class SupportState(AgentState):
    """State for customer support workflow."""
    current_step:    NotRequired[SupportStep]
    warranty_status: NotRequired[Literal["in_warranty", "out_of_warranty"]]
    issue_type:      NotRequired[Literal["hardware", "software"]]


# ─────────────────────────────────────────────
# Step 2: Tools that update state and trigger transitions
# ─────────────────────────────────────────────

@tool
def record_warranty_status(
    status: Literal["in_warranty", "out_of_warranty"],
    runtime: ToolRuntime[None, SupportState],
) -> Command:
    """Record the customer's warranty status and transition to issue classification."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"✅ Warranty status recorded: {status}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "warranty_status": status,
            "current_step": "issue_classifier",   # ← STATE TRANSITION
        }
    )


@tool
def record_issue_type(
    issue_type: Literal["hardware", "software"],
    runtime: ToolRuntime[None, SupportState],
) -> Command:
    """Record the type of issue and transition to resolution specialist."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"✅ Issue type recorded: {issue_type}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "issue_type": issue_type,
            "current_step": "resolution_specialist",  # ← STATE TRANSITION
        }
    )


@tool
def provide_solution(solution: str) -> str:
    """Provide a solution to the customer's issue."""
    return f"✅ Solution provided: {solution}"


@tool
def escalate_to_human(reason: str) -> str:
    """Escalate the case to a human support specialist."""
    return f"🔔 Escalating to human support. Reason: {reason}"


# ─────────────────────────────────────────────
# Step 3: Step configurations (prompt + tools per step)
# ─────────────────────────────────────────────

WARRANTY_COLLECTOR_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Warranty verification

Steps:
1. Greet the customer warmly.
2. Ask if their device is under warranty.
3. Use record_warranty_status to record the answer and advance the workflow.

Be conversational and friendly."""

ISSUE_CLASSIFIER_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Issue classification
CUSTOMER INFO: Warranty status = {warranty_status}

Steps:
1. Ask the customer to describe their issue.
2. Classify as hardware (physical damage) or software (crashes, performance).
3. Use record_issue_type to record and advance the workflow."""

RESOLUTION_SPECIALIST_PROMPT = """You are a customer support agent helping with device issues.

CURRENT STAGE: Resolution
CUSTOMER INFO: Warranty = {warranty_status} | Issue type = {issue_type}

Steps:
- SOFTWARE issue → provide troubleshooting steps via provide_solution.
- HARDWARE issue + IN WARRANTY → explain warranty repair via provide_solution.
- HARDWARE issue + OUT OF WARRANTY → escalate_to_human for paid repair options."""

STEP_CONFIG = {
    "warranty_collector": {
        "prompt": WARRANTY_COLLECTOR_PROMPT,
        "tools": [record_warranty_status],
        "requires": [],
    },
    "issue_classifier": {
        "prompt": ISSUE_CLASSIFIER_PROMPT,
        "tools": [record_issue_type],
        "requires": ["warranty_status"],
    },
    "resolution_specialist": {
        "prompt": RESOLUTION_SPECIALIST_PROMPT,
        "tools": [provide_solution, escalate_to_human],
        "requires": ["warranty_status", "issue_type"],
    },
}


# ─────────────────────────────────────────────
# Step 4: Middleware — dynamically applies step config
# ─────────────────────────────────────────────

@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Read current_step from state and apply matching prompt + tools."""
    current_step = request.state.get("current_step", "warranty_collector")
    step_cfg = STEP_CONFIG[current_step]

    # Validate prerequisites
    for key in step_cfg["requires"]:
        if request.state.get(key) is None:
            raise ValueError(f"'{key}' must be set before reaching '{current_step}'")

    # Format prompt with current state values
    system_prompt = step_cfg["prompt"].format(**request.state)

    # Override prompt and restrict tools to current step
    request = request.override(
        system_prompt=system_prompt,
        tools=step_cfg["tools"],
    )
    return handler(request)


# ─────────────────────────────────────────────
# Step 5: Create the agent
# ─────────────────────────────────────────────

llm = get_llm(max_tokens=600)

agent = create_agent(
    llm,
    tools=[record_warranty_status, record_issue_type, provide_solution, escalate_to_human],
    state_schema=SupportState,
    middleware=[apply_step_config],
    checkpointer=InMemorySaver(),
)


# ─────────────────────────────────────────────
# Step 6: Run the multi-turn conversation
# ─────────────────────────────────────────────

if __name__ == "__main__":
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    turns = [
        "Hi, my phone screen is cracked",        # → warranty_collector greets, asks warranty
        "Yes, it's still under warranty",         # → records warranty, moves to issue_classifier
        "The screen cracked after I dropped it",  # → records hardware, moves to resolution_specialist
        "What should I do next?",                 # → provides warranty repair solution
    ]

    for i, user_msg in enumerate(turns, 1):
        print(f"\n{'='*60}")
        print(f"TURN {i}: {user_msg}")
        print("=" * 60)
        result = agent.invoke(
            {"messages": [HumanMessage(user_msg)]},
            config
        )
        # Print only new messages from this turn
        for msg in result["messages"][-3:]:
            msg.pretty_print()
        step = result.get("current_step", "warranty_collector")
        print(f"\n→ Active step after turn {i}: {step}")