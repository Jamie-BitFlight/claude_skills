#!/bin/sh
# Drive the DH work ledger's whole work loop through the `sam plan` CLI and nothing else.
#
# This is the cross-harness proof that a runner needs no MCP server, no Python import and no
# harness of its own: a plain POSIX shell and the documented commands are enough. Every command
# and flag used here is one `dh_core/ledger_spec.py` names; the only program run besides the CLI
# is `git rev-parse`, for the base commit `create --base-sha` records. The order they run in is the
# one `docs/work-ledger/work-loop.md` (orchestrator) and `docs/work-ledger/runner-contract.md`
# (runner) set out.
#
# The plan it drives is `tests_sam/fixtures/loop-plan/`: three tasks, T1 and T2 parallel and T3
# dependent on both. T3's first attempt leaves its second acceptance criterion unmet, so the judge
# sends it back with `reclaim --response` (work-loop.md row J2) and a second attempt finishes it.
#
# Run it by hand:
#
#     sh plugins/development-harness/tests_sam/scripted_runner.sh
#
# It writes nothing outside a temporary directory: DH_STATE_HOME points at one, so the ledger it
# builds is its own. Set SCRIPTED_RUNNER_WORK_DIR to keep that directory for inspection. Set
# CLAUDE_PLUGIN_ROOT to run against a plugin checkout other than this script's own.
#
# Any command that exits non-zero stops the script with the command, its exit status and both of
# its streams. Every refusal and no-op code the ledger prints is unexpected here: this script
# walks the path where nothing refuses.

set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT:-$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)}
CLI_PATH=$PLUGIN_ROOT/sam_schema/cli.py
FIXTURE_DIR=$SCRIPT_DIR/fixtures/loop-plan

LEASE_TTL_SECONDS=900
RETURN_TEXT='STATUS: DONE'
COMPLETION_REPORT='Completion Report'
VERIFICATION_RESULTS='Verification Results'
RESPONSE_SECTION='Orchestrator Response'
SEND_BACK_MARKER='SEND-BACK-MARKER'

PLAN=''
ATTEMPT=''
BASE_SHA=''
SAM_OUT=''
SAM_STATUS=0

# ---------------------------------------------------------------------------
# Failing loudly, and the two things worth reading off a command's output
# ---------------------------------------------------------------------------

fail() {
    printf 'scripted-runner: %s\n' "$1" >&2
    exit 1
}

expect_contains() {
    # $1 what was expected, $2 the text that must appear, $3 the output to look in.
    case $3 in
        *"$2"*) ;;
        *) fail "$1: expected '$2' in: $3" ;;
    esac
}

expect_absent() {
    # $1 what was expected, $2 the text that must not appear, $3 the output to look in.
    case $3 in
        *"$2"*) fail "$1: did not expect '$2' in: $3" ;;
        *) ;;
    esac
}

expect_equal() {
    # $1 what was expected, $2 the expected value, $3 the value read.
    if [ "$2" != "$3" ]; then
        fail "$1: expected '$2', read '$3'"
    fi
}

fixture() {
    # Print one fixture file, which is a task field, a report section or a send-back response.
    if [ ! -f "$FIXTURE_DIR/$1" ]; then
        fail "the loop-plan fixture has no $1"
    fi
    cat "$FIXTURE_DIR/$1"
}

# ---------------------------------------------------------------------------
# The one way this script reaches the ledger
# ---------------------------------------------------------------------------

sam() {
    # Run one `sam plan` command, leaving its stdout in SAM_OUT, and stop on any non-zero exit.
    printf '+ sam plan %s\n' "$*" >&2
    SAM_STATUS=0
    SAM_OUT=$(uv run "$CLI_PATH" plan "$@" 2>"$WORK_DIR/stderr") || SAM_STATUS=$?
    if [ "$SAM_STATUS" -ne 0 ]; then
        printf 'scripted-runner: sam plan %s exited %s\n' "$*" "$SAM_STATUS" >&2
        printf 'stdout: %s\n' "$SAM_OUT" >&2
        printf 'stderr: %s\n' "$(cat "$WORK_DIR/stderr")" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# The workspace: one temporary state root, so a hand run touches no real ledger
# ---------------------------------------------------------------------------

nearest_repository() {
    # Print the nearest ancestor of $1 holding a .git entry, so DH_STATE_HOME's slug resolves
    # without depending on the directory the script was started from.
    candidate=$1
    while [ "$candidate" != '/' ]; do
        if [ -e "$candidate/.git" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
        candidate=$(dirname -- "$candidate")
    done
    return 1
}

prepare_workspace() {
    if ! command -v uv >/dev/null 2>&1; then
        fail 'uv is not on PATH; it is how sam_schema/cli.py resolves its dependencies'
    fi
    if ! command -v git >/dev/null 2>&1; then
        fail 'git is not on PATH; the plan needs a base commit for --base-sha'
    fi
    if [ ! -f "$CLI_PATH" ]; then
        fail "no CLI at $CLI_PATH; set CLAUDE_PLUGIN_ROOT to the development-harness plugin"
    fi
    BASE_SHA=$(git -C "$PLUGIN_ROOT" rev-parse HEAD) ||
        fail "no commit at $PLUGIN_ROOT to diff reports against; set CLAUDE_PLUGIN_ROOT to a checkout"
    if [ -n "${SCRIPTED_RUNNER_WORK_DIR:-}" ]; then
        WORK_DIR=$SCRIPTED_RUNNER_WORK_DIR
        mkdir -p "$WORK_DIR"
    else
        WORK_DIR=$(mktemp -d)
        trap 'rm -rf "$WORK_DIR"' EXIT
    fi
    mkdir -p "$WORK_DIR/state" "$WORK_DIR/worktrees"
    DH_STATE_HOME=$WORK_DIR/state
    export DH_STATE_HOME
    if [ -z "${DH_PROJECT_ROOT:-}" ] && repository=$(nearest_repository "$SCRIPT_DIR"); then
        DH_PROJECT_ROOT=$repository
        export DH_PROJECT_ROOT
    fi
}

# ---------------------------------------------------------------------------
# The plan: three tasks, T3 behind T1 and T2
# ---------------------------------------------------------------------------

build_plan() {
    # --base-sha records the commit the judge diffs a report against, and it is also what tells
    # `create` to write the ledger: with no ledger-only flag `create` writes a content record, the
    # store this repository's plans are moving off. Every later command names the plan, and a plan
    # the ledger holds keeps them there.
    sam create --slug "$(fixture slug.txt)" --goal "$(fixture goal.txt)" \
        --owner-reference 'work-ledger scripted runner' --base-sha "$BASE_SHA"
    PLAN=$(printf '%s' "$SAM_OUT" | sed -n 's/.*"plan":"\([^"]*\)".*/\1/p')
    if [ -z "$PLAN" ]; then
        fail "create printed no plan id: $SAM_OUT"
    fi
    for task in T1 T2 T3; do
        sam append-task --plan-address "$PLAN" --task-id "$task" \
            --task-title "$(fixture "tasks/$task/title.txt")"
        sam update --plan-address "$PLAN" --task-id "$task" \
            --set "acceptance_criteria=$(fixture "tasks/$task/acceptance-criteria.md")" \
            --set "verification_steps=$(fixture "tasks/$task/verification-steps.md")"
        if [ -f "$FIXTURE_DIR/tasks/$task/dependencies.json" ]; then
            sam update --plan-address "$PLAN" --task-id "$task" \
                --set "dependencies=$(fixture "tasks/$task/dependencies.json")"
        fi
    done
    sam finalize --plan-address "$PLAN"
    expect_contains 'finalize makes the plan ready' '"state":"ready"' "$SAM_OUT"
    sam validate --plan-address "$PLAN"
    expect_equal 'validate finds nothing structural' '[]' "$SAM_OUT"
}

# ---------------------------------------------------------------------------
# The orchestrator's commands: dispatch, settle, accept, reclaim
# ---------------------------------------------------------------------------

dispatch_task() {
    # Open an attempt on $1 and leave the attempt number dispatch printed in ATTEMPT.
    mkdir -p "$WORK_DIR/worktrees/$1"
    sam dispatch --address "$PLAN/$1" --ttl "$LEASE_TTL_SECONDS" \
        --worktree "$WORK_DIR/worktrees/$1"
    ATTEMPT=$SAM_OUT
    if [ -z "$ATTEMPT" ]; then
        fail "dispatch of $1 printed no attempt number"
    fi
}

settle_task() {
    # Record what the launch of $1's attempt $2 returned.
    sam settle --address "$PLAN/$1" --attempt "$2" --return-text "$RETURN_TEXT"
    expect_contains "settle records $1 attempt $2" '"task.settled"' "$SAM_OUT"
}

accept_task() {
    # Judge row J1 for $1: every criterion met, every verification step passed.
    sam accept --address "$PLAN/$1" --note "$2"
    expect_contains "accept records $1" '"task.accepted"' "$SAM_OUT"
}

# ---------------------------------------------------------------------------
# The runner's commands: read, renew, the two report sections, finish
# ---------------------------------------------------------------------------

runner_attempt() {
    # Work $1's attempt $2 the way runner-contract.md sets out. $3, when given, is a phrase the
    # orchestrator's response must carry into the first read of a sent-back attempt.
    task=$1
    attempt=$2
    marker=${3:-}
    sam read --address "$PLAN/$task" --attempt "$attempt"
    expect_contains "read gives $task its own row" "\"task\":\"$task\"" "$SAM_OUT"
    expect_contains "read finds $task in-progress" '"status":"in-progress"' "$SAM_OUT"
    if [ -n "$marker" ]; then
        expect_contains "read heads $task with the orchestrator's response" \
            "\"name\":\"$RESPONSE_SECTION\"" "$SAM_OUT"
        expect_contains "the response the judge sent reaches the next runner" "$marker" "$SAM_OUT"
    fi
    sam renew --address "$PLAN/$task" --attempt "$attempt"
    expect_contains "renew prints the new deadline for $task" '"renew_by":' "$SAM_OUT"
    append_report_section "$task" "$attempt" "$COMPLETION_REPORT" completion-report.md
    append_report_section "$task" "$attempt" "$VERIFICATION_RESULTS" verification-results.md
    sam finish --address "$PLAN/$task" --attempt "$attempt" --result complete
    expect_contains "finish completes $task" '"status":"complete"' "$SAM_OUT"
}

append_report_section() {
    # Append section $3 of $1's attempt $2 from the fixture file $4.
    sam update --plan-address "$PLAN" --task-id "$1" --attempt "$2" \
        --append-section "$3" \
        --section-content "$(fixture "reports/$1/attempt-$2/$4")"
    expect_contains "update appends $3 to $1" '"task.section"' "$SAM_OUT"
}

# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

first_wave() {
    # T1 and T2 have no dependencies, so one `ready` lists both and withholds T3.
    sam ready --plan-address "$PLAN"
    expect_contains 'the first wave holds two tasks' '"count":2' "$SAM_OUT"
    expect_contains 'the first wave lists T1' '"id":"T1"' "$SAM_OUT"
    expect_contains 'the first wave lists T2' '"id":"T2"' "$SAM_OUT"
    expect_absent 'the first wave withholds the dependent task' '"id":"T3"' "$SAM_OUT"
    for task in T1 T2; do
        dispatch_task "$task"
        expect_equal "the first attempt of $task" '1' "$ATTEMPT"
        runner_attempt "$task" "$ATTEMPT"
        settle_task "$task" "$ATTEMPT"
        accept_task "$task" 'every criterion met'
    done
}

second_wave() {
    # Accepting T1 and T2 satisfies T3's dependencies, so T3 becomes the whole next wave.
    sam ready --plan-address "$PLAN"
    expect_contains 'the second wave holds one task' '"count":1' "$SAM_OUT"
    expect_contains 'the second wave lists T3' '"id":"T3"' "$SAM_OUT"
    dispatch_task T3
    expect_equal 'the first attempt of T3' '1' "$ATTEMPT"
    runner_attempt T3 1
    settle_task T3 1
}

send_back() {
    # Judge row J2: T3 finished complete with its second acceptance criterion unmet.
    sam reclaim --address "$PLAN/T3" --reason judge --response "$(fixture responses/T3/attempt-2.md)"
    expect_contains 'reclaim returns T3 to not-started' '"status":"not-started"' "$SAM_OUT"
    sam ready --plan-address "$PLAN"
    expect_contains 'the send-back makes T3 ready again' '"id":"T3"' "$SAM_OUT"
    dispatch_task T3
    expect_equal 'the second attempt of T3' '2' "$ATTEMPT"
    runner_attempt T3 2 "$SEND_BACK_MARKER"
    settle_task T3 2
    accept_task T3 'the empty manifest now renders'
}

main() {
    prepare_workspace
    build_plan
    first_wave
    second_wave
    send_back
    sam status --plan-address "$PLAN"
    expect_contains 'the plan reports progress done' '"progress":"done"' "$SAM_OUT"
    printf 'scripted-runner: plan %s reached progress done\n' "$PLAN"
}

main "$@"
