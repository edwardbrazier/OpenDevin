import re

from opendevin.controller.action_parser import ActionParser, ResponseParser
from opendevin.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    CmdRunAction,
    IPythonRunCellAction,
    MessageAction,
)


class VantagePointResponseParser(ResponseParser):
    """
    VantagePointResponseParser is responsible for parsing the responses from the VantagePointAgent.

    This parser interprets the responses and converts them into actionable items that the agent can execute.
    It extends the functionality of the base ResponseParser to handle specific actions related to the VantagePointAgent.

    The supported actions are:
        - CmdRunAction(command) - bash command to run
        - IPythonRunCellAction(code) - IPython code to run
        - AgentDelegateAction(agent, inputs) - delegate action for (sub)task
        - MessageAction(content) - Message action to run (e.g. ask for clarification)
        - AgentFinishAction() - end the interaction

    The parser works by first parsing the response string to extract the specific action, and then creating the corresponding Action object.
    """

    def __init__(
        self,
    ):
        # Need pay attention to the item order in self.action_parsers
        self.action_parsers = [
            VantagePointActionParserFinish(),
            VantagePointActionParserCmdRun(),
            VantagePointActionParserIPythonRunCell(),
            VantagePointActionParserAgentDelegate(),
        ]
        self.default_parser = VantagePointActionParserMessage()

    def parse(self, response: str) -> Action:
        action_str = self.parse_response(response)
        return self.parse_action(action_str)

    def parse_response(self, response) -> str:
        action = response.choices[0].message.content
        for lang in ['bash', 'ipython', 'browse']:
            if f'<execute_{lang}>' in action and f'</execute_{lang}>' not in action:
                action += f'</execute_{lang}>'
        return action

    def parse_action(self, action_str: str) -> Action:
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)


class VantagePointActionParserFinish(ActionParser):
    """
    Actions that this parser can generate:
        - AgentFinishAction() - end the interaction

    This parser checks if the action string contains the <finish> tag, and if so, it extracts the thought from the action string and returns an AgentFinishAction.
    """

    def __init__(
        self,
    ):
        self.finish_command = None

    def check_condition(self, action_str: str) -> bool:
        self.finish_command = re.search(r'<finish>.*</finish>', action_str, re.DOTALL)
        return self.finish_command is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.finish_command is not None
        ), 'self.finish_command should not be None when parse is called'
        thought = action_str.replace(self.finish_command.group(0), '').strip()
        return AgentFinishAction(thought=thought)


class VantagePointActionParserCmdRun(ActionParser):
    """
    Actions that this parser can generate:
        - CmdRunAction(command) - bash command to run
        - AgentFinishAction() - end the interaction
    """

    def __init__(
        self,
    ):
        self.bash_command = None

    def check_condition(self, action_str: str) -> bool:
        self.bash_command = re.search(
            r'<execute_bash>(.*?)</execute_bash>', action_str, re.DOTALL
        )
        return self.bash_command is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.bash_command is not None
        ), 'self.bash_command should not be None when parse is called'
        thought = action_str.replace(self.bash_command.group(0), '').strip()
        # a command was found
        command_group = self.bash_command.group(1).strip()
        if command_group.strip() == 'exit':
            return AgentFinishAction()
        return CmdRunAction(command=command_group, thought=thought)


class VantagePointActionParserIPythonRunCell(ActionParser):
    """
    Actions that this parser can generate:
        - IPythonRunCellAction(code) - IPython code to run
    """

    def __init__(
        self,
    ):
        self.python_code = None
        self.jupyter_kernel_init_code: str = 'from agentskills import *'

    def check_condition(self, action_str: str) -> bool:
        self.python_code = re.search(
            r'<execute_ipython>(.*?)</execute_ipython>', action_str, re.DOTALL
        )
        return self.python_code is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.python_code is not None
        ), 'self.python_code should not be None when parse is called'
        code_group = self.python_code.group(1).strip()
        thought = action_str.replace(self.python_code.group(0), '').strip()
        return IPythonRunCellAction(
            code=code_group,
            thought=thought,
            kernel_init_code=self.jupyter_kernel_init_code,
        )


class VantagePointActionParserAgentDelegate(ActionParser):
    """
    Actions that this parser can generate:
        - AgentDelegateAction(agent, inputs) - delegate action for (sub)task

    This parser object is stateful.
    """

    def __init__(
        self,
    ):
        self.agent_delegate = None

    def check_condition(self, action_str: str) -> bool:
        self.agent_delegate = re.search(
            r'<ask_omniscient_chatbot>(.*)</ask_omniscient_chatbot>',
            action_str,
            re.DOTALL,
        )
        return self.agent_delegate is not None

    def parse(self, action_str: str) -> Action:
        """
        Assumes that check_conditions has been called previously on the same input string.
        """
        assert (
            self.agent_delegate is not None
        ), 'self.agent_delegate should not be None when parse is called'
        # Extract the thought from the action string by removing the whole command.
        # Assumes that everything outside of those xml tags is thought.
        thought = action_str.replace(self.agent_delegate.group(0), '').strip()
        # Everything between the xml tags is for the action.
        question_to_ask = self.agent_delegate.group(1).strip()
        task = (
            f'{thought}. My question for the Omniscient Chatbot is: {question_to_ask}'
        )
        return AgentDelegateAction(agent='OmniscientChatbot', inputs={'task': task})


class VantagePointActionParserMessage(ActionParser):
    """
    Actions that this parser can generate:
        - MessageAction(content) - Message action to run (e.g. ask for clarification)
    """

    def __init__(
        self,
    ):
        pass

    def check_condition(self, action_str: str) -> bool:
        # We assume the LLM is GOOD enough that when it returns pure natural language
        # it wants to talk to the user
        return True

    def parse(self, action_str: str) -> Action:
        return MessageAction(content=action_str, wait_for_response=True)
