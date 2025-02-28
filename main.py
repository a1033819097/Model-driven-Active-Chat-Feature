import random
import asyncio
import json
from datetime import datetime, timedelta
import astrbot.api.star as star
import astrbot.api.event.filter as filter
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.core.message.message_event_result import MessageChain
from astrbot.api import logger
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember, MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.provider.manager import Personality
from astrbot.core.message.components import Plain  # 添加缺失的Plain导入
from astrbot.core.star.star_handler import star_handlers_registry, EventType  # 添加缺失的导入

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
        self.prob = 0.02
        self.triggers = DEFAULT_TRIGGERS.copy()
        self.target_id = "1033819097"
        self.timer_task = None
        self.last_trigger_time = None  # 记录上次触发时间
        
        # 移除人格相关属性，改为从provider_manager获取
        
    async def initialize(self):
        """初始化插件，启动定时器"""
        self.timer_task = asyncio.create_task(self._timer_loop())
        logger.info("主动对话定时器已启动")
        
    async def _timer_loop(self):
        """定时器循环，每分钟检查一次"""
        while True:
            try:
                current_time = datetime.now()
                
                # 修复时间判断逻辑：只在7点到23点59分之间允许触发
                if 7 <= current_time.hour < 24:
                    # 检查是否满足间隔时间要求（距离上次触发超过1小时）
                    if (self.last_trigger_time is None or 
                        current_time - self.last_trigger_time >= timedelta(hours=1)):
                        
                        if random.random() < self.prob:
                            logger.info(f"触发主动对话检查 - 当前时间: {current_time.strftime('%H:%M:%S')}, "
                                      f"概率: {self.prob}, 上次触发: "
                                      f"{self.last_trigger_time.strftime('%H:%M:%S') if self.last_trigger_time else '无'}")
                            await self._initiate_conversation()
                            self.last_trigger_time = current_time
                else:
                    logger.debug(f"当前时间 {current_time.strftime('%H:%M:%S')} 不在允许的对话时间范围内(07:00-24:00)")
            except Exception as e:
                logger.error(f"主动对话出错: {e}")
            await asyncio.sleep(60)  # 每分钟检查一次

    async def _initiate_conversation(self):
        """发起主动对话"""
        if not self.triggers:
            logger.warning("没有可用的触发语句")
            return
            
        trigger = random.choice(self.triggers)
        provider = self.context.get_using_provider()
        if not provider:
            logger.error("未找到可用的 LLM 提供商")
            return

        unified_msg = f"aiocqhttp:FriendMessage:{self.target_id}"
        
        try:
            # 构造一个模拟的消息事件
            mock_message = AstrBotMessage()
            mock_message.type = MessageType.FRIEND_MESSAGE
            mock_message.message = [Plain(trigger)]
            mock_message.sender = MessageMember(user_id=self.target_id)
            mock_message.self_id = self.target_id
            mock_message.session_id = self.target_id
            mock_message.message_str = trigger
            
            mock_event = AstrMessageEvent(
                message_str=trigger,
                message_obj=mock_message,
                platform_meta=PlatformMetadata(
                    name="aiocqhttp",
                    description="模拟的aiocqhttp平台"
                ),
                session_id=self.target_id
            )
            
            # 获取或创建对话
            curr_cid = await self.context.conversation_manager.get_curr_conversation_id(unified_msg)
            if not curr_cid:
                curr_cid = await self.context.conversation_manager.new_conversation(unified_msg)
            
            # 获取对话信息
            conversation = await self.context.conversation_manager.get_conversation(unified_msg, curr_cid)
            context = []
            system_prompt = ""
            
            if conversation:
                context = json.loads(conversation.history) if conversation.history else []
                persona_id = conversation.persona_id
                
                if persona_id == "[%None]":
                    system_prompt = ""
                else:
                    try:
                        default_persona = self.context.provider_manager.selected_default_persona
                        if default_persona:
                            system_prompt = default_persona.get('prompt', '')
                    except Exception as e:
                        logger.warning(f"获取默认人格失败: {e}")
            
            # 使用标准的LLM请求流程
            llm_req = mock_event.request_llm(
                prompt=trigger,
                session_id=curr_cid,
                contexts=context,
                system_prompt=system_prompt,
                conversation=conversation
            )
            mock_event.set_extra("provider_request", llm_req)
            
            # 执行LLM请求并获取响应
            response = await provider.text_chat(**llm_req.__dict__)
            
            # 触发on_llm_response事件
            handlers = star_handlers_registry.get_handlers_by_event_type(EventType.OnLLMResponseEvent)
            for handler in handlers:
                try:
                    await handler.handler(mock_event, response)
                except Exception as e:
                    logger.error(f"处理LLM响应时出错: {e}")
            
            if not response.completion_text:
                logger.error("LLM 响应为空")
                return
                
            # 发送消息
            await self.context.send_message(unified_msg, MessageChain().message(response.completion_text))
            logger.info(f"已发送主动对话: {trigger} -> {response.completion_text}")
            
        except Exception as e:
            logger.error(f"主动对话出错: {str(e)}")
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
        """列出当前的主动对话概率和时间限制信息"""
        msg = f"当前主动对话概率为: {self.prob}\n"
        msg += "对话时间限制：早7点到晚24点\n"
        msg += "两次对话最小间隔：1小时"
        if self.last_trigger_time:
            msg += f"\n上次触发时间：{self.last_trigger_time.strftime('%Y-%m-%d %H:%M:%S')}"
        yield event.plain_result(msg)

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

    @filter.command("set_persona")
    async def set_persona(self, event: AstrMessageEvent, persona_name: str):
        """设置使用的人格"""
        try:
            default_persona = self.context.provider_manager.selected_default_persona
            if default_persona and default_persona.get('name') == persona_name:
                yield event.plain_result(f"已切换到人格: {persona_name}")
                return
        except Exception as e:
            logger.warning(f"获取默认人格失败: {e}")
            yield event.plain_result("设置人格失败，请确认人格配置是否正确")
            return

    @filter.command("list_persona")
    async def list_persona(self, event: AstrMessageEvent):
        """列出当前可用的人格"""
        try:
            default_persona = self.context.provider_manager.selected_default_persona
            persona_name = default_persona.get('name', '无') if default_persona else '无'
            yield event.plain_result(f"当前使用的默认人格: {persona_name}")
        except Exception as e:
            logger.warning(f"获取默认人格失败: {e}")
            yield event.plain_result("获取人格信息失败，请确认人格配置是否正确")

    async def shutdown(self):
        """关闭插件时停止定时器"""
        if self.timer_task:
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
