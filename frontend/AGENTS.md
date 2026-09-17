# Frontend Engineering Instructions

Follow the repository-level `AGENTS.md` in addition to these frontend rules.

## Structure

- Organize user-facing behavior by feature, not by generic component type.
- Keep API access in `src/api/` and shared generated or hand-written contracts
  in `src/types/`.
- Keep reusable visual primitives separate from feature components.
- Components render UI; hooks coordinate stateful behavior; API modules perform
  network communication.
- Do not duplicate backend workflow or validation logic in the client.

## TypeScript and React

- Enable and respect strict TypeScript settings.
- Avoid `any`; validate unknown server and user input at boundaries.
- Keep components small, accessible, and free of unrelated data logic.
- Prefer derived state over synchronized duplicate state.
- Handle loading, empty, error, clarification, running, and completed states.
- Clean up subscriptions, timers, and requests.
- Do not expose secrets or provider credentials in browser code.

## Testing

- Test behavior visible to the user rather than component internals.
- Mock the API boundary, not individual implementation details.
- Include keyboard and accessibility assertions for interactive features.
- Add an end-to-end test for the primary upload, question, clarification, and
  result flow once those features exist.

