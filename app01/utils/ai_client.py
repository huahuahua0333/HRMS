# ============================================================
# 模块：AI 大模型客户端封装（扩展功能）
# 作用：统一封装对大模型接口的调用，业务视图只调用这里的方法，
#       不直接写 HTTP 请求细节；更换平台 / 密钥时只改 settings 配置。
# 设计要点：
#   1. 仅使用 Python 标准库 urllib，不新增第三方依赖（无需改 requirements.txt）；
#   2. 兼容 OpenAI Chat Completions 协议（/v1/chat/completions）；
#   3. API Key 未配置、网络异常、返回解析失败等情况都返回友好提示，
#      不把异常抛到页面导致系统崩溃。
# ============================================================
import json
import logging
import socket
import urllib.request
import urllib.error

from django.conf import settings

logger = logging.getLogger("app01")


# ============================================================
# 判断是否已配置 API Key
# ============================================================
def is_configured():
    """返回 True 表示已填写 API Key，可以发起调用。"""
    return bool(getattr(settings, "AI_API_KEY", "").strip())


# ============================================================
# 通用对话调用
# ============================================================
def chat(messages, temperature=0.7, max_tokens=1000):
    """
    调用大模型对话接口。

    参数：
        messages: 消息列表，格式为
                  [{"role": "system"/"user"/"assistant", "content": "..."}, ...]
        temperature: 采样温度，越高越发散，越低越稳定
        max_tokens: 单次回复最大 token 数

    返回：
        (success, content) 二元组
        - success: bool，是否调用成功
        - content: 成功时为模型回复文本；失败时为友好的中文错误提示
    """
    # 1. 读取 settings 中的配置（密钥、接口地址、模型名、超时时间）
    api_key = getattr(settings, "AI_API_KEY", "").strip()

    # 未配置 Key：直接降级返回提示，不发起网络请求
    if not api_key:
        return False, "尚未配置 AI_API_KEY，请在 settings.py 中填入 API Key 后再使用。"

    api_base = getattr(settings, "AI_API_BASE", "")
    model = getattr(settings, "AI_MODEL", "gpt-3.5-turbo")
    timeout = getattr(settings, "AI_TIMEOUT", 15)

    # 2. 组装请求体（OpenAI 兼容格式）
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")

    # 3. 构造请求：携带 Bearer 鉴权头
    req = urllib.request.Request(
        api_base,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )

    # 4. 发起请求并解析返回，各类异常都兜底成友好提示
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        # OpenAI 兼容返回结构：choices[0].message.content
        content = body["choices"][0]["message"]["content"].strip()
        return True, content

    except urllib.error.HTTPError as e:
        # 读取平台返回的错误信息（如硅基流动：{"code":30001,"message":"..."}）
        detail = ""
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            detail = err_body.get("message", "")
        except Exception:
            pass
        logger.warning("AI 接口 HTTP 错误：%s %s", e.code, detail)

        if e.code == 401:
            return False, "API Key 无效或已过期，请检查 settings.py 中的 AI_API_KEY。"
        if e.code == 402:
            return False, "AI 账户可用额度不足（402）：请确认已在模型平台完成实名认证，并领取免费额度/代金券后再使用。"
        if e.code == 429:
            return False, "AI 调用过于频繁，请稍后再试。"
        tip = ("：" + detail) if detail else ""
        return False, "AI 接口请求失败（HTTP %s）%s，请检查模型配置。" % (e.code, tip)

    except urllib.error.URLError as e:
        # 网络不通、域名无法解析等连接错误
        logger.warning("AI 接口网络错误：%s", e.reason)
        return False, "无法连接 AI 服务，请检查网络后重试。"

    except (TimeoutError, socket.timeout) as e:
        # 模型在超时时间内未返回首字节（推理模型排队 / 负载高时常见）
        logger.warning("AI 接口读取超时：%s", e)
        return False, "模型响应超时，请稍后重试；若持续超时，可在 settings.py 更换响应更快的模型。"

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        # 返回结构不符合预期 / JSON 解析失败
        logger.warning("AI 接口返回解析失败：%s", e)
        return False, "AI 接口返回格式异常，请联系管理员检查配置。"

    except Exception as e:  # 最后兜底，避免异常冒泡导致页面崩溃
        logger.warning("AI 调用异常：%s", e)
        return False, "AI 服务暂时不可用，请稍后再试。"


# ============================================================
# 业务封装：根据公告标题和要点生成正式公告正文
# ============================================================
def generate_notice(title, points=""):
    """
    生成公告正文。

    参数：
        title: 公告标题（必填）
        points: 补充要点（可选，为空则仅依据标题扩写）
    返回：
        同 chat() 的 (success, content) 二元组
    """
    system_prompt = (
        "你是企业行政文案助手。请根据用户给出的公告标题和要点，"
        "撰写一段正式、简洁、通顺的企业内部公告正文；"
        "不要重复输出标题本身，不要使用 Markdown 标记。"
    )
    user_prompt = "公告标题：%s\n补充要点：%s\n请据此撰写公告正文：" % (
        title,
        points or "无",
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat(messages, temperature=0.6, max_tokens=600)


# ============================================================
# 业务封装：根据岗位名称生成招聘 JD
# ============================================================
def generate_jd(role_name):
    """
    生成招聘岗位描述（JD）。

    参数：
        role_name: 岗位名称（如 人事专员、Python 后端工程师）
    返回：
        同 chat() 的 (success, content) 二元组
    """
    system_prompt = (
        "你是企业招聘文案助手。请根据用户给出的岗位名称，撰写一份规范的招聘岗位描述（JD），"
        "包含“岗位职责”“任职要求”“薪资范围”三部分，条目清晰、语气正式；"
        "不要重复输出岗位名称标题，不要使用 Markdown 标记。"
    )
    user_prompt = "岗位名称：%s\n请生成招聘岗位描述：" % role_name
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat(messages, temperature=0.7, max_tokens=700)
