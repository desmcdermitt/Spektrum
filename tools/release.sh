#!/usr/bin/env bash
#
# Release driver for Spektrum.  Prose version: docs/maintenance/index.rst
#
# A release is two events separated by a code review, so this is two commands:
#
#   ./tools/release.sh prepare <major|minor|patch>
#       Cuts prep_for_release from the canonical master, refuses until the
#       release notes for the new version exist, bumps the version, and runs
#       both suites and lint.  Leaves the commit to you.
#
#   ./tools/release.sh publish
#       Run once that PR has merged.  Tags the merge commit on the canonical
#       master and pushes the tag there.  Pushing that tag is the only thing
#       that publishes to PyPI.
#
#   ./tools/release.sh status
#       What is released, what is tagged, and what has drifted.  Read-only.
#
# Every check below refuses rather than warns.  The two releases this script
# exists to prevent -- v1.2.2 and v1.3.0, neither of which reached PyPI -- were
# both produced by following the old documented process correctly.

set -euo pipefail

PACKAGE='Spektrum'
CANONICAL_SLUG='liquidweb/Spektrum'
NEXT_HEADING='Next Release'
NOTES='docs/release_notes/index.rst'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------- output ----

if [ -t 1 ]; then
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
else
    C_RED=''; C_GREEN=''; C_YELLOW=''; C_BOLD=''; C_OFF=''
fi

ok()   { printf '  %s✓%s %s\n' "$C_GREEN" "$C_OFF" "$1"; }
info() { printf '  %s·%s %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
head_() { printf '\n%s%s%s\n' "$C_BOLD" "$1" "$C_OFF"; }

# Refuse loudly, and always say what to do instead.  A check that only prints
# "failed" sends the reader back to the process they already got wrong.
# stderr, not stdout.  `canonical_remote` is called as `$(canonical_remote)`, and a
# refusal printed to stdout there is captured by the command substitution and never
# reaches the reader -- the script exits 1 in silence, which is the one thing every
# message here exists to avoid.
refuse() {
    printf '\n  %s✗ %s%s\n' "$C_RED" "$1" "$C_OFF" >&2
    shift
    local arg line
    for arg in "$@"; do
        while IFS= read -r line; do
            printf '    %s\n' "$line" >&2
        done <<<"$arg"
    done
    printf '\n' >&2
    exit 1
}

# ----------------------------------------------------------------- remote ----

# `origin` is a personal fork for both maintainers, and the fork is where the
# lost tags went.  Never assume a remote name -- find the one that actually
# points at the canonical repository, and refuse if it is ambiguous.
canonical_remote() {
    local found=()
    local remote url
    while read -r remote url _; do
        case "$url" in
            *"$CANONICAL_SLUG"*|*"${CANONICAL_SLUG%.git}.git"*) found+=("$remote") ;;
        esac
    done < <(git remote -v | awk '$3 == "(fetch)"')

    # De-duplicate, in case one remote is listed more than once.
    local uniq
    uniq="$(printf '%s\n' "${found[@]:-}" | sort -u | grep -v '^$' || true)"
    local count
    count="$(printf '%s' "$uniq" | grep -c . || true)"

    if [ "$count" -eq 0 ]; then
        refuse "No remote points at $CANONICAL_SLUG." \
               "This clone can only see forks, and a tag pushed to a fork never" \
               "reaches CI -- that is how v1.2.2 and v1.3.0 were lost.  Add it:" \
               "" \
               "  git remote add upstream git@github.com:$CANONICAL_SLUG.git"
    fi
    if [ "$count" -gt 1 ]; then
        refuse "More than one remote points at $CANONICAL_SLUG:" "$uniq" \
               "" "Remove the duplicate so there is no doubt where the tag goes."
    fi
    printf '%s' "$uniq"
}

# ---------------------------------------------------------------- helpers ----

# Deliberately not --tags.  A clone that has been through a failed release
# holds tags that disagree with the canonical repo's, and `git fetch --tags`
# exits non-zero on "would clobber existing tag" -- which under `set -e` kills
# the script at the first command, for a condition `status` is meant to report.
fetch_master() {  # fetch_master <remote>
    git fetch --quiet "$1" master || refuse \
        "Could not fetch master from $1." \
        "Check network access and that you can read $CANONICAL_SLUG."
}

remote_tag_sha() {  # remote_tag_sha <remote> <tag>
    git ls-remote --tags "$1" "refs/tags/$2" 2>/dev/null | awk '
        {
            name = $2
            if (sub(/\^\{\}$/, "", name)) { peeled = $1 }
            else { plain = $1 }
        }
        END { print (peeled != "" ? peeled : plain) }
    '
}

version_from() {  # version_from <git-ref>
    git show "$1:setup.py" | sed -n "s/^version = '\(.*\)'$/\1/p"
}

bumpversion_current_from() {  # bumpversion_current_from <git-ref>
    git show "$1:.bumpversion.cfg" | sed -n 's/^current_version = \(.*\)$/\1/p'
}

conf_version_from() {  # conf_version_from <git-ref>
    git show "$1:docs/conf.py" | sed -n "s/^version = '\(.*\)'$/\1/p"
}

notes_has_version() {  # notes_has_version <git-ref-or-WORKTREE> <version>
    if [ "$1" = 'WORKTREE' ]; then
        grep -qx "Release: $2" "$NOTES"
    else
        git show "$1:$NOTES" | grep -qx "Release: $2"
    fi
}

# Three answers, not two.  Treating an unreachable PyPI as "the version is free" would
# let `publish` tag and push having verified nothing -- a check that passes when it
# cannot run is worse than no check.
pypi_state() {  # pypi_state <version> -> published | absent | unknown
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 \
        "https://pypi.org/pypi/$PACKAGE/$1/json" 2>/dev/null || printf '000')"
    case "$code" in
        200) printf 'published' ;;
        404) printf 'absent' ;;
        *)   printf 'unknown' ;;
    esac
}

# Refuse on `unknown`; callers that legitimately tolerate it call pypi_state directly.
require_absent_from_pypi() {  # require_absent_from_pypi <version>
    case "$(pypi_state "$1")" in
        published)
            refuse "$PACKAGE $1 is already on PyPI." \
                   "PyPI never lets a version be reused, replaced or re-uploaded." ;;
        unknown)
            refuse "Could not reach PyPI to check whether $1 is already published." \
                   "Refusing rather than guessing -- publishing over an existing" \
                   "version is not recoverable.  Check the network and re-run." ;;
    esac
}

pypi_latest() {
    curl -sS --max-time 20 "https://pypi.org/pypi/$PACKAGE/json" 2>/dev/null \
        | python3 -c 'import json,sys
try:
    sys.stdout.write(json.load(sys.stdin)["info"]["version"])
except Exception:
    pass' 2>/dev/null
}

next_version() {  # next_version <current> <part>
    local cur="$1" part="$2"
    local major minor patch
    IFS=. read -r major minor patch <<<"$cur"
    case "$part" in
        major) printf '%s.0.0' "$((major + 1))" ;;
        minor) printf '%s.%s.0' "$major" "$((minor + 1))" ;;
        patch) printf '%s.%s.%s' "$major" "$minor" "$((patch + 1))" ;;
    esac
}

# The fork is whatever remote is not the canonical one.  A release branch is pushed
# there, never to the canonical repository -- the PR comes from a fork like every other.
fork_remote() {
    local canonical="$1" found=() r
    for r in $(git remote); do
        [ "$r" = "$canonical" ] || found+=("$r")
    done
    if [ "${#found[@]}" -eq 0 ]; then
        refuse "No remote to push a release branch to." \
               "Only $canonical is configured, and that is the canonical repository." \
               "Add your fork:" "" "  git remote add origin git@github.com:<you>/Spektrum.git"
    fi
    if [ "${#found[@]}" -gt 1 ]; then
        refuse "More than one remote could be your fork: ${found[*]}" \
               "Name it explicitly:  --fork <remote>"
    fi
    printf '%s' "${found[0]}"
}

remote_owner() {  # remote_owner <remote> -> github owner
    git remote get-url "$1" \
        | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##' \
        | cut -d/ -f1
}

# --- release notes -----------------------------------------------------------
# The notes are RST with a fixed shape, so they are edited with python rather than
# sed: getting a heading underline wrong silently breaks the published docs.

notes_next_count() {  # notes_next_count <file> -> number of entries under Next Release
    python3 - "$1" "$NEXT_HEADING" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
head = sys.argv[2]
m = re.search(r'^%s\n-+\n(.*?)(?=^Release: |\Z)' % re.escape(head), text, re.M | re.S)
print(len(re.findall(r'^ #\. ', m.group(1), re.M)) if m else -1)
PY
}

notes_rename_next() {  # notes_rename_next <file> <version>
    python3 - "$1" "$2" "$NEXT_HEADING" <<'PY'
import re, sys
path, version, head = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()

m = re.search(r'^(%s)\n(-+)\n' % re.escape(head), text, re.M)
if not m:
    sys.exit('no "%s" section in %s' % (head, path))

rule = m.group(2)
# Rename this section to the version, then open a fresh empty one above it.
text = text[:m.start()] + 'Release: %s\n%s\n' % (version, rule) + text[m.end():]

fresh = '%s\n%s\n\n*Nothing yet.*\n\n' % (head, rule)
insert = text.index('Release: %s\n' % version)
text = text[:insert] + fresh + text[insert:]

# The placeholder is a property of an empty section only.
text = re.sub(r'(^Release: %s\n-+\n\n)\*Nothing yet\.\*\n\n' % re.escape(version),
              r'\1', text, flags=re.M)
open(path, 'w').write(text)
PY
}

# setup.py, docs/conf.py and .bumpversion.cfg must agree before anything is bumped or
# tagged.  bumpversion aborts with a Python traceback when they do not -- and in `release`
# it would do so after the notes had already been rewritten, leaving a half-made release.
require_consistent_versions() {  # require_consistent_versions <git-ref> -> version
    local ref="$1" version cfg conf
    version="$(version_from "$ref")"
    cfg="$(bumpversion_current_from "$ref")"
    conf="$(conf_version_from "$ref")"

    [ -n "$version" ] || refuse "Could not read a version from $ref:setup.py."

    if [ "$version" != "$cfg" ] || [ "$version" != "$conf" ]; then
        refuse "Version files on $ref disagree." \
               "  setup.py         $version" \
               "  .bumpversion.cfg $cfg" \
               "  docs/conf.py     $conf" \
               "" "bumpversion cannot run against these.  Fix them in their own PR."
    fi
    printf '%s' "$version"
}

require_clean_tree() {
    if [ -n "$(git status --porcelain)" ]; then
        refuse "Working tree is not clean." \
               "Commit or stash first -- a release must be cut from a known tree." \
               "" "$(git status --short)"
    fi
}

# ---------------------------------------------------------------- release ----

cmd_release() {
    local part='' fork=''
    while [ $# -gt 0 ]; do
        case "$1" in
            major|minor|patch) part="$1"; shift ;;
            --fork) fork="${2:-}"; shift 2 ;;
            *) refuse "Unknown argument: $1" "Usage: tools/release.sh release <major|minor|patch> [--fork <remote>]" ;;
        esac
    done
    [ -n "$part" ] || refuse "Usage: tools/release.sh release <major|minor|patch>"

    local remote; remote="$(canonical_remote)"
    [ -n "$fork" ] || fork="$(fork_remote "$remote")"

    head_ "Releasing a $part version"
    info "canonical: $remote ($CANONICAL_SLUG)   fork: $fork"

    fetch_master "$remote"
    require_clean_tree

    local base_version new_version
    base_version="$(require_consistent_versions "$remote/master")"
    new_version="$(next_version "$base_version" "$part")"
    ok "$base_version -> $new_version"

    git rev-parse -q --verify "refs/tags/v$new_version" >/dev/null && refuse \
        "Tag v$new_version already exists locally." "" "  git tag -d v$new_version"
    require_absent_from_pypi "$new_version"
    ok "v$new_version is free, locally and on PyPI"

    local branch="v$base_version-to-v$new_version"
    if git rev-parse -q --verify "refs/heads/$branch" >/dev/null; then
        if [ -z "$(git log --oneline "$remote/master..$branch" 2>/dev/null)" ]; then
            # No commit on it: a previous attempt stopped before committing, most
            # likely on a failing suite.  Nothing is lost by starting over.
            refuse "Branch $branch exists but carries no commit." \
                   "A previous attempt stopped before committing.  Delete it and" \
                   "re-run:" "" "  git branch -D $branch"
        fi
        refuse "Branch $branch already has a release commit on it." \
               "That release is in progress.  Merge its PR, then:" \
               "" "  ./tools/release.sh publish"
    fi
    git checkout --quiet -b "$branch" "$remote/master"
    ok "cut $branch from $remote/master ($(git rev-parse --short HEAD))"

    head_ 'Verifying'
    local py="${PYTHON:-python}"
    command -v "$py" >/dev/null 2>&1 || refuse \
        "\`$py\` is not on PATH." "Activate the virtualenv, or set PYTHON=python3."
    "$py" -m pytest tests -q
    "$py" -m spektrum -s tests/live/
    "$py" -m flake8 spektrum tests && ok 'flake8 clean'

    local entries; entries="$(notes_next_count "$NOTES")"
    if [ "$entries" -lt 0 ]; then
        refuse "$NOTES has no '$NEXT_HEADING' section." \
               "Add one above the newest 'Release:' entry, with the same underline."
    fi
    if [ "$entries" -eq 0 ]; then
        refuse "'$NEXT_HEADING' is empty -- there is nothing to say about $new_version." \
               "Every merged change is supposed to add its own entry.  Add them now," \
               "then re-run.  Merged since v$base_version:" \
               "$(merged_since "$remote" "$base_version")"
    fi
    ok "$entries entr$([ "$entries" = 1 ] && echo y || echo ies) under $NEXT_HEADING"

    notes_rename_next "$NOTES" "$new_version"
    ok "$NEXT_HEADING -> Release: $new_version, and a fresh $NEXT_HEADING opened"

    command -v bumpversion >/dev/null 2>&1 || refuse \
        "bumpversion is not installed." "  pip install -r dev-requirements.txt"
    # --no-commit --no-tag on purpose: bumpversion's tag would land on this pre-merge
    # commit, which the merge then rewrites.  `publish` tags the merge commit instead.
    bumpversion --allow-dirty --no-commit --no-tag "$part"

    # The branch name, the notes heading and the commit subject were all built from
    # next_version's arithmetic; bumpversion is what actually writes the files. They
    # agree today for major/minor/patch, but a `parse`/`serialize` added to
    # .bumpversion.cfg later (pre-release tags, say) would silently make them disagree,
    # and the release would be named for one version and ship another.
    local wrote_setup wrote_conf wrote_cfg
    wrote_setup="$(sed -n "s/^version = '\(.*\)'\$/\1/p" setup.py)"
    wrote_conf="$(sed -n "s/^version = '\(.*\)'\$/\1/p" docs/conf.py)"
    wrote_cfg="$(sed -n 's/^current_version = //p' .bumpversion.cfg)"
    if [ "$wrote_setup" != "$new_version" ] || [ "$wrote_conf" != "$new_version" ] \
       || [ "$wrote_cfg" != "$new_version" ]; then
        refuse "bumpversion wrote a different version than this release is named for." \
               "  expected         $new_version" \
               "  setup.py         $wrote_setup" \
               "  docs/conf.py     $wrote_conf" \
               "  .bumpversion.cfg $wrote_cfg" \
               "" "Nothing is committed.  Delete the branch and check .bumpversion.cfg:" \
               "" "  git checkout - && git branch -D $branch"
    fi
    ok "version files -> $new_version"


    git add -- "$NOTES" setup.py docs/conf.py .bumpversion.cfg
    git commit --quiet -m "v$base_version -> v$new_version"
    ok "one commit: v$base_version -> v$new_version"

    git push --quiet "$fork" "$branch"
    ok "pushed $branch to $fork"

    command -v gh >/dev/null 2>&1 || refuse \
        "gh is not installed, so the PR was not opened." \
        "The branch is pushed.  Open it by hand:" "" \
        "  gh pr create --repo $CANONICAL_SLUG --base master \\" \
        "    --head $(remote_owner "$fork"):$branch --title 'v$base_version -> v$new_version'"

    local url
    if ! url="$(gh pr create --repo "$CANONICAL_SLUG" --base master \
            --head "$(remote_owner "$fork"):$branch" \
            --title "v$base_version -> v$new_version" \
            --body "Release $new_version.  Notes: \`$NOTES\`.

Opened by \`tools/release.sh release $part\`.  After merge, the release is
published by \`./tools/release.sh publish\`, which tags the merge commit." 2>&1)"; then
        refuse "gh could not open the PR:" "$url" \
               "The branch is pushed; open the PR by hand."
    fi
    ok "PR opened: $url"

    head_ 'Next'
    printf '  Merge it, then:  ./tools/release.sh publish\n\n'
}

merged_since() {  # merged_since <remote> <version>
    local sha; sha="$(remote_tag_sha "$1" "v$2")"
    if [ -n "$sha" ]; then
        git log --oneline "$sha..$1/master"
    else
        git log --oneline -12 "$1/master"
    fi
}

# ---------------------------------------------------------------- publish ----

cmd_publish() {
    local assume_yes=''
    [ "${1:-}" = '--yes' ] && assume_yes='1'

    local remote; remote="$(canonical_remote)"
    head_ 'Publishing'
    info "canonical remote: $remote ($CANONICAL_SLUG)"

    fetch_master "$remote"
    local sha short
    sha="$(git rev-parse "$remote/master")"
    short="$(git rev-parse --short "$remote/master")"
    ok "fetched $remote/master ($short)"

    # Everything is read from the remote ref, never from the local checkout.
    # What gets tagged is what is on the canonical master, regardless of the
    # state of this clone.
    local version
    version="$(require_consistent_versions "$remote/master")"
    ok "$remote/master is at $version, consistently"

    if ! notes_has_version "$remote/master" "$version"; then
        refuse "$NOTES on $remote/master has no section for $version." \
               "The prepare PR is incomplete.  Do not tag it."
    fi
    ok "release notes cover $version"

    require_absent_from_pypi "$version"
    ok "$version is not on PyPI yet"

    local tag="v$version"
    if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
        local existing; existing="$(git rev-parse "refs/tags/$tag^{commit}")"
        if [ "$existing" != "$sha" ]; then
            refuse "Local tag $tag points at $(git rev-parse --short "$existing"), not $short." \
                   "This is the exact failure that lost v1.2.2 and v1.3.0: a tag left" \
                   "on a pre-merge commit that never reached $CANONICAL_SLUG." \
                   "" "  git tag -d $tag" \
                   "" "then re-run.  The tag belongs on the merge commit."
        fi
    fi
    if git ls-remote --tags --exit-code "$remote" "refs/tags/$tag" >/dev/null 2>&1; then
        refuse "$remote already has tag $tag but PyPI has no $version." \
               "The tag build failed or never ran.  Check the build before" \
               "re-tagging -- deleting and re-pushing a tag is the last resort:" \
               "" "  https://app.travis-ci.com/github/$CANONICAL_SLUG/builds"
    fi
    ok "$tag is free, locally and on $remote"

    head_ 'About to publish'
    cat <<EOF
  tag       $tag
  commit    $short  $(git log -1 --format='%s' "$sha")
  push to   $remote ($CANONICAL_SLUG)

  Pushing this tag starts a Travis build that uploads $PACKAGE $version to
  PyPI.  PyPI versions cannot be reused or replaced.
EOF
    if [ -z "$assume_yes" ]; then
        [ -t 0 ] || refuse "Not a terminal; re-run with --yes if this is scripted."
        printf '\n  Type the version to confirm (%s): ' "$version"
        local answer; read -r answer
        [ "$answer" = "$version" ] || refuse 'Not confirmed, nothing pushed.'
    fi

    git tag -a "$tag" "$sha" -m "$tag"
    git push "$remote" "refs/tags/$tag"
    ok "pushed $tag to $remote"

    head_ 'Waiting for PyPI'
    info "build: https://app.travis-ci.com/github/$CANONICAL_SLUG/builds"
    local waited=0
    while [ "$waited" -lt 900 ]; do
        if [ "$(pypi_state "$version")" = 'published' ]; then
            ok "$PACKAGE $version is live: https://pypi.org/project/$PACKAGE/$version/"
            return 0
        fi
        sleep 30
        waited=$((waited + 30))
        info "still waiting (${waited}s)"
    done

    refuse "$version has not appeared on PyPI after 15 minutes." \
           "The tag is pushed, so the release is not lost -- the build is the" \
           "thing to look at.  A stale or revoked PYPI_TOKEN shows up here:" \
           "" "  https://app.travis-ci.com/github/$CANONICAL_SLUG/builds"
}

# ----------------------------------------------------------------- status ----

cmd_status() {
    local remote; remote="$(canonical_remote)"
    fetch_master "$remote"

    local version latest
    version="$(version_from "$remote/master")"
    latest="$(pypi_latest)"

    head_ 'Status'
    printf '  %-22s %s\n' 'PyPI latest'          "${latest:-unknown}"
    printf '  %-22s %s\n' "$remote/master"       "$version ($(git rev-parse --short "$remote/master"))"
    printf '  %-22s %s\n' 'canonical remote'     "$remote -> $CANONICAL_SLUG"

    local pending; pending="$(git show "$remote/master:$NOTES" 2>/dev/null \
        | { cat > /tmp/.spektrum_notes.$$; notes_next_count /tmp/.spektrum_notes.$$; \
            rm -f /tmp/.spektrum_notes.$$; })"
    if [ "${pending:-0}" -lt 0 ]; then
        printf '  %-22s %s\n' "$NEXT_HEADING" 'section missing'
    else
        printf '  %-22s %s entr%s waiting\n' "$NEXT_HEADING" "$pending" \
            "$([ "$pending" = 1 ] && echo y || echo ies)"
    fi

    if [ "$version" != "${latest:-}" ]; then
        printf '\n  %sUnreleased:%s %s is on master, PyPI has %s\n' \
            "$C_YELLOW" "$C_OFF" "$version" "${latest:-unknown}"
        if notes_has_version "$remote/master" "$version"; then
            printf '  Notes for %s are written -- ready to publish.\n' "$version"
        else
            printf '  Notes for %s are NOT written; master is bumped without them.\n' "$version"
        fi
    fi

    # Every tag is compared against the canonical repo, not just against local
    # history.  The two faults look identical in `git tag` output and are not
    # the same problem: a tag that was never pushed is a lost release, while a
    # tag that disagrees with the remote is a clone that will mislead whoever
    # reads it.  This is the check that would have caught v1.2.2 and v1.3.0.
    head_ 'Tag health'
    local remote_tags problems=0
    remote_tags="$(git ls-remote --tags "$remote" 2>/dev/null | awk '
        {
            name = $2
            sub(/^refs\/tags\//, "", name)
            peeled = sub(/\^\{\}$/, "", name)
            if (peeled || !(name in seen)) { seen[name] = $1 }
        }
        END { for (n in seen) print n, seen[n] }
    ' | sort -V)"

    local tag local_sha remote_sha
    while read -r tag; do
        [ -n "$tag" ] || continue
        local_sha="$(git rev-parse "refs/tags/$tag^{commit}")"
        remote_sha="$(printf '%s\n' "$remote_tags" | awk -v t="$tag" '$1 == t {print $2}')"

        if [ -z "$remote_sha" ]; then
            if git merge-base --is-ancestor "$local_sha" "$remote/master" 2>/dev/null; then
                printf '  %s%s%s never pushed to %s -- its commit is on master, so the\n' \
                    "$C_YELLOW" "$tag" "$C_OFF" "$remote"
                printf '         release was never triggered\n'
            else
                printf '  %s%s%s never pushed, and %s is not on master either --\n' \
                    "$C_RED" "$tag" "$C_OFF" "$(git rev-parse --short "$local_sha")"
                printf '         this release does not exist anywhere\n'
            fi
            problems=$((problems + 1))
        elif [ "$remote_sha" != "$local_sha" ]; then
            printf '  %s%s%s disagrees with %s: local %s, remote %s\n' \
                "$C_YELLOW" "$tag" "$C_OFF" "$remote" \
                "$(git rev-parse --short "$local_sha")" \
                "$(git rev-parse --short "$remote_sha" 2>/dev/null || printf '%s' "${remote_sha:0:7}")"
            problems=$((problems + 1))
        fi
    done < <(git tag --list 'v*' | sort -V)

    [ "$problems" -eq 0 ] && ok "all local tags agree with $remote"

    # The range is resolved from the remote's tag, never the local one.  A local
    # tag of the same name can point somewhere else entirely -- see above.
    head_ 'Merged since the last published release'
    local latest_sha=''
    [ -n "$latest" ] && latest_sha="$(printf '%s\n' "$remote_tags" \
        | awk -v t="v$latest" '$1 == t {print $2}')"

    if [ -n "$latest_sha" ]; then
        git log --oneline "$latest_sha..$remote/master" | sed 's/^/  /'
    else
        info "$remote has no tag v${latest:-?} to compare against"
    fi
    printf '\n'
}

# ------------------------------------------------------------ interactive ----

# Bare `tools/release.sh`.  Works out which state the repository is in rather than
# assuming you are at the beginning -- the interesting failures happen when you are not,
# and "merged but never tagged" is the one that lost v1.2.2 and v1.3.0.
cmd_interactive() {
    [ -t 0 ] || refuse "Not a terminal." \
        "Interactive mode needs a tty.  Use the subcommands when scripting:" \
        "" "  ./tools/release.sh status | release <part> | publish"

    local remote; remote="$(canonical_remote)"
    head_ "Spektrum release"
    info "canonical: $remote ($CANONICAL_SLUG)"
    fetch_master "$remote"

    local version; version="$(version_from "$remote/master")"
    [ -n "$version" ] || refuse "Could not read a version from $remote/master:setup.py."

    local state; state="$(pypi_state "$version")"
    [ "$state" = 'unknown' ] && refuse \
        "Could not reach PyPI." "Refusing rather than guessing what is published."

    # --- master claims a version PyPI has never seen --------------------------
    if [ "$state" = 'absent' ]; then
        if ! notes_has_version "$remote/master" "$version"; then
            refuse "$remote/master is at $version, which is not on PyPI, but $NOTES" \
                   "has no section for it.  The version was bumped without notes." \
                   "Fix that on a branch before releasing anything."
        fi
        head_ "$version is merged but was never tagged"
        cat <<EOF
  $remote/master  $version ($(git rev-parse --short "$remote/master"))
  PyPI            $(pypi_latest)

  The release was prepared and merged; the tag that publishes it was never
  pushed.  This is what happened to 1.2.2 and 1.3.0.
EOF
        printf '\n  Tag and publish %s now? [y/N] ' "$version"
        local go; read -r go
        case "$go" in
            [yY]*) printf '\n'; cmd_publish ;;
            *) printf '\n  Left as is.  When ready:  ./tools/release.sh publish\n\n' ;;
        esac
        return
    fi

    # --- master's version is published; is there anything new? ----------------
    local base_sha; base_sha="$(remote_tag_sha "$remote" "v$version")"
    local pending
    if [ -n "$base_sha" ]; then
        pending="$(git log --oneline "$base_sha..$remote/master")"
    else
        pending="$(git log --oneline -12 "$remote/master")"
    fi

    if [ -z "$pending" ]; then
        head_ 'Nothing to release'
        printf '  %s is the current version and it is published.\n' "$version"
        printf '  No commits have merged since.  Exiting.\n\n'
        return
    fi

    # --- is a release already in flight? --------------------------------------
    local fork; fork="$(fork_remote "$remote")"
    local inflight
    inflight="$(git ls-remote --heads "$fork" "refs/heads/v$version-to-v*" 2>/dev/null \
        | sed 's#.*refs/heads/##')"
    if [ -n "$inflight" ]; then
        head_ 'A release is already open'
        printf '  Branch %s is pushed to %s.\n' "$inflight" "$fork"
        printf '  Merge its PR, then re-run this command (or: ./tools/release.sh publish).\n\n'
        return
    fi

    head_ "Merged since v$version"
    printf '%s\n' "$pending" | sed 's/^/  /'

    local entries
    entries="$(git show "$remote/master:$NOTES" \
        | { cat > /tmp/.spektrum_notes.$$; notes_next_count /tmp/.spektrum_notes.$$; \
            rm -f /tmp/.spektrum_notes.$$; })"
    if [ "$entries" -le 0 ]; then
        refuse "'$NEXT_HEADING' in $NOTES is empty." \
               "Those commits merged without saying what changed.  Add an entry for" \
               "each, in a normal PR, then run this again."
    fi

    head_ "$NEXT_HEADING"
    printf '  %s entr%s ready to publish as the next version.\n' \
        "$entries" "$([ "$entries" = 1 ] && echo y || echo ies)"

    head_ 'Which version?'
    printf '  current  %s\n' "$version"
    printf '    patch  %s      minor  %s      major  %s\n\n' \
        "$(next_version "$version" patch)" \
        "$(next_version "$version" minor)" \
        "$(next_version "$version" major)"
    printf '  major, minor or patch (anything else cancels): '
    local part; read -r part
    case "$part" in
        major|minor|patch) ;;
        *) printf '\n  Cancelled, nothing changed.\n\n'; return ;;
    esac

    printf '\n'
    cmd_release "$part"

    printf '  Has the PR been merged? [y/N] '
    local merged; read -r merged
    case "$merged" in
        [yY]*)
            printf '\n'
            # The answer is not trusted: publish re-reads the version, the notes and
            # the version files from the canonical master and refuses if the bump is
            # not actually there.  A wrong answer costs a refusal, not a bad tag.
            cmd_publish
            ;;
        *)
            printf '\n  Fine.  Once it merges:  ./tools/release.sh publish\n\n'
            ;;
    esac
}

# ------------------------------------------------------------------- main ----

case "${1:-}" in
    ''|-i|--interactive) cmd_interactive ;;
    status)  shift; cmd_status "$@" ;;
    release) shift; cmd_release "$@" ;;
    publish) shift; cmd_publish "$@" ;;
    prepare)
        refuse "\`prepare\` was replaced by \`release\`." \
               "It writes the notes from the accumulated '$NEXT_HEADING' section," \
               "opens the PR, and leaves tagging to \`publish\`:" \
               "" "  ./tools/release.sh release <major|minor|patch>"
        ;;
    -h|--help|help)
        cat <<EOF
Usage: tools/release.sh [command]

  (no arguments)                  interactive: work out what is needed, do it
  status                          what is released, tagged and drifted
  release <major|minor|patch>     notes + bump + one commit + PR, for review
  publish                         tag the merged master and push it (publishes)

Full process: docs/maintenance/index.rst
EOF
        ;;
    *)
        refuse "Unknown command: $1" "Try:  ./tools/release.sh --help"
        ;;
esac
