import logging
from typing import Optional

from pydantic import Field

from actions.base import ActionConfig, ActionConnector
from inputs.base import Message

class ConsoleConnectorConfig(ActionConfig):
    """
    Configuration for Console output (Text).
    """
    prefix: str = Field(default="BOT:", description="Prefix for the output message")


class ConsoleConnector(ActionConnector[ConsoleConnectorConfig, Message]):
    """
    Connector that prints the LLM response to the console.
    """

    def __init__(self, config: ConsoleConnectorConfig):
        super().__init__(config)
        self.prefix = self.config.prefix
        logging.info(">>> Console Connector Ready: I will print answers here <<<")

    async def connect(self, output_interface: Message) -> None:
        """
        Received a message from LLM, print it out.
        """

        if isinstance(output_interface, Message):
            text = output_interface.message
        elif hasattr(output_interface, 'action'):
            text = output_interface.action
        else:
            text = str(output_interface)

        print(f"\n\033[92m{self.prefix} {text}\033[0m\n")
