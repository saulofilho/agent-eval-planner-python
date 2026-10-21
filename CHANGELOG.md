# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.2.0] - 2026-10-21

### Adicionado
- `--harness rd-copilot` emite a linha nativa (`target_component`, `turns`, `suite=regression`, `metadata.vector_id`) que o harness do rd-copilot carrega.
- O validador aceita essa forma e a linha legada do marketing-copilot: `--bound-tools`, `--schema`, `--target-components`, e aviso quando `forbidden_tools` cita tool do catálogo que o alvo não chama.

## [0.1.0] - 2026-09-23

### Adicionado
- Versão Python equivalente à gem Ruby `agent_eval_planner`.
- Pipeline: contrato do agente → plano Markdown, suite JSONL e remediações.
- CLI `agent-eval-planner` com generate, validate e as mesmas flags da gem.
- Catálogo de vetores SCOPE / INJECT / ROLE / PII / TOOL / HALLUC / EXFIL.
- Suíte de testes com `unittest`.
- Empacotamento moderno baseado em `pyproject.toml` (PEP 517/518/621).
