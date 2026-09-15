from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CaptionLabel,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    SubtitleLabel,
)

from Agent.CustomerAgent.custom.customer_agent import CustomerAgent
from bridge.context import ChannelType, Context, ContextType
from core.di_container import container
from database.db_manager import db_manager
from database.knowledge_service import KnowledgeService
from utils.logger_loguru import get_logger

logger = get_logger("LocalTestUI")


class LocalAgentWorker(QThread):
    """在后台线程中运行 Agent，避免阻塞 UI。"""

    reply_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str, account_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.query = query
        self.account_info = account_info

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self._ask_agent())
            self.reply_ready.emit(result)
        except Exception as e:
            logger.error(f"本地测试提问失败: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()

    async def _ask_agent(self) -> Dict[str, Any]:
        agent = CustomerAgent()
        context = Context.create_platform_context(
            content=self.query,
            from_uid="local_demo_user",
            nickname="本地演示用户",
            user_msg_type=ContextType.TEXT,
            # Context kwargs 中 shop_id 需要是字符串，后续 MessageBuilder 会再转成 int
            shop_id=str(self.account_info["db_shop_id"]),
            user_id=f"local_debug_{self.account_info['user_id']}",
            username=self.account_info["username"],
            shop_name=self.account_info["shop_name"],
            channel_type=ChannelType.PLATFORM,
        )
        started_at = time.perf_counter()
        reply = await agent.async_reply(self.query, context)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "reply": getattr(reply, "content", str(reply)),
            "elapsed_ms": elapsed_ms,
            "trace": getattr(agent, "last_trace", {}),
        }


class LocalTestUI(QFrame):
    """本地提问测试页，用于演示 Agent 回复能力。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("local-test")
        self.worker: Optional[LocalAgentWorker] = None
        self.account_items: List[Dict[str, Any]] = []
        self.latest_query = ""
        self.latest_rag_result: Dict[str, Any] = {}
        self.logger = get_logger("LocalTestUI")
        self.knowledge_service = container.get(KnowledgeService)

        self._init_ui()
        self._load_accounts()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        self.setObjectName("localTestRoot")

        title = SubtitleLabel("Agent + RAG 演示台", self)
        root_layout.addWidget(title)

        hint = QLabel(
            "左侧用于展示 Agent 对话，右侧用于展示本次问题命中的 RAG 检索结果。"
            "这样可以同时说明系统如何检索知识、又如何生成最终客服回复。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("pageHint")
        root_layout.addWidget(hint)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        account_label = QLabel("演示账号:")
        self.account_combo = ComboBox()
        self.account_combo.setMinimumWidth(320)
        self.account_combo.currentIndexChanged.connect(self._on_account_changed)

        self.refresh_btn = PushButton("刷新账号")
        self.refresh_btn.clicked.connect(self._load_accounts)

        self.clear_btn = PushButton("清空记录")
        self.clear_btn.clicked.connect(self._clear_chat)

        self.search_btn = PushButton("只看检索")
        self.search_btn.clicked.connect(self._preview_retrieval_only)

        top_bar.addWidget(account_label)
        top_bar.addWidget(self.account_combo)
        top_bar.addWidget(self.refresh_btn)
        top_bar.addWidget(self.search_btn)
        top_bar.addWidget(self.clear_btn)
        top_bar.addStretch()
        root_layout.addLayout(top_bar)

        self.current_account_label = QLabel("当前未选择账号")
        self.current_account_label.setObjectName("accountHint")
        root_layout.addWidget(self.current_account_label)

        sample_frame = QFrame(self)
        sample_frame.setObjectName("sampleFrame")
        sample_layout = QHBoxLayout(sample_frame)
        sample_layout.setContentsMargins(12, 12, 12, 12)
        sample_layout.setSpacing(8)

        sample_layout.addWidget(QLabel("示例问题:"))
        for text in [
            "这款精华液适合敏感肌吗？",
            "这款防晒多久补涂一次？",
            "多久发货？",
            "可以退款吗？",
            "帮我转人工",
        ]:
            btn = PushButton(text)
            btn.clicked.connect(lambda _, q=text: self._fill_example(q))
            sample_layout.addWidget(btn)
        sample_layout.addStretch()
        root_layout.addWidget(sample_frame)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        chat_card = CardWidget(self)
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(16, 16, 16, 16)
        chat_layout.setSpacing(10)
        chat_card.setObjectName("softCard")
        chat_layout.addWidget(StrongBodyLabel("Agent 对话区"))

        chat_hint = CaptionLabel("展示用户问题与最终客服回复")
        chat_hint.setObjectName("cardHint")
        chat_layout.addWidget(chat_hint)

        self.chat_view = QTextEdit(self)
        self.chat_view.setReadOnly(True)
        self.chat_view.setPlaceholderText("这里会显示本地测试对话记录...")
        self.chat_view.setMinimumHeight(360)
        chat_layout.addWidget(self.chat_view, 1)

        rag_card = CardWidget(self)
        rag_layout = QVBoxLayout(rag_card)
        rag_layout.setContentsMargins(16, 16, 16, 16)
        rag_layout.setSpacing(10)
        rag_card.setObjectName("softCard")
        rag_layout.addWidget(StrongBodyLabel("RAG 检索区"))

        rag_hint = CaptionLabel("展示本次问题命中的商品知识、客服知识和检索说明")
        rag_hint.setObjectName("cardHint")
        rag_layout.addWidget(rag_hint)

        self.rag_summary_label = BodyLabel("尚未开始检索")
        self.rag_summary_label.setWordWrap(True)
        rag_layout.addWidget(self.rag_summary_label)

        self.rag_source_label = CaptionLabel("知识来源：等待提问")
        self.rag_source_label.setStyleSheet("color: #666;")
        rag_layout.addWidget(self.rag_source_label)

        self.rag_view = QTextEdit(self)
        self.rag_view.setReadOnly(True)
        self.rag_view.setPlaceholderText("这里会显示与当前问题相关的知识命中内容...")
        rag_layout.addWidget(self.rag_view, 1)

        self.flow_view = QTextEdit(self)
        self.flow_view.setReadOnly(True)
        self.flow_view.setMaximumHeight(210)
        self.flow_view.setPlaceholderText("这里会显示回答分析、工具调用和演示说明...")
        rag_layout.addWidget(self.flow_view)

        splitter.addWidget(chat_card)
        splitter.addWidget(rag_card)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root_layout.addWidget(splitter, 1)

        input_label = QLabel("输入问题:")
        root_layout.addWidget(input_label)

        self.input_edit = QTextEdit(self)
        self.input_edit.setPlaceholderText("例如：这款精华液适合敏感肌吗？")
        self.input_edit.setMinimumHeight(110)
        root_layout.addWidget(self.input_edit)

        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(12)

        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")

        self.send_btn = PrimaryPushButton("发送提问")
        self.send_btn.clicked.connect(self._send_question)

        bottom_bar.addWidget(self.status_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.send_btn)
        root_layout.addLayout(bottom_bar)

        self._apply_styles()
        self._reset_rag_panel()

    def _apply_styles(self):
        self.setStyleSheet(
            """
            #localTestRoot {
                background: #f7f0e4;
            }
            QLabel#pageHint {
                color: #766754;
                font-size: 13px;
                padding: 2px 2px 8px 2px;
            }
            QLabel#accountHint {
                color: #5e5144;
                background: #f2e8d8;
                border: 1px solid #dccbb2;
                border-radius: 8px;
                padding: 8px 12px;
            }
            QLabel#statusLabel {
                color: #7b6b58;
                padding-left: 4px;
            }
            QLabel#cardHint {
                color: #8a7966;
            }
            QFrame#sampleFrame {
                background: #fffaf2;
                border: 1px solid #e1d3bc;
                border-radius: 12px;
            }
            CardWidget#softCard {
                background: #fffaf2;
                border: 1px solid #e1d3bc;
                border-radius: 16px;
            }
            QTextEdit {
                background: #fffcf7;
                border: 1px solid #ddceb9;
                border-radius: 12px;
                padding: 10px 12px;
                selection-background-color: #dcc6a7;
            }
            QTextEdit:focus {
                border: 1px solid #b5926a;
            }
            QSplitter::handle {
                background: #ede0cd;
                width: 6px;
            }
            QSplitter::handle:hover {
                background: #dcc8ad;
            }
            """
        )

    def _load_accounts(self):
        self.account_combo.clear()
        self.account_items = []

        accounts = db_manager.get_all_accounts_with_details()
        if not accounts:
            self.account_combo.addItem("请先在账号管理中添加账号")
            self.current_account_label.setText("未检测到可用账号")
            self.send_btn.setEnabled(False)
            return

        def sort_key(item: Dict[str, Any]):
            username = item.get("username", "")
            return (0 if username.startswith(("mock_", "test_")) else 1, item.get("shop_name", ""))

        for account in sorted(accounts, key=sort_key):
            shop = db_manager.get_shop(account["channel_name"], account["shop_id"])
            if not shop:
                continue

            item = dict(account)
            item["db_shop_id"] = shop["id"]
            self.account_items.append(item)
            label = f"{item['shop_name']} / {item['username']}"
            self.account_combo.addItem(label)

        if not self.account_items:
            self.account_combo.addItem("账号数据异常，请先重新添加账号")
            self.current_account_label.setText("未检测到可用账号")
            self.send_btn.setEnabled(False)
            return

        self.account_combo.setCurrentIndex(0)
        self.send_btn.setEnabled(True)
        self._on_account_changed()

    def _get_current_account(self) -> Optional[Dict[str, Any]]:
        index = self.account_combo.currentIndex()
        if index < 0 or index >= len(self.account_items):
            return None
        return self.account_items[index]

    def _on_account_changed(self):
        account = self._get_current_account()
        if not account:
            self.current_account_label.setText("当前未选择账号")
            return

        self.current_account_label.setText(
            f"当前店铺：{account['shop_name']}    内部店铺ID：{account['db_shop_id']}    演示账号：{account['username']}"
        )
        self._reset_rag_panel()

    def _fill_example(self, question: str):
        self.input_edit.setPlainText(question)
        self.input_edit.setFocus()

    def _append_message(self, role: str, content: str):
        if role == "用户":
            color = "#7a5b3c"
            background = "#f7ede0"
            border = "#e1cfb4"
        else:
            color = "#6b7148"
            background = "#f5f3e8"
            border = "#ddd7c1"
        html = (
            f"<div style='margin: 10px 0; padding: 10px 12px; background: {background}; "
            f"border: 1px solid {border}; border-radius: 10px;'>"
            f"<span style='font-weight: 700; color: {color};'>【{role}】</span><br>"
            f"<span style='color: #4f4336; line-height: 1.65;'>{content.replace(chr(10), '<br>')}</span>"
            f"</div>"
        )
        self.chat_view.append(html)
        self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum())

    def _clear_chat(self):
        self.chat_view.clear()
        self.status_label.setText("已清空本地记录")
        self._reset_rag_panel()

    def _reset_rag_panel(self):
        self.rag_summary_label.setText("等待输入问题，可同时展示 Agent 回复与 RAG 检索命中。")
        self.rag_source_label.setText("知识来源：商品知识库 + 客服知识库")
        self.rag_view.setPlainText(
            "推荐演示顺序\n"
            "------------------------------\n"
            "1. 输入一个商品问题，观察是否命中商品知识\n"
            "2. 输入一个售后问题，观察是否命中客服知识\n"
            "3. 对比右侧检索结果与左侧最终回复，讲解“先检索，再生成”"
        )
        self.flow_view.setPlainText(
            "回答分析面板\n"
            "------------------------------\n"
            "等待提问后展示：\n"
            "1. RAG 命中数量\n"
            "2. Agent 工具调用\n"
            "3. LLM 调用次数与耗时\n"
            "4. 是否进入兜底策略"
        )

    def _search_knowledge(self, query: str, account: Dict[str, Any]) -> Dict[str, Any]:
        return self.knowledge_service.search_knowledge(
            shop_id=account["db_shop_id"],
            query=query,
            limit=3,
        )

    def _format_rag_result(self, result: Dict[str, Any]) -> str:
        products = result.get("product_knowledge", [])
        cs_list = result.get("customer_service_knowledge", [])
        sections: List[str] = []

        if products:
            lines = ["【商品知识命中】"]
            for i, product in enumerate(products, 1):
                lines.append(f"{i}. {product.goods_name} (ID: {product.goods_id})")
                if product.price:
                    lines.append(f"   价格: {product.price}")
                if product.extracted_content:
                    content = product.extracted_content[:180]
                    if len(product.extracted_content) > 180:
                        content += "..."
                    lines.append(f"   摘要: {content}")
            sections.append("\n".join(lines))

        if cs_list:
            lines = ["【客服知识命中】"]
            for i, item in enumerate(cs_list, 1):
                lines.append(f"{i}. {item.title}")
                content = item.content[:160]
                if len(item.content) > 160:
                    content += "..."
                lines.append(f"   摘要: {content}")
                if item.tags:
                    lines.append(f"   标签: {item.tags}")
            sections.append("\n".join(lines))

        if not sections:
            return (
                "未命中本地知识。\n\n"
                "这时可以向他人说明：系统会先尝试检索业务知识，"
                "若没有命中，再进入兜底生成或继续追问。"
            )

        return "\n\n".join(sections)

    def _update_rag_panel(self, query: str, result: Dict[str, Any]):
        products = result.get("product_knowledge", [])
        cs_list = result.get("customer_service_knowledge", [])

        self.rag_summary_label.setText(
            f"本次问题“{query}”共命中 {len(products)} 条商品知识、{len(cs_list)} 条客服知识。"
        )

        source_parts = []
        if products:
            source_parts.append("商品知识库")
        if cs_list:
            source_parts.append("客服知识库")
        if not source_parts:
            source_parts.append("未命中知识库")
        self.rag_source_label.setText(f"知识来源：{' + '.join(source_parts)}")

        self.rag_view.setPlainText(self._format_rag_result(result))

        if products and not cs_list:
            scene = "该问题更偏商品咨询，系统优先从商品知识中检索，再由 Agent 组织成客服回复。"
        elif cs_list and not products:
            scene = "该问题更偏售后/规则咨询，系统优先从客服知识中检索，再由 Agent 组织成客服回复。"
        elif products and cs_list:
            scene = "该问题同时命中了商品知识和客服知识，可以说明系统具备多源检索增强能力。"
        else:
            scene = "该问题未命中本地知识，可向他人说明系统存在知识缺失时的兜底策略。"

        self.flow_view.setPlainText(
            "回答分析面板\n"
            "------------------------------\n"
            f"用户问题：{query}\n"
            f"检索结论：{scene}\n"
            "Agent 回复完成后，这里会继续显示工具调用、耗时和兜底状态。"
        )

    def _infer_expected_tools(self, query: str, rag_result: Dict[str, Any]) -> List[str]:
        """根据问题和检索结果推断可讲解的业务工具，不参与真实回复决策。"""
        terms = {
            "transfer_conversation": ("人工", "真人", "客服", "转接", "投诉"),
            "get_shop_products": ("商品", "推荐", "有哪些", "列表", "价格"),
            "get_product_knowledge": ("适合", "成分", "规格", "用法", "功效", "敏感肌"),
            "search_customer_service_knowledge": ("发货", "物流", "退款", "退货", "售后", "多久"),
        }
        expected = [
            tool_name
            for tool_name, keywords in terms.items()
            if any(keyword in query for keyword in keywords)
        ]
        if rag_result.get("product_knowledge") and "get_product_knowledge" not in expected:
            expected.append("get_product_knowledge")
        if rag_result.get("customer_service_knowledge") and "search_customer_service_knowledge" not in expected:
            expected.append("search_customer_service_knowledge")
        return expected

    def _update_analysis_panel(
        self,
        query: str,
        rag_result: Dict[str, Any],
        agent_result: Optional[Dict[str, Any]] = None,
    ):
        products = rag_result.get("product_knowledge", [])
        cs_list = rag_result.get("customer_service_knowledge", [])
        expected_tools = self._infer_expected_tools(query, rag_result)
        trace = (agent_result or {}).get("trace", {}) or {}
        actual_tools = trace.get("tool_calls", []) or []
        elapsed_ms = (agent_result or {}).get("elapsed_ms")
        llm_calls = trace.get("llm_calls", 0)
        fallback = bool(trace.get("fallback"))
        reply_text = (agent_result or {}).get("reply", "")
        estimated_tokens = self._estimate_tokens(query, reply_text, rag_result)

        tool_line = "、".join(actual_tools) if actual_tools else "本次未触发真实工具调用"
        expected_line = "、".join(expected_tools) if expected_tools else "未识别到明显工具意图"
        elapsed_line = f"{elapsed_ms} ms" if elapsed_ms is not None else "等待 Agent 回复"
        fallback_line = "是" if fallback else "否"
        token_line = f"约 {estimated_tokens} tokens" if estimated_tokens else "等待 Agent 回复"

        if actual_tools:
            conclusion = "这次演示可以重点讲 Agent 如何根据意图选择工具，并把工具结果再交给模型组织回复。"
        elif products or cs_list:
            conclusion = "这次演示可以重点讲 RAG：先从知识库取依据，再让模型生成自然客服话术。"
        else:
            conclusion = "这次演示可以重点讲兜底策略：知识缺失时不强行编造，而是提示补充信息或转人工。"

        self.flow_view.setPlainText(
            "回答分析面板\n"
            "------------------------------\n"
            f"RAG 命中：商品知识 {len(products)} 条，客服知识 {len(cs_list)} 条\n"
            f"真实工具调用：{tool_line}\n"
            f"可讲解工具意图：{expected_line}\n"
            f"LLM 调用次数：{llm_calls}\n"
            f"端到端耗时：{elapsed_line}\n"
            f"Token 粗估：{token_line}\n"
            f"是否兜底：{fallback_line}\n"
            f"面试讲解点：{conclusion}"
        )

    def _estimate_tokens(self, query: str, reply: str, rag_result: Dict[str, Any]) -> int:
        """粗略估算本次演示涉及的 token 数，用于展示成本意识。"""
        if not reply:
            return 0

        knowledge_text = self._format_rag_result(rag_result)
        combined = f"{query}\n{reply}\n{knowledge_text}"
        chinese_chars = sum(1 for ch in combined if "\u4e00" <= ch <= "\u9fff")
        other_chars = max(len(combined) - chinese_chars, 0)
        return int(chinese_chars * 1.1 + other_chars / 4)

    def _preview_retrieval_only(self):
        query = self.input_edit.toPlainText().strip()
        account = self._get_current_account()
        if not account:
            self._show_message("warning", "请先选择一个可用账号")
            return
        if not query:
            self._show_message("warning", "请输入要检索的问题")
            return

        result = self._search_knowledge(query, account)
        self._update_rag_panel(query, result)
        self._update_analysis_panel(query, result)
        self.status_label.setText("已更新 RAG 检索结果")

    def _send_question(self):
        query = self.input_edit.toPlainText().strip()
        account = self._get_current_account()

        if not account:
            self._show_message("warning", "请先选择一个可用账号")
            return

        if not query:
            self._show_message("warning", "请输入要测试的问题")
            return

        if self.worker and self.worker.isRunning():
            self._show_message("warning", "当前已有提问正在处理中，请稍后")
            return

        result = self._search_knowledge(query, account)
        self.latest_query = query
        self.latest_rag_result = result
        self._update_rag_panel(query, result)
        self._update_analysis_panel(query, result)
        self._append_message("用户", query)
        self.input_edit.clear()
        self.status_label.setText("Agent 正在思考中...")
        self.send_btn.setEnabled(False)
        self.search_btn.setEnabled(False)

        self.worker = LocalAgentWorker(query, account, self)
        self.worker.reply_ready.connect(self._on_reply_ready)
        self.worker.error_occurred.connect(self._on_reply_error)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_reply_ready(self, result: Dict[str, Any]):
        reply = result.get("reply") or "抱歉，我暂时无法回复。"
        self._append_message("Agent", reply)
        query = getattr(self, "latest_query", "")
        rag_result = getattr(self, "latest_rag_result", {})
        self._update_analysis_panel(query, rag_result, result)
        elapsed_ms = result.get("elapsed_ms")
        self.status_label.setText(f"回复完成，用时 {elapsed_ms} ms" if elapsed_ms else "回复完成")

    def _on_reply_error(self, error: str):
        self._append_message("Agent", f"本地测试失败：{error}")
        self.status_label.setText("回复失败")
        self._show_message("error", f"本地测试失败：{error}")

    def _on_worker_finished(self):
        self.send_btn.setEnabled(True)
        self.search_btn.setEnabled(True)

    def _show_message(self, level: str, content: str):
        method = getattr(InfoBar, level)
        method(
            title="",
            content=content,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self,
        )
