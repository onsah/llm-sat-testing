import argparse
from dataclasses import dataclass
import os
import sys
import cnfgen

from llm import LLM


@dataclass
class Args:
    formula_path: str
    api_base_url: str
    api_key: str
    model: str


def get_args() -> Args:
    parser = argparse.ArgumentParser(
        prog="llm-sat-bench",
        description="Benchmark LLMs using SAT problems",
        epilog="Gives an LLM n SAT problems and outputs the ratio of formulas verified",
    )

    parser.add_argument(
        "--formula",
        help="Path to the formula in DIMACS format"
    )

    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("API_BASE_URL"),
        help="OpenAI compatible API base URL.",
    )

    parser.add_argument(
        "--api-key", default=os.environ.get("API_KEY"), help="API key of the model"
    )

    parser.add_argument(
        "--model", default="deepseek/deepseek-v3.2", help="LLM model from OpenRouter"
    )

    args = parser.parse_args()

    return Args(
        args.formula,
        args.api_base_url,
        args.api_key,
        args.model,
    )


def generate_cnf(satisfiable: bool) -> cnfgen.CNF:
    if not satisfiable:
        # Generate until found a SAT one
        while True:
            cnf = cnfgen.RandomKCNF(5, 10, 200)
            if not cnf.solve()[0]:
                return cnf
    else:
        # Generate until found a SAT one
        while True:
            cnf = cnfgen.RandomKCNF(5, 10, 200)
            if cnf.solve()[0]:
                return cnf
            
def parse_dimacs(dimacs: str) -> cnfgen.CNF:
    cnf = cnfgen.CNF()

    # add clauses
    for line in dimacs.split("\n")[1:]:
        clause: list[int] = []
        for ass in line.split(" ")[:-1]:
            clause.append(int(ass))
        if len(clause) > 0:
            cnf.add_clause(clause)
    
    return cnf
        
def read_cnf(path: str) -> cnfgen.CNF:
    with open(path) as formula_file:
        return parse_dimacs(formula_file.read())


def main():
    args = get_args()

    llm = LLM(
        api_key=args.api_key,
        base_url=args.api_base_url,
        model=args.model
    )

    cnf = read_cnf(args.formula_path)

    print("Formula:")
    print(cnf.to_dimacs())

    result = llm.solve(cnf)

    print("LLM reasoning:")
    print(result.reasoning_content)

    print("LLM result:")
    print(result.satisfiable)

    print("LLM assignment:")
    print(result.assignment)

    is_success = result.satisfiable == cnf.is_satisfiable()

    if is_success and cnf.is_satisfiable():
        assert isinstance(result.assignment, list)
        # Add the assignment to the CNF
        for i in range(1, len(result.assignment) + 1):
            cnf.add_clause([i if result.assignment[i - 1] else -i])
        # Check if assignment is still SAT
        if not cnf.is_satisfiable():
            print("Assignment failed!")
            is_success = False

    if is_success:
        print("LLM predicted correctly")
    else:
        print("LLM mispredicted")

    sys.stdout.flush()


main()
