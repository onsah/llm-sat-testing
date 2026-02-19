from dataclasses import dataclass
import json
from typing import Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from cnfgen import CNF


@dataclass
class SATResult:
    satisfiable: bool
    assignment: Optional[list[bool]]
    reasoning_content: Any

    @staticmethod
    def parse(content: str, reasoning_content: Any) -> SATResult:
        js = json.loads(content)
        satisfiable = bool(js["satisfiable"])
        if satisfiable:
            assignment: list[bool] = []
            for val in js["assignment"]:
                assignment.append(bool(val))
            return SATResult(True, assignment, reasoning_content)
        else:
            return SATResult(False, None, reasoning_content)


class LLM:
    client: OpenAI
    model: str

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    _system_prompt = """
    The user will give a CNF in dimacs format. Determine if it's satisfiable or not WITHOUT USING ANY EXTERNAL TOOLS. Use your own reasoning by writing down the assignment steps while you are working. If you think formula is satisfiable, ensure that by checking every clause. After determining the result output a JSON with two fields:
    - satisfiable: Boolean. True if the formula is satisfiable
    - assignment: Array of booleans. If the formula is satisfiable provide an assignment for each variable from 1 to N. If the formula is not satisfiable this field is null.

    EXAMPLE INPUT: 
    p cnf 10 10
    -7 9 10 0
    7 8 9 0
    -7 -9 10 0
    -2 3 5 0
    -4 -6 -8 0
    -1 3 -5 0
    1 -3 -8 0
    4 -5 -10 0
    4 -7 -8 0
    -2 -5 8 0

    EXAMPLE JSON OUTPUT:
    {
        "satisfiable": true,
        "assignment": [false, false, false, false, false, false, false, false, false, false]
    }
    """

    def solve(self, cnf: CNF) -> SATResult:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": LLM._system_prompt},
            {"role": "user", "content": cnf.to_dimacs()},
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    # Must be removed when model is Chatgpt5.2
                    # "name": "sat_result",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "satisfiable": {
                                "type": "bool",
                                "description": "Whether the formula is satisfiable or not",
                            },
                            "assignment": {
                                "type": "array",
                                "items": {"type": "boolean"},
                                "required": False,
                                "description": "Assignment for each variable from 1 to N. Null if not satisfiable",
                            },
                        },
                        "required": ["satisfiable"],
                        "additionalProperties": False,
                    },
                },
            },
            extra_body={
                "reasoning": {"enabled": True, "max_tokens": 100000},
            },
        )

        print(response)
        message = response.choices[0].message
        message_content = message.content
        assert message_content is not None
        # reasoning_content = message.reasoning_content
        # assert isinstance(reasoning_content, str)

        result = SATResult.parse(message_content, message.reasoning)
        return result
