import asyncio
import logging
import threading
import time
from queue import Empty, Queue
from typing import Optional

from pydantic import Field

from inputs.base import Message, SensorConfig
from inputs.base.loop import FuserInput
from providers.io_provider import IOProvider
from providers.teleops_conversation_provider import TeleopsConversationProvider


class Esp32ControlConfig(SensorConfig):
    api_key: Optional[str] = Field(default=None, description="API Key")


class Esp32Control(FuserInput[Esp32ControlConfig, Optional[str]]):
    def __init__(self, config: Esp32ControlConfig):
        super().__init__(config)
        self.running = True
        self.messages: list[str] = []
        self.descriptor_for_LLM = "User"
        self.io_provider = IOProvider()
        self.message_buffer: Queue[str] = Queue()

        api_key = self.config.api_key
        self.conversation_provider = TeleopsConversationProvider(api_key=api_key)

        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()

        logging.info(">>> ESP32 Control Ready: Type command for robot <<<")

    def _input_loop(self):
        while self.running:
            try:
                user_input = input()
                if user_input.strip():
                    self.message_buffer.put(user_input)
                    print(f"DEBUG: Input received: {user_input}")
            except EOFError:
                break
            except Exception as e:
                logging.error(f"Input error: {e}")
                break

    async def _poll(self) -> Optional[str]:
        await asyncio.sleep(0.1)
        try:
            message = self.message_buffer.get_nowait()
            return message
        except Empty:
            return None

    async def _raw_to_text(self, raw_input: Optional[str]) -> Optional[Message]:
        if raw_input is None:
            return None
        return Message(timestamp=time.time(), message=raw_input)

    async def raw_to_text(self, raw_input: Optional[str]):
        pending_message = await self._raw_to_text(raw_input)
        if pending_message is not None:
            if len(self.messages) == 0:
                self.messages.append(pending_message.message)
            else:
                self.messages[-1] = f"{self.messages[-1]} {pending_message.message}"

    def formatted_latest_buffer(self) -> Optional[str]:
        if len(self.messages) == 0:
            return None

        current_msg = self.messages[-1]
        result = f"User Command: {current_msg}"

        self.io_provider.add_input(self.descriptor_for_LLM, current_msg, time.time())
        self.conversation_provider.store_user_message(current_msg)
        self.messages = []
        return result

    def stop(self):
        self.running = False
