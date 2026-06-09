"""AI自动审核模块 - 用于分析加群申请是否应该通过"""

from pydantic import BaseModel, Field

from zhenxun.services.llm import generate_structured
from zhenxun.services.log import logger


class JoinRequestReview(BaseModel):
    """加群申请审核结果模型

    AI只负责拒绝明显不合格的申请，不处理通过的情况。
    """

    should_approve: bool = Field(description="AI是否认为可以不拒绝(True=不拒绝继续等待人工, False=直接拒绝)")
    confidence: float = Field(description="判断的置信度(0.0-1.0)", ge=0.0, le=1.0)
    reason: str = Field(description="判断理由的详细说明(内部使用)")
    risk_level: str = Field(description="风险等级: low(低风险), medium(中等风险), high(高风险)")
    reject_message: str = Field(description="拒绝理由(精准、简洁,15字以内)")


async def analyze_join_request(
    user_id: int,
    nickname: str,
    qq_level: int,
    comment: str,
    group_id: int,
    model_name: str | None = None
) -> JoinRequestReview:
    """使用AI分析加群申请,判断是否应该拒绝

    AI职责: 只负责拒绝明显不合格的申请,不处理通过的情况。
    - 当AI发现明显问题时: 直接拒绝 + 给出精准理由
    - 当AI未发现明显问题时: 不做任何操作,继续等待人工审核

    AI会识别和处理"问题-答案"格式的加群理由,并根据:
    - 答案是否直接回答问题
    - 答案的有效性和真实性
    - 内容的安全性
    给出精准的拒绝理由(如"未提供邀请码"、"答案无意义"等)

    Args:
        user_id: 申请人QQ号
        nickname: 申请人昵称
        qq_level: 申请人QQ等级
        comment: 加群理由(可能包含问题-答案格式)
        group_id: 目标群号
        model_name: 指定的模型名称,None则使用全局默认

    Returns:
        JoinRequestReview: 审核结果
            - should_approve=False: AI发现问题,直接拒绝
            - should_approve=True: AI未发现明显问题,不处理
            - reject_message: 精准的拒绝理由(≤15字)

    Raises:
        Exception: AI分析失败时抛出
    """
    try:
        prompt = f"""
你是一个严格的群组管理员助手，负责审核加群申请。你的任务是识别并拒绝明显不合格的申请。

【你的职责】
你只负责拒绝明显有问题的申请，不负责批准任何申请。
- 发现明显问题 → 拒绝 + 给出精准理由
- 未发现明显问题 → 不做任何操作，让人工继续处理

【重要提示】
这个申请**没有通过系统的自动审核规则**，所以才需要你来判断是否应该拒绝。
你应该采取**严格审核**的态度，只拒绝那些明显有问题的申请。

【申请信息】
- 申请人QQ号: {user_id}
- 申请人昵称: {nickname}
- 加群理由: {comment}
- 目标群号: {group_id}

注意: QQ等级已经在前置流程中检查过了，你不需要关注等级问题。

【加群理由格式识别】
加群理由可能包含以下格式：
1. **问题-答案格式**: 如"邀请码:ABC123"、"问题:XXX 答案:XXX"、"从哪知道的?朋友介绍"
2. **纯文本格式**: 直接描述加群目的
3. **结构化格式**: 包含多个字段的表单式内容

**针对问题-答案格式的审核重点**:
- 识别问题的核心要求(如:邀请码、来源、目的等)
- 检查答案是否**直接回答**了问题
- 判断答案的**有效性**和**真实性**

【明显应该拒绝的情况】:
1. **未回答问题**:
   - 答案为空或未提供必填信息(如邀请码为空)
   - 拒绝理由: "未提供邀请码"、"未填写加群目的"、"缺少自我介绍"

2. **答非所问**:
   - 答案与问题完全不符(如邀请码填"不知道")
   - 无意义的随机数字、字符
   - 拒绝理由: "邀请码格式错误"、"未说明群来源"、"答案无意义"

3. **过于敷衍**:
   - "看看"、"随便"、"不知道"、"玩玩"等敷衍词汇
   - 拒绝理由: "目的过于简单"、"理由不够充分"、"信息不具体"

4. **疑似机器人**:
   - 标点符号("."、"..."）
   - 单一字符("1"、"a")
   - 重复无意义字符
   - 拒绝理由: "疑似机器人"、"内容不真实"

5. **违规内容**:
   - 广告、推广、引流信息
   - 违规网址、联系方式
   - 不当言论
   - 拒绝理由: "包含广告信息"、"包含违规内容"

【不应该拒绝的情况】:
- 答案准确回答了所有问题
- 内容真实、具体、有意义
- 语言表达正常，符合人类特征
- 没有任何违规或明显风险

→ 这种情况返回 should_approve=True，让人工继续审核

【置信度要求】:
- **拒绝**: 置信度应该≥0.75(较确定有问题才拒绝)
- **不拒绝**: 置信度可以较低(不确定就不拒绝，交给人工)

【风险等级评估】:
- high: 明显有问题、答非所问、疑似违规 → 应该拒绝
- medium: 存在疑点但不够明显 → 不拒绝，交给人工
- low: 没有明显问题 → 不拒绝，交给人工

【拒绝理由撰写要求】:
如果决定拒绝，你需要提供一个**精准、极简**的拒绝理由。

**核心原则**:
1. **严格限制在15字以内**(受平台限制)
2. **针对具体问题**: 明确指出哪里不符合
3. **去除废话**: 不要"抱歉"、"请"等礼貌词
4. **可操作**: 让申请人知道怎么改正

**拒绝理由示例**(均≤15字):
针对未回答:
- "未提供邀请码"
- "未填写加群目的"
- "缺少自我介绍"

针对答非所问:
- "邀请码格式错误"
- "未说明群来源"
- "答案不符合要求"

针对敷衍回答:
- "目的过于简单"
- "理由不够充分"
- "信息不具体"

针对无意义内容:
- "答案无意义"
- "疑似机器人"
- "内容不真实"

针对违规内容:
- "包含广告信息"
- "包含违规内容"

请严格按照以上标准审核，**只拒绝明显有问题的申请，给出精准拒绝理由**。
记住: 不要考虑QQ等级因素，专注于加群理由的内容质量和问答匹配度。
"""

        result: JoinRequestReview = await generate_structured(
            message=prompt,
            response_model=JoinRequestReview,
            instruction="你是严格的群组管理员，只负责拒绝明显有问题的申请。重点审核: 1)识别问题-答案格式; 2)判断答案是否直接回答问题; 3)检查答案的有效性和真实性。只拒绝明显有问题的，不确定就交给人工。IMPORTANT: 拒绝理由必须精准、针对具体问题(如'未提供邀请码'、'答案无意义')，严格控制在15字以内。",
            model=model_name,
        )

        logger.info(
            f"AI审核完成 - 用户:{nickname}({user_id}) "
            f"结果:{'不拒绝' if result.should_approve else '拒绝'} "
            f"置信度:{result.confidence:.2f} 风险:{result.risk_level} "
            f"理由:{result.reason}",
            "加群申请处理",
        )

        return result

    except Exception as e:
        logger.error(f"AI分析加群申请失败: {e}", "加群申请处理", e=e)
        # 失败时返回一个保守的结果(不批准)
        return JoinRequestReview(
            should_approve=False,
            confidence=0.0,
            reason=f"AI分析失败: {str(e)}",
            risk_level="high",
            reject_message="AI审核失败"
        )
