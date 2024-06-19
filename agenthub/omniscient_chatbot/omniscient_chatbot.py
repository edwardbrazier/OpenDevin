from opendevin.controller.agent import Agent
from opendevin.controller.state.state import State
from opendevin.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    MessageAction,
)
from opendevin.llm.llm import LLM


class OmniscientChatbot(Agent):
    VERSION = '0.1'
    """
    The Omniscient Chatbot is an agent which answers questions about the codebase. Its distinctive capability is that it can pass a whole codebase to the AI model.
    """

    system_message: str = '(no system message)\n'
    in_context_example: str = '(no in-context example)\n'

    def __init__(self, llm: LLM) -> None:
        """
        Initializes a new instance of the class.

        Parameters:
        - llm (LLM): The llm to be used by this agent
        """
        super().__init__(llm)
        self.reset()

    def reset(self) -> None:
        """
        Resets the agent's state.
        """
        super().reset()

    def step(self, state: State) -> Action:
        """
        Performs one step using this agent.
        The step consists of loading a codebase and answering the question about it.

        Requires:
        - The input field of the state parameter must include data in this form. (example)
        {
            'codebase_path': './opendevin',
            'file_extensions': ['py', 'md'],
            'question': 'How does the instruction get from the delegating agent to the Omniscient Chatbot?'
        }

        Parameters:
        - state (State): used to get the conversation history

        Returns:
        - AgentFinishAction() - End the interaction without providing any new information
        - MessageAction(content) - Response to a question
        """

        # First of all, we need to know whether this the delegator agent
        # has only just now delegated to this agent, or whether
        # this agent produced the last action.
        if len(state.history) > 0 and not (
            isinstance(state.history[-1], AgentDelegateAction)
        ):
            # This agent produced the last action.
            # It only produces one action at a time, so it's finished.
            return AgentFinishAction()

        messages: list[dict[str, str]] = [
            {'role': 'system', 'content': self.system_message},
            {'role': 'user', 'content': self.in_context_example},
        ]

        # Get the instructions from the delegating agent.
        # TODO
        # The data is in state.input.

        # Dummy message for testing
        messages += [
            {
                'role': 'user',
                'content': 'Say that the codebase is boring.',
            }
        ]

        response = self.llm.do_completion(
            messages=messages,
            stop=[],
            temperature=0.0,
        )
        state.num_of_chars += sum(
            len(message['content']) for message in messages
        ) + len(response.choices[0].message.content)

        # Get the string from the response
        if response.choices == []:
            return AgentFinishAction()

        response_string: str = response.choices[0].message.content
        answer: str = response_string

        return MessageAction(answer)

    def search_memory(self, query: str) -> list[str]:
        raise NotImplementedError('Implement this abstract method')
