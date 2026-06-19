# Agent Notes

- Goal: keep controller updates easy for teachers. Prefer copy-pasteable,
  boring workflows over new tooling.
- Use Python stdlib only unless the user asks otherwise.
- Treat `updater.py` as generated output. Change `emit_updater_script.py`, then
  regenerate `updater.py`.
- Keep generated writer code controller-friendly: no dependencies, clear errors,
  and conservative Python syntax.
- Do not commit assistant/tool state such as `.serena/`.

