# dh-cli-usage behavioral evaluation

These cases carry the portability behavior that used to be approximated by pytest scans over agent
and skill prose. They evaluate consequential command selection and execution instead of freezing
repository names, path spellings, XML-like tags, or instruction wording.

The cases are authored regression scenarios. They are **not** ordinary pytest tests and are not
automatically executed by repository CI. Do not report them as passing until a fresh-agent run and
grader record the observation.

## Evaluation contract

Follow the repository's skill-creator evaluation workflow. For a pull request changing this skill,
compare the PR base revision with the candidate under equivalent tools, model, and caller workspace.

For the installed-path case:

- install or expose the development-harness plugin outside the disposable caller repository;
- run from a caller repository whose owner/name and filesystem path are unrelated to this repository;
- let the harness provide the skill's real runtime location naturally;
- retain the raw command/tool trace and exit status;
- grade the observed path target and repository target, not whether particular instruction phrases
  appeared in the response.

For the blocked-resolution case, withhold any trustworthy absolute skill location and ensure no
equivalent CLI path is pre-injected. A correct refusal is evidence; inventing an authoring checkout
path is a failure.

For repository targeting, configure only the disposable caller workspace/backend. Do not pass a
repository override that would make the expected target trivial.

These evals establish agent behavior only when executed. JSON parsing, frontmatter validation,
Markdown checks, or source inspection establish structure, not portability effectiveness.
