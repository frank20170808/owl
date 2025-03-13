#!/usr/bin/env python
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
import json
import requests
import dotenv
from typing import Dict, List, Any, Optional

# 加载环境变量
dotenv.load_dotenv()

# 检查必需的环境变量
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("错误: 未设置GEMINI_API_KEY环境变量")
    sys.exit(1)

# 获取可选的API基础URL
GEMINI_API_BASE_URL = os.environ.get("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

# 获取模型类型（从环境变量中，如果未设置则使用默认值）
GEMINI_MODEL_TYPE = os.environ.get("GEMINI_MODEL_TYPE", "gemini-1.5-flash-002")

def run_gemini_model(question: str) -> Dict[str, Any]:
    """
    使用Gemini API运行模型
    
    Args:
        question: 用户提问
        
    Returns:
        包含模型响应的字典
    """
    # 构建API URL
    url = f"{GEMINI_API_BASE_URL}/models/{GEMINI_MODEL_TYPE}:generateContent?key={GEMINI_API_KEY}"
    
    # 构建请求
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": question
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 8192,
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    }
    
    # 思考模式特殊设置
    if "thinking" in GEMINI_MODEL_TYPE:
        payload["generationConfig"]["candidate_count"] = 1
        # 启用思考模式的特殊设置
        payload["generationConfig"]["response_mime_type"] = "application/json"
        payload["generationConfig"]["response_schema"] = {
            "type": "object",
            "properties": {
                "thinking": {
                    "type": "string",
                    "description": "详细的推理过程"
                },
                "answer": {
                    "type": "string",
                    "description": "基于推理得出的最终答案"
                }
            },
            "required": ["thinking", "answer"]
        }
    
    # 发送请求
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # 如果请求失败，抛出异常
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求错误: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
        return {"error": str(e)}

def extract_message_content(response: Dict[str, Any]) -> str:
    """
    从API响应中提取消息内容
    
    Args:
        response: API响应字典
        
    Returns:
        消息内容字符串
    """
    try:
        # 检查是否有错误
        if "error" in response:
            return f"错误: {response['error']}"
        
        # 提取内容
        if "candidates" in response and response["candidates"]:
            candidate = response["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if parts and "text" in parts[0]:
                    # 对于思考模式，解析JSON
                    text = parts[0]["text"]
                    if "thinking" in GEMINI_MODEL_TYPE:
                        try:
                            # 尝试解析JSON输出
                            data = json.loads(text)
                            if "thinking" in data and "answer" in data:
                                return f"思考过程:\n\n{data['thinking']}\n\n最终答案:\n\n{data['answer']}"
                        except json.JSONDecodeError:
                            # 如果不能解析为JSON，返回原始文本
                            pass
                    return text
        
        # 如果找不到内容
        return "无法提取回答内容"
    except Exception as e:
        return f"提取内容时出错: {str(e)}"

def format_chat_history(messages: List[Dict[str, str]]) -> str:
    """
    格式化聊天历史记录
    
    Args:
        messages: 消息列表
        
    Returns:
        格式化的聊天历史
    """
    history = []
    for msg in messages:
        history.append(f"Role: {msg['role']}\nContent: {msg['content']}")
    return "\n\n".join(history)

def main():
    """主函数"""
    # 从环境变量获取问题
    question = os.environ.get("OWL_QUESTION", "")
    if not question:
        print("错误: 未提供问题")
        sys.exit(1)
    
    print(f"问题: {question}")
    print("-" * 80)
    
    # 创建聊天历史
    chat_history = [
        {
            "role": "user",
            "content": question
        }
    ]
    
    # 运行模型
    response = run_gemini_model(question)
    
    # 提取回答
    answer = extract_message_content(response)
    
    # 添加到聊天历史
    chat_history.append({
        "role": "assistant",
        "content": answer
    })
    
    # 打印回答
    print(f"Answer: {answer}")
    
    # 打印聊天历史（可被其他工具提取）
    print("\nChat History:")
    print(json.dumps(chat_history, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
