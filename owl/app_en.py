# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import os
import sys
import gradio as gr
import subprocess
import threading
import time
from datetime import datetime
import queue
from pathlib import Path
import json
import signal
import dotenv

# Set up log queue
log_queue: queue.Queue[str] = queue.Queue()

# Currently running process
current_process = None
process_lock = threading.Lock()

# Script options
SCRIPTS = {
    "Qwen Mini (Chinese)": "run_qwen_mini_zh.py",
    "Qwen (Chinese)": "run_qwen_zh.py",
    "Mini": "run_mini.py",
    "DeepSeek (Chinese)": "run_deepseek_zh.py",
    "Default": "run.py",
    "GAIA Roleplaying": "run_gaia_roleplaying.py",
    "OpenAI Compatible": "run_openai_compatiable_model.py",
    "Ollama": "run_ollama.py",
}

# Script descriptions
SCRIPT_DESCRIPTIONS = {
    "Qwen Mini (Chinese)": "Uses the Chinese version of Alibaba Cloud's Qwen model, suitable for Chinese Q&A and tasks",
    "Qwen (Chinese)": "Uses Alibaba Cloud's Qwen model, supports various tools and functions",
    "Mini": "Lightweight version, uses OpenAI GPT-4o model",
    "DeepSeek (Chinese)": "Uses DeepSeek model, suitable for non-multimodal tasks",
    "Default": "Default OWL implementation, uses OpenAI GPT-4o model and full set of tools",
    "GAIA Roleplaying": "GAIA benchmark implementation, used to evaluate model capabilities",
    "OpenAI Compatible": "Uses third-party models compatible with OpenAI API, supports custom API endpoints",
    "Ollama": "Uses Ollama API",
}

# Environment variable groups
ENV_GROUPS = {
    "Model API": [
        {
            "name": "OPENAI_API_KEY",
            "label": "OpenAI API Key",
            "type": "password",
            "required": False,
            "help": "OpenAI API key for accessing GPT models. Get it from: https://platform.openai.com/api-keys",
        },
        {
            "name": "OPENAI_API_BASE_URL",
            "label": "OpenAI API Base URL",
            "type": "text",
            "required": False,
            "help": "Base URL for OpenAI API, optional. Set this if using a proxy or custom endpoint.",
        },
        {
            "name": "QWEN_API_KEY",
            "label": "Alibaba Cloud Qwen API Key",
            "type": "password",
            "required": False,
            "help": "Alibaba Cloud Qwen API key for accessing Qwen models. Get it from: https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key",
        },
        {
            "name": "DEEPSEEK_API_KEY",
            "label": "DeepSeek API Key",
            "type": "password",
            "required": False,
            "help": "DeepSeek API key for accessing DeepSeek models. Get it from: https://platform.deepseek.com/api_keys",
        },
    ],
    "Search Tools": [
        {
            "name": "GOOGLE_API_KEY",
            "label": "Google API Key",
            "type": "password",
            "required": False,
            "help": "Google Search API key for web search functionality. Get it from: https://developers.google.com/custom-search/v1/overview",
        },
        {
            "name": "SEARCH_ENGINE_ID",
            "label": "Search Engine ID",
            "type": "text",
            "required": False,
            "help": "Google Custom Search Engine ID, used with Google API key. Get it from: https://developers.google.com/custom-search/v1/overview",
        },
    ],
    "Other Tools": [
        {
            "name": "HF_TOKEN",
            "label": "Hugging Face Token",
            "type": "password",
            "required": False,
            "help": "Hugging Face API token for accessing Hugging Face models and datasets. Get it from: https://huggingface.co/join",
        },
        {
            "name": "CHUNKR_API_KEY",
            "label": "Chunkr API Key",
            "type": "password",
            "required": False,
            "help": "Chunkr API key for document processing functionality. Get it from: https://chunkr.ai/",
        },
        {
            "name": "FIRECRAWL_API_KEY",
            "label": "Firecrawl API Key",
            "type": "password",
            "required": False,
            "help": "Firecrawl API key for web crawling functionality. Get it from: https://www.firecrawl.dev/",
        },
    ],
    "Custom Environment Variables": [],  # User-defined environment variables will be stored here
}


def get_script_info(script_name):
    """Get detailed information about the script"""
    return SCRIPT_DESCRIPTIONS.get(script_name, "No description available")


def load_env_vars():
    """Load environment variables"""
    env_vars = {}
    # Try to load from .env file
    dotenv.load_dotenv()

    # Get all environment variables
    for group in ENV_GROUPS.values():
        for var in group:
            env_vars[var["name"]] = os.environ.get(var["name"], "")

    # Load other environment variables that may exist in the .env file
    if Path(".env").exists():
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        try:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()

                            # Handle quoted values
                            if (value.startswith('"') and value.endswith('"')) or (
                                value.startswith("'") and value.endswith("'")
                            ):
                                value = value[
                                    1:-1
                                ]  # Remove quotes at the beginning and end

                            # Check if it's a known environment variable
                            known_var = False
                            for group in ENV_GROUPS.values():
                                if any(var["name"] == key for var in group):
                                    known_var = True
                                    break

                            # If it's not a known environment variable, add it to the custom environment variables group
                            if not known_var and key not in env_vars:
                                ENV_GROUPS["Custom Environment Variables"].append(
                                    {
                                        "name": key,
                                        "label": key,
                                        "type": "text",
                                        "required": False,
                                        "help": "User-defined environment variable",
                                    }
                                )
                                env_vars[key] = value
                        except Exception as e:
                            print(
                                f"Error parsing environment variable line: {line}, error: {str(e)}"
                            )
        except Exception as e:
            print(f"Error loading .env file: {str(e)}")

    return env_vars


def save_env_vars(env_vars):
    """Save environment variables to .env file"""
    # Read existing .env file content
    env_path = Path(".env")
    existing_content = {}

    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        try:
                            key, value = line.split("=", 1)
                            existing_content[key.strip()] = value.strip()
                        except Exception as e:
                            print(
                                f"Error parsing environment variable line: {line}, error: {str(e)}"
                            )
        except Exception as e:
            print(f"Error reading .env file: {str(e)}")

    # Update environment variables
    for key, value in env_vars.items():
        if value is not None:  # Allow empty string values, but not None
            # Ensure the value is a string
            value = str(value)  # Ensure the value is a string

            # Check if the value is already wrapped in quotes
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                # Already wrapped in quotes, keep as is
                existing_content[key] = value
                # Update environment variable by removing quotes
                os.environ[key] = value[1:-1]
            else:
                # Not wrapped in quotes, add double quotes
                # Wrap the value in double quotes to ensure special characters are handled correctly
                quoted_value = f'"{value}"'
                existing_content[key] = quoted_value
                # Also update the environment variable for the current process (using the unquoted value)
                os.environ[key] = value

    # Write to .env file
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            for key, value in existing_content.items():
                f.write(f"{key}={value}\n")
    except Exception as e:
        print(f"Error writing to .env file: {str(e)}")
        return f"❌ Failed to save environment variables: {str(e)}"

    return "✅ Environment variables saved"


def add_custom_env_var(name, value, var_type):
    """Add custom environment variable"""
    if not name:
        return "❌ Environment variable name cannot be empty", None

    # Check if an environment variable with the same name already exists
    for group in ENV_GROUPS.values():
        if any(var["name"] == name for var in group):
            return f"❌ Environment variable {name} already exists", None

    # Add to custom environment variables group
    ENV_GROUPS["Custom Environment Variables"].append(
        {
            "name": name,
            "label": name,
            "type": var_type,
            "required": False,
            "help": "User-defined environment variable",
        }
    )

    # Save environment variables
    env_vars = {name: value}
    save_env_vars(env_vars)

    # Return success message and updated environment variable group
    return f"✅ Added environment variable {name}", ENV_GROUPS[
        "Custom Environment Variables"
    ]


def update_custom_env_var(name, value, var_type):
    """Update custom environment variable"""
    if not name:
        return "❌ Environment variable name cannot be empty", None

    # Check if the environment variable exists in the custom environment variables group
    found = False
    for i, var in enumerate(ENV_GROUPS["Custom Environment Variables"]):
        if var["name"] == name:
            # Update type
            ENV_GROUPS["Custom Environment Variables"][i]["type"] = var_type
            found = True
            break

    if not found:
        return f"❌ Custom environment variable {name} does not exist", None

    # Save environment variable value
    env_vars = {name: value}
    save_env_vars(env_vars)

    # Return success message and updated environment variable group
    return f"✅ Updated environment variable {name}", ENV_GROUPS[
        "Custom Environment Variables"
    ]


def delete_custom_env_var(name):
    """Delete custom environment variable"""
    if not name:
        return "❌ Environment variable name cannot be empty", None

    # Check if the environment variable exists in the custom environment variables group
    found = False
    for i, var in enumerate(ENV_GROUPS["Custom Environment Variables"]):
        if var["name"] == name:
            # Delete from custom environment variables group
            del ENV_GROUPS["Custom Environment Variables"][i]
            found = True
            break

    if not found:
        return f"❌ Custom environment variable {name} does not exist", None

    # Delete the environment variable from .env file
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(env_path, "w", encoding="utf-8") as f:
                for line in lines:
                    try:
                        # More precisely match environment variable lines
                        line_stripped = line.strip()
                        # Check if it's a comment line or empty line
                        if not line_stripped or line_stripped.startswith("#"):
                            f.write(line)  # Keep comment lines and empty lines
                            continue

                        # Check if it contains an equals sign
                        if "=" not in line_stripped:
                            f.write(line)  # Keep lines without equals sign
                            continue

                        # Extract variable name and check if it matches the variable to be deleted
                        var_name = line_stripped.split("=", 1)[0].strip()
                        if var_name != name:
                            f.write(line)  # Keep variables that don't match
                    except Exception as e:
                        print(
                            f"Error processing .env file line: {line}, error: {str(e)}"
                        )
                        # Keep the original line when an error occurs
                        f.write(line)
        except Exception as e:
            print(f"Error deleting environment variable: {str(e)}")
            return f"❌ Failed to delete environment variable: {str(e)}", None

    # Delete from current process environment variables
    if name in os.environ:
        del os.environ[name]

    # Return success message and updated environment variable group
    return f"✅ Deleted environment variable {name}", ENV_GROUPS[
        "Custom Environment Variables"
    ]


def terminate_process():
    """Terminate the currently running process"""
    global current_process

    with process_lock:
        if current_process is not None and current_process.poll() is None:
            try:
                # On Windows, use taskkill to forcibly terminate the process tree
                if os.name == "nt":
                    # Get process ID
                    pid = current_process.pid
                    # Use taskkill command to terminate the process and its children - avoid using shell=True for better security
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)], check=False
                        )
                    except subprocess.SubprocessError as e:
                        log_queue.put(f"Error terminating process: {str(e)}\n")
                        return f"❌ Error terminating process: {str(e)}"
                else:
                    # On Unix, use SIGTERM and SIGKILL
                    current_process.terminate()
                    try:
                        current_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        current_process.kill()

                # Wait for process to terminate
                try:
                    current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass  # Already tried to force terminate, ignore timeout

                log_queue.put("Process terminated\n")
                return "✅ Process terminated"
            except Exception as e:
                log_queue.put(f"Error terminating process: {str(e)}\n")
                return f"❌ Error terminating process: {str(e)}"
        else:
            return "❌ No process is currently running"


def run_script(script_dropdown, question, progress=gr.Progress()):
    """Run the selected script and return the output"""
    global current_process

    script_name = SCRIPTS.get(script_dropdown)
    if not script_name:
        return "❌ Invalid script selection", "", "", "", None

    if not question.strip():
        return "Please enter a question!", "", "", "", None

    # Clear the log queue
    while not log_queue.empty():
        log_queue.get()

    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{script_name.replace('.py', '')}_{timestamp}.log"

    # Build command
    cmd = [
        sys.executable,
        os.path.join("owl", "script_adapter.py"),
        os.path.join("owl", script_name),
    ]

    # Create a copy of environment variables and add the question
    env = os.environ.copy()
    # Ensure question is a string type
    if not isinstance(question, str):
        question = str(question)
    # Preserve newlines, but ensure it's a valid string
    env["OWL_QUESTION"] = question

    # Start the process
    with process_lock:
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            encoding="utf-8",
        )

    # Create thread to read output
    def read_output():
        try:
            # Use a unique timestamp to ensure log filename is not duplicated
            timestamp_unique = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            unique_log_file = (
                log_dir / f"{script_name.replace('.py', '')}_{timestamp_unique}.log"
            )

            # Use this unique filename to write logs
            with open(unique_log_file, "w", encoding="utf-8") as f:
                # Update global log file path
                nonlocal log_file
                log_file = unique_log_file

                for line in iter(current_process.stdout.readline, ""):
                    if line:
                        # Write to log file
                        f.write(line)
                        f.flush()
                        # Add to queue
                        log_queue.put(line)
        except Exception as e:
            log_queue.put(f"Error reading output: {str(e)}\n")

    # Start the reading thread
    threading.Thread(target=read_output, daemon=True).start()

    # Collect logs
    logs = []
    progress(0, desc="Running...")

    # Wait for process to complete or timeout
    start_time = time.time()
    timeout = 1800  # 30 minutes timeout

    while current_process.poll() is None:
        # Check if timeout
        if time.time() - start_time > timeout:
            with process_lock:
                if current_process.poll() is None:
                    if os.name == "nt":
                        current_process.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        current_process.terminate()
                    log_queue.put("Execution timeout, process terminated\n")
            break

        # Get logs from queue
        while not log_queue.empty():
            log = log_queue.get()
            logs.append(log)

        # Update progress
        elapsed = time.time() - start_time
        progress(min(elapsed / 300, 0.99), desc="Running...")

        # Short sleep to reduce CPU usage
        time.sleep(0.1)

        # Update log display once per second
        yield (
            status_message(current_process),
            extract_answer(logs),
            "".join(logs),
            str(log_file),
            None,
        )

    # Get remaining logs
    while not log_queue.empty():
        logs.append(log_queue.get())

    # Extract chat history (if any)
    chat_history = extract_chat_history(logs)

    # Return final status and logs
    return (
        status_message(current_process),
        extract_answer(logs),
        "".join(logs),
        str(log_file),
        chat_history,
    )


def status_message(process):
    """Return status message based on process status"""
    if process.poll() is None:
        return "⏳ Running..."
    elif process.returncode == 0:
        return "✅ Execution successful"
    else:
        return f"❌ Execution failed (return code: {process.returncode})"


def extract_answer(logs):
    """Extract answer from logs"""
    answer = ""
    for log in logs:
        if "Answer:" in log:
            answer = log.split("Answer:", 1)[1].strip()
            break
    return answer


def extract_chat_history(logs):
    """Try to extract chat history from logs"""
    try:
        chat_json_str = ""
        capture_json = False

        for log in logs:
            if "chat_history" in log:
                # Start capturing JSON
                start_idx = log.find("[")
                if start_idx != -1:
                    capture_json = True
                    chat_json_str = log[start_idx:]
            elif capture_json:
                # Continue capturing JSON until finding the matching closing bracket
                chat_json_str += log
                if "]" in log:
                    # Found closing bracket, try to parse JSON
                    end_idx = chat_json_str.rfind("]") + 1
                    if end_idx > 0:
                        try:
                            # Clean up possible extra text
                            json_str = chat_json_str[:end_idx].strip()
                            chat_data = json.loads(json_str)

                            # Format for use with Gradio chat component
                            formatted_chat = []
                            for msg in chat_data:
                                if "role" in msg and "content" in msg:
                                    role = (
                                        "User" if msg["role"] == "user" else "Assistant"
                                    )
                                    formatted_chat.append([role, msg["content"]])
                            return formatted_chat
                        except json.JSONDecodeError:
                            # If parsing fails, continue capturing
                            pass
                        except Exception:
                            # Other errors, stop capturing
                            capture_json = False
    except Exception:
        pass
    return None


def create_ui():
    """Create Gradio interface"""
    # Load environment variables
    env_vars = load_env_vars()

    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue")) as app:
        gr.Markdown(
            """
            # 🦉 OWL Intelligent Assistant Platform
            
            Select a model and enter your question, the system will run the corresponding script and display the results.
            """
        )

        with gr.Tabs():
            with gr.TabItem("Run Mode"):
                with gr.Row():
                    with gr.Column(scale=1):
                        # Ensure default value is a key that exists in SCRIPTS
                        default_script = list(SCRIPTS.keys())[0] if SCRIPTS else None
                        script_dropdown = gr.Dropdown(
                            choices=list(SCRIPTS.keys()),
                            value=default_script,
                            label="Select Mode",
                        )

                        script_info = gr.Textbox(
                            value=get_script_info(default_script)
                            if default_script
                            else "",
                            label="Model Description",
                            interactive=False,
                        )

                        script_dropdown.change(
                            fn=lambda x: get_script_info(x),
                            inputs=script_dropdown,
                            outputs=script_info,
                        )

                        question_input = gr.Textbox(
                            lines=8,
                            placeholder="Please enter your question...",
                            label="Question",
                            elem_id="question_input",
                            show_copy_button=True,
                        )

                        gr.Markdown(
                            """
                            > **Note**: Your question will replace the default question in the script. The system will automatically handle the replacement, ensuring your question is used correctly.
                            > Multi-line input is supported, line breaks will be preserved.
                            """
                        )

                        with gr.Row():
                            run_button = gr.Button("Run", variant="primary")
                            stop_button = gr.Button("Stop", variant="stop")

                    with gr.Column(scale=2):
                        with gr.Tabs():
                            with gr.TabItem("Results"):
                                status_output = gr.Textbox(label="Status")
                                answer_output = gr.Textbox(label="Answer", lines=10)
                                log_file_output = gr.Textbox(label="Log File Path")

                            with gr.TabItem("Run Logs"):
                                log_output = gr.Textbox(label="Complete Logs", lines=25)

                            with gr.TabItem("Chat History"):
                                chat_output = gr.Chatbot(label="Conversation History")

                # Example questions
                examples = [
                    [
                        "Qwen Mini (Chinese)",
                        "Browse Amazon and find a product that is attractive to programmers. Please provide the product name and price.",
                    ],
                    [
                        "DeepSeek (Chinese)",
                        "Please analyze the latest statistics of the CAMEL-AI project on GitHub. Find out the number of stars, number of contributors, and recent activity of the project. Then, create a simple Excel spreadsheet to display this data and generate a bar chart to visualize these metrics. Finally, summarize the popularity and development trends of the CAMEL project.",
                    ],
                    [
                        "Default",
                        "Navigate to Amazon.com and identify one product that is attractive to coders. Please provide me with the product name and price. No need to verify your answer.",
                    ],
                ]

                gr.Examples(examples=examples, inputs=[script_dropdown, question_input])

            with gr.TabItem("Environment Variable Configuration"):
                env_inputs = {}
                save_status = gr.Textbox(label="Save Status", interactive=False)

                # Add custom environment variables section
                with gr.Accordion("Add Custom Environment Variables", open=True):
                    with gr.Row():
                        new_var_name = gr.Textbox(
                            label="Environment Variable Name",
                            placeholder="Example: MY_CUSTOM_API_KEY",
                        )
                        new_var_value = gr.Textbox(
                            label="Environment Variable Value",
                            placeholder="Enter value",
                        )
                        new_var_type = gr.Dropdown(
                            choices=["text", "password"], value="text", label="Type"
                        )

                    add_var_button = gr.Button(
                        "Add Environment Variable", variant="primary"
                    )
                    add_var_status = gr.Textbox(label="Add Status", interactive=False)

                    # Custom environment variables list
                    custom_vars_list = gr.JSON(
                        value=ENV_GROUPS["Custom Environment Variables"],
                        label="Added Custom Environment Variables",
                        visible=len(ENV_GROUPS["Custom Environment Variables"]) > 0,
                    )

                # Update and delete custom environment variables section
                with gr.Accordion(
                    "Update or Delete Custom Environment Variables",
                    open=True,
                    visible=len(ENV_GROUPS["Custom Environment Variables"]) > 0,
                ) as update_delete_accordion:
                    with gr.Row():
                        # Create dropdown menu to display all custom environment variables
                        custom_var_dropdown = gr.Dropdown(
                            choices=[
                                var["name"]
                                for var in ENV_GROUPS["Custom Environment Variables"]
                            ],
                            label="Select Environment Variable",
                            interactive=True,
                        )
                        update_var_value = gr.Textbox(
                            label="New Environment Variable Value",
                            placeholder="Enter new value",
                        )
                        update_var_type = gr.Dropdown(
                            choices=["text", "password"], value="text", label="Type"
                        )

                    with gr.Row():
                        update_var_button = gr.Button(
                            "Update Environment Variable", variant="primary"
                        )
                        delete_var_button = gr.Button(
                            "Delete Environment Variable", variant="stop"
                        )

                    update_var_status = gr.Textbox(
                        label="Operation Status", interactive=False
                    )

                # Add environment variable button click event
                add_var_button.click(
                    fn=add_custom_env_var,
                    inputs=[new_var_name, new_var_value, new_var_type],
                    outputs=[add_var_status, custom_vars_list],
                ).then(
                    fn=lambda vars: {"visible": len(vars) > 0},
                    inputs=[custom_vars_list],
                    outputs=[update_delete_accordion],
                )

                # Update environment variable button click event
                update_var_button.click(
                    fn=update_custom_env_var,
                    inputs=[custom_var_dropdown, update_var_value, update_var_type],
                    outputs=[update_var_status, custom_vars_list],
                )

                # Delete environment variable button click event
                delete_var_button.click(
                    fn=delete_custom_env_var,
                    inputs=[custom_var_dropdown],
                    outputs=[update_var_status, custom_vars_list],
                ).then(
                    fn=lambda vars: {"visible": len(vars) > 0},
                    inputs=[custom_vars_list],
                    outputs=[update_delete_accordion],
                )

                # When custom environment variables list is updated, update dropdown menu options
                custom_vars_list.change(
                    fn=lambda vars: {
                        "choices": [var["name"] for var in vars],
                        "value": None,
                    },
                    inputs=[custom_vars_list],
                    outputs=[custom_var_dropdown],
                )

                # Existing environment variable configuration
                for group_name, vars in ENV_GROUPS.items():
                    if (
                        group_name != "Custom Environment Variables" or len(vars) > 0
                    ):  # Only show non-empty custom environment variable groups
                        with gr.Accordion(
                            group_name,
                            open=(group_name != "Custom Environment Variables"),
                        ):
                            for var in vars:
                                # Add help information
                                gr.Markdown(f"**{var['help']}**")

                                if var["type"] == "password":
                                    env_inputs[var["name"]] = gr.Textbox(
                                        value=env_vars.get(var["name"], ""),
                                        label=var["label"],
                                        placeholder=f"Please enter {var['label']}",
                                        type="password",
                                    )
                                else:
                                    env_inputs[var["name"]] = gr.Textbox(
                                        value=env_vars.get(var["name"], ""),
                                        label=var["label"],
                                        placeholder=f"Please enter {var['label']}",
                                    )

                save_button = gr.Button("Save Environment Variables", variant="primary")

                # Save environment variables
                save_inputs = [
                    env_inputs[var_name]
                    for group in ENV_GROUPS.values()
                    for var in group
                    for var_name in [var["name"]]
                    if var_name in env_inputs
                ]
                save_button.click(
                    fn=lambda *values: save_env_vars(
                        dict(
                            zip(
                                [
                                    var["name"]
                                    for group in ENV_GROUPS.values()
                                    for var in group
                                    if var["name"] in env_inputs
                                ],
                                values,
                            )
                        )
                    ),
                    inputs=save_inputs,
                    outputs=save_status,
                )

        # Run script
        run_button.click(
            fn=run_script,
            inputs=[script_dropdown, question_input],
            outputs=[
                status_output,
                answer_output,
                log_output,
                log_file_output,
                chat_output,
            ],
            show_progress=True,
        )

        # Terminate execution
        stop_button.click(fn=terminate_process, inputs=[], outputs=[status_output])

        # Add footer
        gr.Markdown(
            """
            ### 📝 Instructions
            
            - Select a model and enter your question
            - Click the "Run" button to start execution
            - To stop execution, click the "Stop" button
            - View execution status and answers in the "Results" tab
            - View complete logs in the "Run Logs" tab
            - View conversation history in the "Chat History" tab (if available)
            - Configure API keys and other environment variables in the "Environment Variable Configuration" tab
            - You can add custom environment variables to meet special requirements
            
            ### ⚠️ Notes
            
            - Running some models may require API keys, please make sure you have set the corresponding environment variables in the "Environment Variable Configuration" tab
            - Some scripts may take a long time to run, please be patient
            - If execution exceeds 30 minutes, the process will automatically terminate
            - Your question will replace the default question in the script, ensure the question is compatible with the selected model
            """
        )

    return app


if __name__ == "__main__":
    # Create and launch the application
    app = create_ui()
    app.queue().launch(share=True)
