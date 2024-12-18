"""
Entrypoint for streamlit, see https://docs.streamlit.io/
"""

import base64
import logging
import os
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import StrEnum
from functools import partial
from pathlib import PosixPath
from typing import cast
from uuid import uuid4

import httpx
from anthropic import RateLimitError
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)

from .loop import (
    PROVIDER_TO_DEFAULT_MODEL_NAME,
    APIProvider,
    sampling_loop,
)
from .tools import ToolResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# configure formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# console handler
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

enable_file_logging = False

# file handler
if enable_file_logging:
    file_handler = logging.FileHandler("public/app.log", mode="a")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

CONFIG_DIR = PosixPath("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"
STREAMLIT_STYLE = """
<style>
    /* Highlight the stop button in red */
    button[kind=header] {
        background-color: rgb(255, 75, 75);
        border: 1px solid rgb(255, 75, 75);
        color: rgb(255, 255, 255);
    }
    button[kind=header]:hover {
        background-color: rgb(255, 51, 51);
    }
     /* Hide the streamlit deploy button */
    .stAppDeployButton {
        visibility: hidden;
    }
</style>
"""

WARNING_TEXT = "⚠️ Security Alert: Never provide access to sensitive accounts or data, as malicious web content can hijack Claude's behavior"
INTERRUPT_TEXT = "(user stopped or interrupted and wrote the following)"
INTERRUPT_TOOL_ERROR = "human stopped or interrupted tool execution"


class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


# Store message state per request id
messages_for_session_id = {}


def setup_state(state):
    state.setdefault("messages", [])
    state.setdefault(
        "api_key", load_from_storage("api_key") or os.getenv("ANTHROPIC_API_KEY", "")
    )
    state.setdefault(
        "provider", os.getenv("API_PROVIDER", "anthropic") or APIProvider.ANTHROPIC
    )
    state.setdefault("provider_radio", state["provider"])
    state.setdefault(
        "model",
        PROVIDER_TO_DEFAULT_MODEL_NAME[cast(APIProvider, state["provider"])]
        if state.get("model") is None
        else state["model"],
    )
    state.setdefault("auth_validated", False)
    state.setdefault("responses", {})
    state.setdefault("tools", {})
    state.setdefault("only_n_most_recent_images", 3)
    state.setdefault("custom_system_prompt", load_from_storage("system_prompt") or "")
    state.setdefault("hide_images", False)
    state.setdefault("in_sampling_loop", False)


async def main(new_message: str):
    session_id = uuid4()
    """Render loop for streamlit"""
    state = {}
    setup_state(state)

    state["messages"].append(
        {
            "role": Sender.USER,
            "content": [
                *maybe_add_interruption_blocks(state),
                BetaTextBlockParam(type="text", text=new_message),
            ],
        }
    )

    with track_sampling_loop(state):
        # run the agent sampling loop with the newest message
        state["messages"] = await sampling_loop(
            system_prompt_suffix=state["custom_system_prompt"],
            model=state["model"],
            provider=state["provider"],
            messages=state["messages"],
            output_callback=partial(_render_message, Sender.BOT, session_id),
            tool_output_callback=partial(
                _tool_output_callback, tool_state=state["tools"]
            ),
            api_response_callback=partial(
                _api_response_callback,
                response_state=state["responses"],
            ),
            api_key=state["api_key"],
            only_n_most_recent_images=state["only_n_most_recent_images"],
        )

    logger.info("NATH - finished loop")

    text_response = state["messages"][-1]["content"][0]["text"]
    if not text_response:
        logger.error("no response")

    logger.info(f"NATH - Final message: {text_response}")
    return text_response


def maybe_add_interruption_blocks(state):
    if not state["in_sampling_loop"]:
        return []
    # If this function is called while we're in the sampling loop, we can assume that the previous sampling loop was interrupted
    # and we should annotate the conversation with additional context for the model and heal any incomplete tool use calls
    result = []
    last_message = state["messages"][-1]
    previous_tool_use_ids = [
        block["id"] for block in last_message["content"] if block["type"] == "tool_use"
    ]
    for tool_use_id in previous_tool_use_ids:
        state["tools"][tool_use_id] = ToolResult(error=INTERRUPT_TOOL_ERROR)
        result.append(
            BetaToolResultBlockParam(
                tool_use_id=tool_use_id,
                type="tool_result",
                content=INTERRUPT_TOOL_ERROR,
                is_error=True,
            )
        )
    result.append(BetaTextBlockParam(type="text", text=INTERRUPT_TEXT))
    return result


@contextmanager
def track_sampling_loop(state):
    state["in_sampling_loop"] = True
    yield
    state["in_sampling_loop"] = False


def validate_auth(provider: APIProvider, api_key: str | None):
    if provider == APIProvider.ANTHROPIC:
        if not api_key:
            return "Enter your Anthropic API key in the sidebar to continue."
    if provider == APIProvider.BEDROCK:
        import boto3

        if not boto3.Session().get_credentials():
            return "You must have AWS credentials set up to use the Bedrock API."
    if provider == APIProvider.VERTEX:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError

        if not os.environ.get("CLOUD_ML_REGION"):
            return "Set the CLOUD_ML_REGION environment variable to use the Vertex API."
        try:
            google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except DefaultCredentialsError:
            return "Your google cloud credentials are not set up correctly."


def load_from_storage(filename: str) -> str | None:
    """Load data from a file in the storage directory."""
    try:
        file_path = CONFIG_DIR / filename
        if file_path.exists():
            data = file_path.read_text().strip()
            if data:
                return data
    except Exception as e:
        logger.error(f"Debug: Error loading {filename}: {e}")
    return None


def save_to_storage(filename: str, data: str) -> None:
    """Save data to a file in the storage directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CONFIG_DIR / filename
        file_path.write_text(data)
        # Ensure only user can read/write the file
        file_path.chmod(0o600)
    except Exception as e:
        logger.error(f"Debug: Error saving {filename}: {e}")


def _api_response_callback(
    request: httpx.Request,
    response: httpx.Response | object | None,
    error: Exception | None,
    response_state: dict[str, tuple[httpx.Request, httpx.Response | object | None]],
):
    """
    Handle an API response by storing it to state and rendering it.
    """
    response_id = datetime.now().isoformat()
    response_state[response_id] = (request, response)
    if error:
        _render_error(error)
    _render_api_response(request, response, response_id)


def _tool_output_callback(
    tool_output: ToolResult, tool_id: str, tool_state: dict[str, ToolResult]
):
    """Handle a tool output by storing it to state and rendering it."""
    tool_state[tool_id] = tool_output
    _render_message(Sender.TOOL, tool_output)


def _render_api_response(
    request: httpx.Request,
    response: httpx.Response | object | None,
    response_id: str,
):
    """Render an API response to a streamlit tab"""
    logger.info(
        f"_render_api_response - request={request} response={response} response_id={response_id}"
    )


def _render_error(error: Exception):
    if isinstance(error, RateLimitError):
        body = "You have been rate limited."
        if retry_after := error.response.headers.get("retry-after"):
            body += f" **Retry after {str(timedelta(seconds=int(retry_after)))} (HH:MM:SS).** See our API [documentation](https://docs.anthropic.com/en/api/rate-limits) for more details."
        body += f"\n\n{error.message}"
    else:
        body = str(error)
        body += "\n\n**Traceback:**"
        lines = "\n".join(traceback.format_exception(error))
        body += f"\n\n```{lines}```"
    save_to_storage(f"error_{datetime.now().timestamp()}.md", body)
    logger.error(f"**{error.__class__.__name__}**\n\n{body}")


def _render_message(
    sender: Sender,
    session_id: string,
    message: str | BetaContentBlockParam | ToolResult,
):
    """Convert input from the user or output from the agent to a streamlit message."""
    # streamlit's hotreloading breaks isinstance checks, so we need to check for class names
    is_tool_result = not isinstance(message, str | dict)
    if not message or (
        is_tool_result
        and not hasattr(message, "error")
        and not hasattr(message, "output")
    ):
        return

    messages_for_session_id[session_id] = message
    if is_tool_result:
        message = cast(ToolResult, message)
        if message.output:
            logger.info(message.output)
        if message.error:
            logger.error(message.error)
        if message.base64_image:
            logger.info(f"screenshot taken by {sender}")
            if enable_file_logging:
                image_data = base64.b64decode(message.base64_image)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                with open(f"public/{timestamp}.png", "wb") as image_file:
                    image_file.write(image_data)
    elif isinstance(message, dict):
        if message["type"] == "text":
            logger.info(message["text"])
        elif message["type"] == "tool_use":
            logger.info(f'Tool Use: {message["name"]}\nInput: {message["input"]}')
        else:
            # only expected return types are text and tool_use
            raise Exception(f'Unexpected response type {message["type"]}')
