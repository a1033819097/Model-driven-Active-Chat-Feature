import random
import asyncio
import astrbot.api.star as star
import astrbot.api.event.filter as filter
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.core.message.message_event_result import MessageChain
from astrbot.api import logger
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember, MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata

DEFAULT_TRIGGERS = [
    "你现在感觉有点无聊，想跟朋友打个招呼吧？那就去和你的朋友问声好吧！",
    "你想知道你朋友最近的学习情况，现在向他询问吧。",
    "你想知道你朋友今天过得怎么样，现在就询问他吧。",
    "你正在看书，特别想和你朋友分享，现在向他分享吧。",
    "你正在逛街，想和你朋友分享，现在向他分享吧。",
    "你刚刚听了一首很棒的歌，迫不及待地想推荐给你的朋友，现在告诉他吧！",
    "你突然想起了一个好笑的笑话，觉得你的朋友一定会喜欢，现在讲给他听吧！",
    "你最近想看电影，想问问你的朋友有没有兴趣一起看,现在问问他吧。",
    "你正在做一道新菜，想问问你的朋友喜欢什么样的口味，现在问问他吧。",
    "你刚完成了一项任务，感到很有成就感，想和你的朋友分享这份喜悦。现在向他分享吧。",
    "你发现了一个很有趣的小知识，觉得你的朋友可能会感兴趣，现在告诉他吧！",
    "你最近在计划一次旅行，想问问你的朋友有没有什么好的建议。现在向他询问吧。",
    "你今天的心情很好，想和你的朋友聊聊天，分享一下你的快乐，现在向他分享吧。",
    "你刚刚学到了一项新技能，想问问你的朋友有没有兴趣一起学习，现在问问他吧。",
    "你正在思考人生的一些问题，想找你的朋友聊聊，听听他的看法，现在找他开启话题吧。",
    "你发现了一家新开的餐厅，想问问你的朋友要不要一起去尝尝，现在问问他吧。",
    "你刚刚完成了一次运动，感觉很棒，想鼓励你的朋友也一起来锻炼，现在找他开启话题吧",
    "你今天看到了一幅美丽的风景，想用文字描述给你朋友听，让他也感受一下，现在找他开启话题吧。"
]

@star.register(name="initiate-conversation", desc="主动发起对话功能", author="Soulter", version="1.0.0")
class Main(star.Star):
    def __init__(self, context: star.Context) -> None:
        self.context = context
        self.prob = 0.05  # 默认触发概率为 0.3
        self.triggers = DEFAULT_TRIGGERS.copy()
        self.target_id = "123456789"  # 目标用户ID
        self.timer_task = None
        
    async def initialize(self):
        """初始化插件，启动定时器"""
        self.timer_task = asyncio.create_task(self._timer_loop())
        logger.info("主动对话定时器已启动")
        
    async def _timer_loop(self):
        """定时器循环，每分钟检查一次"""
        while True:
            try:
                if random.random() < self.prob:
                    await self._initiate_conversation()
            except Exception as e:
                logger.error(f"主动对话出错: {e}")
            await asyncio.sleep(60)  # 每分钟检查一次

    async def _initiate_conversation(self):
        """发起主动对话"""
        if not self.triggers:
            logger.warning("没有可用的触发语句")
            return
            
        # 随机选择一个触发语句
        trigger = random.choice(self.triggers)
        
        # 获取 LLM provider
        provider = self.context.get_using_provider()
        if not provider:
            logger.error("未找到可用的 LLM 提供商")
            return
        
        # 构造统一的会话ID (platform:message_type:session_id)
        session = f"aiocqhttp:FriendMessage:{self.target_id}"
        
        # 直接向 LLM 发送请求
        try:
            response = await provider.text_chat(
                prompt=trigger,
                session_id=session,
                contexts=[]  # 添加空的上下文列表
            )
            
            if not response.completion_text:
                logger.error("LLM 响应为空")
                return
                
            # 修正：使用 message() 方法而不是 plain()
            await self.context.send_message(session, MessageChain().message(response.completion_text))
            logger.info(f"已发送主动对话: {trigger} -> {response.completion_text}")
            
        except Exception as e:
            logger.error(f"请求 LLM 失败: {e}")
            return

    @filter.command("set_prob")
    async def set_prob(self, event: AstrMessageEvent, prob: float):
        """设置主动对话概率"""
        if prob < 0 or prob > 1:
            yield event.plain_result("概率值必须在 0 到 1 之间")
            return
            
        self.prob = prob
        yield event.plain_result(f"已设置主动对话概率为: {prob}")

    @filter.command("list_prob")
    async def list_prob(self, event: AstrMessageEvent):
        """列出当前的主动对话概率"""
        yield event.plain_result(f"当前主动对话概率为: {self.prob}")

    @filter.command("list_trigger")
    async def list_trigger(self, event: AstrMessageEvent):
        """列出所有触发语句"""
        if not self.triggers:
            yield event.plain_result("当前没有触发语句")
            return
            
        msg = "当前的触发语句:\n"
        for i, trigger in enumerate(self.triggers):
            msg += f"{i+1}. {trigger}\n"
            
        yield event.plain_result(msg)

    @filter.command("add_trigger")
    async def add_trigger(self, event: AstrMessageEvent, trigger: str):
        """添加新的触发语句"""
        self.triggers.append(trigger)
        yield event.plain_result(f"已添加触发语句: {trigger}")

    @filter.command("del_trigger") 
    async def del_trigger(self, event: AstrMessageEvent, index: int):
        """删除指定的触发语句"""
        if index < 1 or index > len(self.triggers):
            yield event.plain_result("无效的触发语句索引")
            return
            
        deleted = self.triggers.pop(index-1)
        yield event.plain_result(f"已删除触发语句: {deleted}")

    async def shutdown(self):
        """关闭插件时停止定时器"""
        if self.timer_task:
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
