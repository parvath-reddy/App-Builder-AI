import os
from dotenv import load_dotenv
import logging

from langchain_groq.chat_models import ChatGroq
from langgraph.constants import END
from langgraph.graph import StateGraph

from agent.prompts import planner_prompt, architect_prompt, coder_system_prompt
from agent.states import Plan, TaskPlan, CoderState
from agent.tools import write_file, read_file, get_current_directory, list_files

# Load environment variables
_ = load_dotenv()

# Configure standard logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatGroq(model="openai/gpt-oss-120b")


def planner_agent(state: dict) -> dict:
    """Converts user prompt into a structured Plan."""
    user_prompt = state["user_prompt"]
    resp = llm.with_structured_output(Plan).invoke(
        planner_prompt(user_prompt)
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")
    logger.info(f"Planner generated plan: {resp}")
    return {"plan": resp}


def architect_agent(state: dict) -> dict:
    """Creates TaskPlan from Plan."""
    plan: Plan = state["plan"]
    resp = llm.with_structured_output(TaskPlan).invoke(
        architect_prompt(plan=plan.model_dump_json())
    )
    if resp is None:
        raise ValueError("Architect did not return a valid response.")

    resp.plan = plan
    logger.info(f"Architect generated task plan: {resp.model_dump_json()}")
    return {"task_plan": resp}


def coder_agent(state: dict) -> dict:
    """Direct code generation agent without using create_react_agent."""
    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    
    # Read existing file content
    try:
        existing_content = read_file.invoke({"path": current_task.filepath})
    except Exception as e:
        existing_content = ""
        logger.warning(f"Could not read file {current_task.filepath}: {e}")

    # Create the prompt for code generation
    system_prompt = coder_system_prompt()
    
    # Build comprehensive context from all existing files
    all_files_context = ""
    try:
        project_root = get_current_directory.invoke({})
        existing_files = list_files.invoke({"directory": "."})
        if existing_files and existing_files != "No files found.":
            all_files_context = f"\n\nExisting project files:\n{existing_files}\n"
    except Exception as e:
        logger.warning(f"Could not list files: {e}")
    
    user_prompt = f"""
Task: {current_task.task_description}

File to create/modify: {current_task.filepath}

Current content of {current_task.filepath}:
{existing_content if existing_content else "[File does not exist yet - create it from scratch]"}
{all_files_context}

Instructions:
1. Generate the COMPLETE file content for {current_task.filepath}
2. If the file already exists, integrate the new requirements with existing code
3. Ensure all imports, functions, and dependencies are properly defined
4. Make sure the code is production-ready and follows best practices
5. Return ONLY the file content, no explanations or markdown

Generate the complete file content now:
"""

    try:
        # Use the LLM directly to generate code
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        # Extract the generated content
        generated_content = response.content.strip()
        
        # Remove markdown code blocks if present
        if generated_content.startswith("```"):
            lines = generated_content.split("\n")
            # Remove first line (```language) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            generated_content = "\n".join(lines)
        
        # Write the file
        write_result = write_file.invoke({
            "path": current_task.filepath,
            "content": generated_content
        })
        
        logger.info(f"Coder agent completed step {coder_state.current_step_idx}: {write_result}")
        
    except Exception as e:
        logger.error(f"Error in coder agent for {current_task.filepath}: {e}")
        # Write a placeholder file with error info
        try:
            placeholder_content = f"""
# TODO: Implementation needed for {current_task.filepath}
# Task: {current_task.task_description}
# Error occurred during generation: {str(e)}

{existing_content}
"""
            write_file.invoke({
                "path": current_task.filepath,
                "content": placeholder_content
            })
        except Exception as write_error:
            logger.error(f"Could not write placeholder file: {write_error}")

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}


# Build the agent graph
graph = StateGraph(dict)
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get("status") == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)

graph.set_entry_point("planner")
agent = graph.compile()


# Quick test when running standalone
if __name__ == "__main__":
    result = agent.invoke(
        {"user_prompt": "Build a colourful modern todo app in html css and js"},
        {"recursion_limit": 100}
    )
    print("Final State:", result)