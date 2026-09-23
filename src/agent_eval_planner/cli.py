"""Command-line interface for agent-eval-planner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import generate, validate_suite
from .errors import Error
from .models import PlannerResult
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for generate mode."""
    parser = argparse.ArgumentParser(
        prog="agent-eval-planner",
        description="Gera plano de eval, suite JSONL e remediações a partir do contrato de um agente.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Usage:\n"
            "  agent-eval-planner [options] <contract.md|prompt.txt|agent.json>\n"
            "  agent-eval-planner validate [options] <suite.jsonl>"
        ),
    )
    parser.add_argument("input", nargs="?", help="Caminho do contrato do agente")
    parser.add_argument("-t", "--team", help="Nome do time no título")
    parser.add_argument("-a", "--agent", dest="agent_name", help="Nome do target_agent")
    parser.add_argument("--tools", help="Tools conhecidas (vírgula)")
    parser.add_argument("--scope", dest="declared_scope", help="Escopo declarado (resumo)")
    parser.add_argument("--out-of-scope", dest="out_of_scope", help="Fora de escopo declarado")
    parser.add_argument(
        "--harness",
        default="generic",
        help="Harness alvo (generic|marketing-copilot)",
    )
    parser.add_argument("-o", "--output", help="Arquivo .md/.jsonl ou diretório de saída")
    parser.add_argument("--plan-only", action="store_true", help="Gerar apenas o plano")
    parser.add_argument("--suite-only", action="store_true", help="Gerar apenas a suite JSONL")
    parser.add_argument(
        "--remediations-only",
        action="store_true",
        help="Gerar apenas remediações",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"agent_eval_planner {__version__}",
    )
    return parser


def build_validate_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for validate mode."""
    parser = argparse.ArgumentParser(
        prog="agent-eval-planner validate",
        description="Valida uma suite JSONL (hard-fail em forbidden_tools vazios / placeholders).",
    )
    parser.add_argument("suite", nargs="?", help="Caminho da suite.jsonl")
    parser.add_argument(
        "--known-tools",
        help="Tools reais (vírgula)",
    )
    parser.add_argument(
        "--agent-has-no-tools",
        action="store_true",
        help="Agente sem tools",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI execution method."""
    args_list = list(argv) if argv is not None else sys.argv[1:]
    if args_list and args_list[0] == "validate":
        return _run_validate(args_list[1:])
    return _run_generate(args_list)


def _run_generate(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.input:
        parser.print_help(sys.stderr)
        return 1

    tools = None
    if args.tools:
        tools = [part.strip() for part in args.tools.split(",") if part.strip()]

    try:
        result = generate(
            input_path=args.input,
            team=args.team,
            agent_name=args.agent_name,
            tools=tools,
            declared_scope=args.declared_scope,
            out_of_scope=args.out_of_scope,
            harness=args.harness,
        )
        _write_outputs(result, args)
        return 0
    except Error as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


def _looks_like_directory(path: str) -> bool:
    candidate = Path(path)
    return candidate.is_dir() or path.endswith("/") or candidate.suffix == ""


def _select_single(result: PlannerResult, args: argparse.Namespace) -> str | None:
    if args.suite_only:
        return result.suite
    if args.remediations_only:
        return result.remediations
    if args.plan_only:
        return result.plan
    return None


def _write_bundle(directory: Path, result: PlannerResult, args: argparse.Namespace) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if not args.suite_only and not args.remediations_only:
        plan_path = directory / "plano-de-acao-agent-eval.md"
        plan_path.write_text(result.plan, encoding="utf-8")
        print(f"Plano gerado em {plan_path}", file=sys.stderr)
    if not args.plan_only and not args.remediations_only:
        suite_path = directory / "suite.jsonl"
        suite_path.write_text(result.suite, encoding="utf-8")
        print(f"Suite gerada em {suite_path}", file=sys.stderr)
    if args.plan_only or args.suite_only:
        return
    rem_path = directory / "remediacoes.md"
    rem_path.write_text(result.remediations, encoding="utf-8")
    print(f"Remediações geradas em {rem_path}", file=sys.stderr)


def _emit_stdout(result: PlannerResult, args: argparse.Namespace) -> None:
    if args.suite_only:
        sys.stdout.write(result.suite)
    elif args.remediations_only:
        sys.stdout.write(result.remediations)
    elif args.plan_only:
        sys.stdout.write(result.plan)
    else:
        sys.stdout.write(result.plan)
        print("\n# --- suite.jsonl ---\n", file=sys.stderr)
        sys.stdout.write(result.suite)
        print("\n# --- remediacoes.md ---\n", file=sys.stderr)
        sys.stdout.write(result.remediations)


def _write_outputs(result: PlannerResult, args: argparse.Namespace) -> None:
    if not args.output:
        _emit_stdout(result, args)
        return

    path = args.output
    if _looks_like_directory(path):
        _write_bundle(Path(path), result, args)
        return

    output = Path(path)
    if args.suite_only or output.suffix == ".jsonl":
        output.write_text(result.suite, encoding="utf-8")
        print(f"Suite gerada em {path}", file=sys.stderr)
        return

    content = _select_single(result, args) or result.plan
    output.write_text(content, encoding="utf-8")
    print(f"Artefato gerado em {path}", file=sys.stderr)


def _run_validate(argv: list[str]) -> int:
    parser = build_validate_parser()
    args = parser.parse_args(argv)
    if not args.suite:
        parser.print_help(sys.stderr)
        return 1

    known_tools: list[str] = []
    if args.known_tools:
        known_tools = [part.strip() for part in args.known_tools.split(",") if part.strip()]

    try:
        errors = validate_suite(
            args.suite,
            known_tools=known_tools,
            agent_has_no_tools=args.agent_has_no_tools,
        )
    except Error as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"INVALID: {args.suite} ({len(errors)} error(s))", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: {args.suite}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
