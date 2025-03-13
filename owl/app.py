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
import re
import dotenv

# 设置日志队列
log_queue: queue.Queue[str] = queue.Queue()

# 当前运行的进程
current_process = None
process_lock = threading.Lock()

# 脚本选项
SCRIPTS = {
    # 常规模型
    "Qwen Mini (中文)": "run_qwen_mini_zh.py",
    "Qwen （中文）": "run_qwen_zh.py",
    "Mini": "run_mini.py",
    "DeepSeek （中文）": "run_deepseek_zh.py",
    "Default": "run.py",
    "GAIA Roleplaying": "run_gaia_roleplaying.py",
    "OpenAI Compatible": "run_openai_compatiable_model.py",
    "Ollama": "run_ollama.py",
    
    # Gemini 2.0系列模型
    "Gemini 2.0-思考模式": "run_gemini_thinking.py",
    "Gemini 2.0-Flash-001": "run_gemini_thinking.py",
    "Gemini 2.0-Pro-Exp": "run_gemini_thinking.py",
    "Gemini 2.0-Flash-Lite": "run_gemini_thinking.py",
    
    # Gemini 1.5系列模型
    "Gemini 1.5-Pro": "run_gemini_thinking.py",
    "Gemini 1.5-Flash-002": "run_gemini_thinking.py",
    "Gemini 1.5-Flash-Exp": "run_gemini_thinking.py",
}

# 脚本描述
SCRIPT_DESCRIPTIONS = {
    # 常规模型
    "Qwen Mini (中文)": "使用阿里云Qwen模型的中文版本，适合中文问答和任务",
    "Qwen （中文）": "使用阿里云Qwen模型，支持多种工具和功能",
    "Mini": "轻量级版本，使用OpenAI GPT-4o模型",
    "DeepSeek （中文）": "使用DeepSeek模型，适合非多模态任务",
    "Default": "默认OWL实现，使用OpenAI GPT-4o模型和全套工具",
    "GAIA Roleplaying": "GAIA基准测试实现，用于评估模型能力",
    "OpenAI Compatible": "使用兼容OpenAI API的第三方模型，支持自定义API端点",
    "Ollama": "使用Ollama API",
    
    # Gemini 2.0系列模型
    "Gemini 2.0-思考模式": "Gemini 2.0 Flash Thinking (gemini-2.0-flash-thinking-exp-01-21)，谷歌增强推理实验模型。\n    侧重于展示模型的思考过程，提高性能和可解释性。",
    "Gemini 2.0-Flash-001": "Gemini 2.0 Flash 基础模型 (gemini-2.0-flash-001)，提供高速响应和良好的通用能力。",
    "Gemini 2.0-Pro-Exp": "Gemini 2.0 Pro 实验版本 (gemini-2.0-pro-exp-02-05)，具有较强的推理能力和知识广度。",
    "Gemini 2.0-Flash-Lite": "Gemini 2.0 Flash Lite预览版 (gemini-2.0-flash-lite-preview-02-05)，轻量级模型，适合移动和低延迟场景。",
    
    # Gemini 1.5系列模型
    "Gemini 1.5-Pro": "Gemini 1.5 Pro (gemini-1.5-pro)，通用大语言模型，平衡了性能和效率。",
    "Gemini 1.5-Flash-002": "Gemini 1.5 Flash (gemini-1.5-flash-002)，速度优化版本，适合需要快速响应的场景。",
    "Gemini 1.5-Flash-Exp": "Gemini 1.5 Flash 实验版 (gemini-1.5-flash-exp-0827)，提供实验性能力的快速版本。",
}

# Gemini模型类型映射表
GEMINI_MODEL_TYPES = {
    "Gemini 2.0-思考模式": "gemini-2.0-flash-thinking-exp-01-21",
    "Gemini 2.0-Flash-001": "gemini-2.0-flash-001",
    "Gemini 2.0-Pro-Exp": "gemini-2.0-pro-exp-02-05",
    "Gemini 2.0-Flash-Lite": "gemini-2.0-flash-lite-preview-02-05",
    "Gemini 1.5-Pro": "gemini-1.5-pro",
    "Gemini 1.5-Flash-002": "gemini-1.5-flash-002",
    "Gemini 1.5-Flash-Exp": "gemini-1.5-flash-exp-0827",
}

# 环境变量分组
ENV_GROUPS = {
    "模型API": [
        {
            "name": "OPENAI_API_KEY",
            "label": "OpenAI API密钥",
            "type": "password",
            "required": False,
            "help": "OpenAI API密钥，用于访问GPT模型。获取方式：https://platform.openai.com/api-keys",
        },
        {
            "name": "OPENAI_API_BASE_URL",
            "label": "OpenAI API基础URL",
            "type": "text",
            "required": False,
            "help": "OpenAI API的基础URL，可选。如果使用代理或自定义端点，请设置此项。",
        },
        {
            "name": "QWEN_API_KEY",
            "label": "阿里云Qwen API密钥",
            "type": "password",
            "required": False,
            "help": "阿里云Qwen API密钥，用于访问Qwen模型。获取方式：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key",
        },
        {
            "name": "DEEPSEEK_API_KEY",
            "label": "DeepSeek API密钥",
            "type": "password",
            "required": False,
            "help": "DeepSeek API密钥，用于访问DeepSeek模型。获取方式：https://platform.deepseek.com/api_keys",
        },
        {
            "name": "GEMINI_API_KEY",
            "label": "Gemini API 密钥",
            "type": "password",
            "required": False,
            "help": "Gemini API 密钥，用于访问 Gemini 模型。",
        },
        {
            "name": "GEMINI_API_BASE_URL",
            "label": "Gemini API 基础URL",
            "type": "text",
            "required": False,
            "help": "Gemini API的基础URL，如果使用代理或自定义端点，请设置此项。",
        },
    ],
    "搜索工具": [
        {
            "name": "GOOGLE_API_KEY",
            "label": "Google API密钥",
            "type": "password",
            "required": False,
            "help": "Google搜索API密钥，用于网络搜索功能。获取方式：https://developers.google.com/custom-search/v1/overview",
        },
        {
            "name": "SEARCH_ENGINE_ID",
            "label": "搜索引擎ID",
            "type": "text",
            "required": False,
            "help": "Google自定义搜索引擎ID，与Google API密钥配合使用。获取方式：https://developers.google.com/custom-search/v1/overview",
        },
    ],
    "其他工具": [
        {
            "name": "HF_TOKEN",
            "label": "Hugging Face令牌",
            "type": "password",
            "required": False,
            "help": "Hugging Face API令牌，用于访问Hugging Face模型和数据集。获取方式：https://huggingface.co/join",
        },
        {
            "name": "CHUNKR_API_KEY",
            "label": "Chunkr API密钥",
            "type": "password",
            "required": False,
            "help": "Chunkr API密钥，用于文档处理功能。获取方式：https://chunkr.ai/",
        },
        {
            "name": "FIRECRAWL_API_KEY",
            "label": "Firecrawl API密钥",
            "type": "password",
            "required": False,
            "help": "Firecrawl API密钥，用于网页爬取功能。获取方式：https://www.firecrawl.dev/",
        },
    ],
    "自定义环境变量": [],  # 用户自定义的环境变量将存储在这里
}


def get_script_info(script_name):
    """获取脚本的详细信息"""
    return SCRIPT_DESCRIPTIONS.get(script_name, "无描述信息")


def load_env_vars():
    """加载环境变量"""
    env_vars = {}
    # 尝试从.env文件加载
    dotenv.load_dotenv()

    # 获取所有环境变量
    for group in ENV_GROUPS.values():
        for var in group:
            env_vars[var["name"]] = os.environ.get(var["name"], "")

    # 加载.env文件中可能存在的其他环境变量
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

                            # 处理引号包裹的值
                            if (value.startswith('"') and value.endswith('"')) or (
                                value.startswith("'") and value.endswith("'")
                            ):
                                value = value[1:-1]  # 移除首尾的引号

                            # 检查是否是已知的环境变量
                            known_var = False
                            for group in ENV_GROUPS.values():
                                if any(var["name"] == key for var in group):
                                    known_var = True
                                    break

                            # 如果不是已知的环境变量，添加到自定义环境变量组
                            if not known_var and key not in env_vars:
                                ENV_GROUPS["自定义环境变量"].append(
                                    {
                                        "name": key,
                                        "label": key,
                                        "type": "text",
                                        "required": False,
                                        "help": "用户自定义环境变量",
                                    }
                                )
                                env_vars[key] = value
                        except Exception as e:
                            print(f"解析环境变量行时出错: {line}, 错误: {str(e)}")
        except Exception as e:
            print(f"加载.env文件时出错: {str(e)}")

    return env_vars


def save_env_vars(env_vars):
    """保存环境变量到.env文件"""
    # 读取现有的.env文件内容
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
                            print(f"解析环境变量行时出错: {line}, 错误: {str(e)}")
        except Exception as e:
            print(f"读取.env文件时出错: {str(e)}")

    # 更新环境变量
    for key, value in env_vars.items():
        if value is not None:  # 允许空字符串值，但不允许None
            # 确保值是字符串形式
            value = str(value)  # 确保值是字符串

            # 检查值是否已经被引号包裹
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                # 已经被引号包裹，保持原样
                existing_content[key] = value
                # 更新环境变量时移除引号
                os.environ[key] = value[1:-1]
            else:
                # 没有被引号包裹，添加双引号
                # 用双引号包裹值，确保特殊字符被正确处理
                quoted_value = f'"{value}"'
                existing_content[key] = quoted_value
                # 同时更新当前进程的环境变量（使用未引用的值）
                os.environ[key] = value

    # 写入.env文件
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            for key, value in existing_content.items():
                f.write(f"{key}={value}\n")
    except Exception as e:
        print(f"写入.env文件时出错: {str(e)}")
        return f"❌ 保存环境变量失败: {str(e)}"

    return "✅ 环境变量已保存"


def add_custom_env_var(name, value, var_type):
    """添加自定义环境变量"""
    if not name:
        return "❌ 环境变量名不能为空", None

    # 检查是否已存在同名环境变量
    for group in ENV_GROUPS.values():
        if any(var["name"] == name for var in group):
            return f"❌ 环境变量 {name} 已存在", None

    # 添加到自定义环境变量组
    ENV_GROUPS["自定义环境变量"].append(
        {
            "name": name,
            "label": name,
            "type": var_type,
            "required": False,
            "help": "用户自定义环境变量",
        }
    )

    # 保存环境变量
    env_vars = {name: value}
    save_env_vars(env_vars)

    # 返回成功消息和更新后的环境变量组
    return f"✅ 已添加环境变量 {name}", ENV_GROUPS["自定义环境变量"]


def update_custom_env_var(name, value, var_type):
    """更改自定义环境变量"""
    if not name:
        return "❌ 环境变量名不能为空", None

    # 检查环境变量是否存在于自定义环境变量组中
    found = False
    for i, var in enumerate(ENV_GROUPS["自定义环境变量"]):
        if var["name"] == name:
            # 更新类型
            ENV_GROUPS["自定义环境变量"][i]["type"] = var_type
            found = True
            break

    if not found:
        return f"❌ 自定义环境变量 {name} 不存在", None

    # 保存环境变量值
    env_vars = {name: value}
    save_env_vars(env_vars)

    # 返回成功消息和更新后的环境变量组
    return f"✅ 已更新环境变量 {name}", ENV_GROUPS["自定义环境变量"]


def delete_custom_env_var(name):
    """删除自定义环境变量"""
    if not name:
        return "❌ 环境变量名不能为空", None

    # 检查环境变量是否存在于自定义环境变量组中
    found = False
    for i, var in enumerate(ENV_GROUPS["自定义环境变量"]):
        if var["name"] == name:
            # 从自定义环境变量组中删除
            del ENV_GROUPS["自定义环境变量"][i]
            found = True
            break

    if not found:
        return f"❌ 自定义环境变量 {name} 不存在", None

    # 从.env文件中删除该环境变量
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(env_path, "w", encoding="utf-8") as f:
                for line in lines:
                    try:
                        # 更精确地匹配环境变量行
                        line_stripped = line.strip()
                        # 检查是否为注释行或空行
                        if not line_stripped or line_stripped.startswith("#"):
                            f.write(line)  # 保留注释行和空行
                            continue

                        # 检查是否包含等号
                        if "=" not in line_stripped:
                            f.write(line)  # 保留不包含等号的行
                            continue

                        # 提取变量名并检查是否与要删除的变量匹配
                        var_name = line_stripped.split("=", 1)[0].strip()
                        if var_name != name:
                            f.write(line)  # 保留不匹配的变量
                    except Exception as e:
                        print(f"处理.env文件行时出错: {line}, 错误: {str(e)}")
                        # 出错时保留原行
                        f.write(line)
        except Exception as e:
            print(f"删除环境变量时出错: {str(e)}")
            return f"❌ 删除环境变量失败: {str(e)}", None

    # 从当前进程的环境变量中删除
    if name in os.environ:
        del os.environ[name]

    # 返回成功消息和更新后的环境变量组
    return f"✅ 已删除环境变量 {name}", ENV_GROUPS["自定义环境变量"]


def terminate_process():
    """终止当前运行的进程"""
    global current_process

    with process_lock:
        if current_process is not None and current_process.poll() is None:
            try:
                # 在Windows上使用taskkill强制终止进程树
                if os.name == "nt":
                    # 获取进程ID
                    pid = current_process.pid
                    # 使用taskkill命令终止进程及其子进程 - 避免使用shell=True以提高安全性
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)], check=False
                        )
                    except subprocess.SubprocessError as e:
                        log_queue.put(f"终止进程时出错: {str(e)}\n")
                        return f"❌ 终止进程时出错: {str(e)}"
                else:
                    # 在Unix上使用SIGTERM和SIGKILL
                    current_process.terminate()
                    try:
                        current_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        current_process.kill()

                # 等待进程终止
                try:
                    current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass  # 已经尝试强制终止，忽略超时

                log_queue.put("进程已终止\n")
                return "✅ 进程已终止"
            except Exception as e:
                log_queue.put(f"终止进程时出错: {str(e)}\n")
                return f"❌ 终止进程时出错: {str(e)}"
        else:
            return "❌ 没有正在运行的进程"


def run_script(script_dropdown, question, progress=gr.Progress()):
    """运行选定的脚本并返回输出"""
    global current_process

    script_name = SCRIPTS.get(script_dropdown)
    if not script_name:
        return "❌ 无效的脚本选择", "", "", "", None, None, None

    if not question.strip():
        return "请输入问题！", "", "", "", None, None, None

    # 清空日志队列
    while not log_queue.empty():
        log_queue.get()

    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 确保results文件夹存在
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    # 创建带时间戳的日志文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{script_name.replace('.py', '')}_{timestamp}.log"

    # 构建命令
    cmd = [
        sys.executable,
        os.path.join("owl", "script_adapter.py"),
        os.path.join("owl", script_name),
    ]

    # 创建环境变量副本并添加问题
    env = os.environ.copy()
    # 确保问题是字符串类型
    if not isinstance(question, str):
        question = str(question)
    # 保留换行符，但确保是有效的字符串
    env["OWL_QUESTION"] = question
    
    # 如果使用Gemini模型，添加模型类型环境变量
    if script_dropdown in GEMINI_MODEL_TYPES:
        env["GEMINI_MODEL_TYPE"] = GEMINI_MODEL_TYPES[script_dropdown]

    # 启动进程
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

    # 创建线程来读取输出
    def read_output():
        try:
            # 使用唯一的时间戳确保日志文件名不重复
            timestamp_unique = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            unique_log_file = (
                log_dir / f"{script_name.replace('.py', '')}_{timestamp_unique}.log"
            )

            # 使用这个唯一的文件名写入日志
            with open(unique_log_file, "w", encoding="utf-8") as f:
                # 更新全局日志文件路径
                nonlocal log_file
                log_file = unique_log_file

                for line in iter(current_process.stdout.readline, ""):
                    if line:
                        # 写入日志文件
                        f.write(line)
                        f.flush()
                        # 添加到队列
                        log_queue.put(line)
        except Exception as e:
            log_queue.put(f"读取输出时出错: {str(e)}\n")

    # 启动读取线程
    threading.Thread(target=read_output, daemon=True).start()

    # 收集日志
    logs = []
    progress(0, desc="正在运行...")

    # 等待进程完成或超时
    start_time = time.time()
    timeout = 1800  # 30分钟超时

    while current_process.poll() is None:
        # 检查是否超时
        if time.time() - start_time > timeout:
            with process_lock:
                if current_process.poll() is None:
                    if os.name == "nt":
                        current_process.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        current_process.terminate()
                    log_queue.put("执行超时，已终止进程\n")
            break

        # 从队列获取日志
        while not log_queue.empty():
            log = log_queue.get()
            logs.append(log)

        # 更新进度
        elapsed = time.time() - start_time
        progress(min(elapsed / 300, 0.99), desc="正在运行...")

        # 短暂休眠以减少CPU使用
        time.sleep(0.1)

        # 每秒更新一次日志显示
        yield (
            status_message(current_process),
            extract_answer(logs),
            "".join(logs),
            str(log_file),
            None,
            None,
            None,
        )

    # 获取剩余日志
    while not log_queue.empty():
        logs.append(log_queue.get())

    # 提取聊天历史（如果有）
    chat_history = extract_chat_history(logs)
    
    # 提取答案文本
    answer_text = extract_answer(logs)
    
    # 保存结果到Markdown文件
    answer_file = None
    chat_history_file = None
    
    if answer_text and status_message(current_process) == "✅ 执行成功":
        try:
            # 保存答案到Markdown文件
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = script_dropdown.replace(" ", "_").replace("（", "").replace("）", "")
            
            # 创建答案文件名
            answer_filename = f"{model_name}_{timestamp_str}.md"
            answer_file = results_dir / answer_filename
            
            # 写入答案文件
            with open(answer_file, "w", encoding="utf-8") as f:
                f.write(f"# {script_dropdown} 回答结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## 问题\n\n{question.strip()}\n\n")
                f.write(f"## 回答\n\n{answer_text}\n")
            
            # 如果有聊天历史，也保存到单独的文件
            if chat_history:
                # 创建聊天历史文件名
                chat_filename = f"chat_history_{model_name}_{timestamp_str}.md"
                chat_history_file = results_dir / chat_filename
                
                # 写入聊天历史文件
                with open(chat_history_file, "w", encoding="utf-8") as f:
                    f.write(f"# {script_dropdown} 聊天历史 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    for msg in chat_history:
                        role, content = msg
                        f.write(f"## {role}\n\n{content}\n\n")
        except Exception as e:
            log_queue.put(f"保存结果文件时出错: {str(e)}\n")
    
    # 返回最终状态和日志
    return (
        status_message(current_process),
        answer_text,
        "".join(logs),
        str(log_file),
        chat_history,
        answer_file,
        chat_history_file,
    )


def status_message(process):
    """根据进程状态返回状态消息"""
    if process.poll() is None:
        return "⏳ 正在运行..."
    elif process.returncode == 0:
        return "✅ 执行成功"
    else:
        return f"❌ 执行失败 (返回码: {process.returncode})"


def extract_answer(logs):
    """从日志中提取答案"""
    answer = ""
    for log in logs:
        if "Answer:" in log:
            answer = log.split("Answer:", 1)[1].strip()
            break
    return answer


def extract_chat_history(logs):
    """尝试从日志中提取聊天历史"""
    chat_history = []
    
    try:
        # 合并所有日志为一个字符串
        logs_text = "".join(logs)
        
        # 尝试查找聊天历史的JSON输出
        chat_regex = r"Chat History:(.*?)(?=\n\n|$)"
        chat_match = re.search(chat_regex, logs_text, re.DOTALL)
        
        if chat_match:
            chat_json_str = chat_match.group(1).strip()
            try:
                # 尝试解析JSON
                chat_data = json.loads(chat_json_str)
                if isinstance(chat_data, list):
                    for item in chat_data:
                        # 检查必要的键是否存在
                        if isinstance(item, dict) and "role" in item and "content" in item:
                            chat_history.append((item["role"], item["content"]))
            except json.JSONDecodeError:
                # 如果无法解析JSON，尝试用正则表达式提取
                role_content_pattern = r"Role: (.*?)\nContent: (.*?)(?=\nRole:|$)"
                matches = re.findall(role_content_pattern, chat_json_str, re.DOTALL)
                for role, content in matches:
                    chat_history.append((role.strip(), content.strip()))
    except Exception as e:
        print(f"提取聊天历史时出错: {str(e)}")
    
    return chat_history


def create_ui():
    """创建Gradio用户界面"""
    
    # 加载环境变量并保存到.env文件
    env_vars = load_env_vars()
    
    with gr.Blocks(title="OWL - Open WebAgent Language", css="""
        .gradio-container {
            max-width: 1200px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
        .env-group {
            border: 1px solid #cccccc;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
            background-color: #f9f9f9;
        }
        .env-group h4 {
            margin-top: 0;
            margin-bottom: 10px;
            border-bottom: 1px solid #eaeaea;
            padding-bottom: 8px;
        }
        .custom-accordion .label-wrap {
            background-color: #f0f7ff !important;
        }
        .result-box {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
        }
        .status-success {
            color: green;
            font-weight: bold;
        }
        .status-running {
            color: orange;
            font-weight: bold;
        }
        .status-error {
            color: red;
            font-weight: bold;
        }
        """) as demo:
        
        # 使用Markdown显示标题
        gr.Markdown(
            """
            # 🦉 OWL - Open WebAgent Language
            ### 开源的网络代理语言框架
            """
        )
        
        with gr.Tabs() as tabs:
            # 主要交互标签页
            with gr.TabItem("会话"):
                with gr.Row():
                    with gr.Column(scale=2):
                        script_dropdown = gr.Dropdown(
                            list(SCRIPTS.keys()),
                            label="选择模型",
                            value=list(SCRIPTS.keys())[0] if SCRIPTS else None,
                            info="选择一个语言模型来处理您的请求",
                        )
                        
                        script_info = gr.Markdown(
                            get_script_info(list(SCRIPTS.keys())[0]) if SCRIPTS else "",
                            elem_id="script_info",
                        )
                        
                        # 更新脚本信息
                        def update_script_info(script_dropdown):
                            return get_script_info(script_dropdown)
                        
                        script_dropdown.change(
                            fn=update_script_info,
                            inputs=script_dropdown,
                            outputs=script_info,
                        )
                        
                    with gr.Column(scale=5):
                        question_input = gr.Textbox(
                            lines=4,
                            placeholder="在这里输入您的问题或指令...",
                            label="问题",
                        )
                        submit_btn = gr.Button("提交", variant="primary")
                        cancel_btn = gr.Button("终止运行", variant="stop")
                        
                        # 当终止按钮点击时
                        cancel_btn.click(fn=terminate_process, inputs=None, outputs=gr.Markdown())

                with gr.Tabs() as result_tabs:
                    with gr.TabItem("结果"):
                        status_output = gr.Markdown()
                        answer_output = gr.Markdown()
                        results_file_output = gr.File(label="下载结果", interactive=False, visible=False)
                    
                    with gr.TabItem("聊天历史"):
                        chat_output = gr.JSON(label="聊天交互记录")
                        chat_history_file_output = gr.File(label="下载聊天历史", interactive=False, visible=False)
                    
                    with gr.TabItem("日志"):
                        log_output = gr.Code(label="日志输出")
                        log_file_output = gr.Textbox(label="日志文件路径", interactive=False)
            
            # 环境变量配置标签页
            with gr.TabItem("配置"):
                # 在这里创建环境变量配置界面
                env_inputs = {}
                env_types = {}
                
                # 使用折叠面板放置环境变量组
                for group_name, vars_list in ENV_GROUPS.items():
                    if vars_list or group_name == "自定义环境变量":  # 始终显示自定义环境变量组
                        with gr.Accordion(group_name, open=(group_name == "模型API"), elem_classes="custom-accordion"):
                            with gr.Column():
                                for var in vars_list:
                                    with gr.Row():
                                        if var["type"] == "password":
                                            env_inputs[var["name"]] = gr.Textbox(
                                                label=var["label"],
                                                placeholder=f"请输入{var['label']}",
                                                type="password",
                                                value=env_vars.get(var["name"], ""),
                                                info=var["help"],
                                            )
                                        else:
                                            env_inputs[var["name"]] = gr.Textbox(
                                                label=var["label"],
                                                placeholder=f"请输入{var['label']}",
                                                value=env_vars.get(var["name"], ""),
                                                info=var["help"],
                                            )
                                        env_types[var["name"]] = var["type"]
                                
                                # 为自定义环境变量组添加添加/删除按钮
                                if group_name == "自定义环境变量":
                                    # 添加环境变量UI
                                    with gr.Row():
                                        custom_env_name = gr.Textbox(
                                            label="环境变量名",
                                            placeholder="输入新的环境变量名 (例如: MY_CUSTOM_KEY)",
                                        )
                                        custom_env_value = gr.Textbox(
                                            label="环境变量值",
                                            placeholder="输入环境变量值",
                                        )
                                        custom_env_type = gr.Radio(
                                            choices=["text", "password"],
                                            label="类型",
                                            value="text",
                                        )
                                    
                                    with gr.Row():
                                        add_env_btn = gr.Button("添加环境变量", variant="primary")
                                        custom_env_result = gr.Markdown()
                                    
                                    # 删除环境变量UI
                                    if ENV_GROUPS["自定义环境变量"]:
                                        with gr.Row():
                                            delete_env_dropdown = gr.Dropdown(
                                                [var["name"] for var in ENV_GROUPS["自定义环境变量"]],
                                                label="选择要删除的环境变量",
                                            )
                                            delete_env_btn = gr.Button("删除环境变量", variant="stop")
                                        
                                        with gr.Row():
                                            delete_env_result = gr.Markdown()
                                
                save_btn = gr.Button("保存环境变量", variant="primary")
                save_result = gr.Markdown()
                
                # 添加自定义环境变量
                def add_env_var(name, value, var_type):
                    result_message, updated_vars = add_custom_env_var(name, value, var_type)
                    return result_message
                
                add_env_btn.click(
                    fn=add_env_var,
                    inputs=[custom_env_name, custom_env_value, custom_env_type],
                    outputs=custom_env_result,
                )
                
                # 删除自定义环境变量
                if "delete_env_dropdown" in locals():
                    def delete_env_var(name):
                        result_message, updated_vars = delete_custom_env_var(name)
                        return result_message
                    
                    delete_env_btn.click(
                        fn=delete_env_var,
                        inputs=delete_env_dropdown,
                        outputs=delete_env_result,
                    )
                
                # 保存环境变量
                def save_env_variables():
                    updated_env_vars = {
                        name: inputs.value
                        for name, inputs in env_inputs.items()
                        if inputs.value != ""
                    }
                    return save_env_vars(updated_env_vars)
                
                save_btn.click(fn=save_env_variables, inputs=None, outputs=save_result)
        
        # 注册提交按钮点击事件
        submit_btn.click(
            fn=run_script,
            inputs=[script_dropdown, question_input],
            outputs=[
                status_output,
                answer_output,
                log_output,
                log_file_output,
                chat_output,
                results_file_output,
                chat_history_file_output,
            ],
        )
    
    return demo


# 当直接运行此脚本时，启动Gradio界面
if __name__ == "__main__":
    app = create_ui()
    app.launch(share=False, inbrowser=True)
