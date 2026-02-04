from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


VERSION_PATTERN = re.compile(
    r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>(alpha|beta))\.(?P<pre_num>\d+))?$"
)


class ReleaseError(Exception):
    """Custom error for release failures."""


class GitHubAPIError(ReleaseError):
    def __init__(self, method: str, path: str, exit_code: int, message: str) -> None:
        super().__init__(
            f"GitHub API {method} {path} failed (exit {exit_code}): {message}"
        )
        self.method = method
        self.path = path
        self.exit_code = exit_code
        self.message = message


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: Optional[Tuple[str, int]] = None

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = VERSION_PATTERN.match(value)
        if not match:
            raise ReleaseError(
                "Invalid version format. Expected vX.Y.Z with optional -alpha.N or -beta.N"
            )

        prerelease: Optional[Tuple[str, int]] = None
        pre = match.group("pre")
        pre_num = match.group("pre_num")
        if pre and pre_num:
            prerelease = (pre, int(pre_num))

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=prerelease,
        )

    @classmethod
    def parse_optional(cls, value: str) -> Optional["SemVer"]:
        try:
            return cls.parse(value)
        except ReleaseError:
            return None

    def without_prerelease(self) -> "SemVer":
        return SemVer(self.major, self.minor, self.patch)

    def bump_minor(self) -> "SemVer":
        return SemVer(self.major, self.minor + 1, 0)

    def is_alpha(self) -> bool:
        return self.prerelease is not None and self.prerelease[0] == "alpha"

    def is_stable(self) -> bool:
        return self.prerelease is None

    def tag(self) -> str:
        return f"v{self.version_string()}"

    def version_string(self) -> str:
        suffix = ""
        if self.prerelease:
            suffix = f"-{self.prerelease[0]}.{self.prerelease[1]}"
        return f"{self.major}.{self.minor}.{self.patch}{suffix}"


def run_gh_api_json(
    path: str,
    method: str = "GET",
    params: Optional[Dict[str, str]] = None,
    input_body: Any = None,
) -> Any:
    cmd = ["gh", "api", "--method", method, path]
    if params:
        for key, value in params.items():
            if value is None:
                continue
            cmd.extend(["-f", f"{key}={value}"])

    input_text: Optional[str] = None
    if input_body is not None:
        cmd.extend(["--input", "-"])
        input_text = json.dumps(input_body)

    result = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise GitHubAPIError(method, path, result.returncode, message)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError(
            f"Failed to parse GitHub API response for {path}: {exc}"
        ) from exc


def list_repo_tags(repo: str) -> List[Dict[str, Any]]:
    tags: List[Dict[str, Any]] = []
    page = 1
    while True:
        data = run_gh_api_json(
            f"repos/{repo}/tags",
            params={
                "per_page": "100",
                "page": str(page),
            },
        )
        if not isinstance(data, list):
            raise ReleaseError("Unexpected response when listing tags.")
        if not data:
            break
        tags.extend(data)
        page += 1
    return tags


def parse_tags(tags: List[Dict[str, Any]]) -> List[SemVer]:
    parsed: List[SemVer] = []
    for tag in tags:
        name = tag.get("name")
        if not isinstance(name, str):
            continue
        semver = SemVer.parse_optional(name)
        if semver:
            parsed.append(semver)
    return parsed


def select_latest_stable(versions: List[SemVer]) -> SemVer:
    stable_versions = [v for v in versions if v.is_stable()]
    if not stable_versions:
        raise ReleaseError("No valid stable tags found.")
    return max(stable_versions, key=lambda v: (v.major, v.minor, v.patch))


def compute_next_version(mode: str, args: argparse.Namespace, repo: str) -> SemVer:
    if mode == "emergency":
        return SemVer.parse(args.emergency_version_override)

    if mode == "promote_alpha":
        alpha_version = SemVer.parse(args.promote_alpha)
        if not alpha_version.is_alpha():
            raise ReleaseError(
                "--promote-alpha requires an alpha version (vX.Y.Z-alpha.N)"
            )
        return alpha_version.without_prerelease()

    tags = list_repo_tags(repo)
    parsed = parse_tags(tags)
    if not parsed:
        raise ReleaseError("No tags matched the expected version pattern.")

    latest_stable = select_latest_stable(parsed)
    if mode == "publish_release":
        return latest_stable.bump_minor()

    if mode == "publish_alpha":
        target = latest_stable.bump_minor()
        alphas = [
            v
            for v in parsed
            if v.is_alpha()
            and (v.major, v.minor, v.patch)
            == (target.major, target.minor, target.patch)
        ]
        max_alpha = max((a.prerelease[1] for a in alphas), default=0)
        return SemVer(
            target.major, target.minor, target.patch, ("alpha", max_alpha + 1)
        )

    raise ReleaseError("Unknown mode requested.")


def get_branch_head(repo: str, branch: str) -> Tuple[str, str]:
    ref = run_gh_api_json(f"repos/{repo}/git/ref/heads/{branch}")
    commit_sha = ref.get("object", {}).get("sha")
    if not commit_sha:
        raise ReleaseError(f"Unable to resolve branch {branch} head.")
    commit = run_gh_api_json(f"repos/{repo}/git/commits/{commit_sha}")
    tree_sha = commit.get("tree", {}).get("sha")
    if not tree_sha:
        raise ReleaseError(f"Unable to resolve tree for commit {commit_sha}.")
    return commit_sha, tree_sha


def resolve_tag_to_commit(repo: str, tag: str) -> str:
    ref = run_gh_api_json(f"repos/{repo}/git/ref/tags/{tag}")
    obj = ref.get("object")
    if not obj:
        raise ReleaseError(f"Tag {tag} did not resolve to an object.")

    obj_type = obj.get("type")
    obj_sha = obj.get("sha")
    if not obj_type or not obj_sha:
        raise ReleaseError(f"Tag {tag} is missing type/sha information.")

    while obj_type == "tag":
        tag_obj = run_gh_api_json(f"repos/{repo}/git/tags/{obj_sha}")
        obj = tag_obj.get("object")
        if not obj:
            raise ReleaseError(
                f"Annotated tag {tag} is missing nested object information."
            )
        obj_type = obj.get("type")
        obj_sha = obj.get("sha")
        if not obj_type or not obj_sha:
            raise ReleaseError(f"Annotated tag {tag} is missing nested type/sha.")

    if obj_type != "commit":
        raise ReleaseError(f"Tag {tag} does not point to a commit (found {obj_type}).")
    return obj_sha


def find_merge_base(repo: str, commit_sha: str, branch: str) -> str:
    comparison = run_gh_api_json(f"repos/{repo}/compare/{commit_sha}...{branch}")
    merge_base = comparison.get("merge_base_commit", {}).get("sha")
    if not merge_base:
        raise ReleaseError(
            f"Unable to determine merge base between {commit_sha} and {branch}."
        )
    return merge_base


def get_commit_tree(repo: str, commit_sha: str) -> str:
    commit = run_gh_api_json(f"repos/{repo}/git/commits/{commit_sha}")
    tree_sha = commit.get("tree", {}).get("sha")
    if not tree_sha:
        raise ReleaseError(f"Unable to resolve tree for commit {commit_sha}.")
    return tree_sha


def fetch_file_at_ref(repo: str, path: str, ref: str) -> str:
    content = run_gh_api_json(f"repos/{repo}/contents/{path}", params={"ref": ref})
    encoding = content.get("encoding")
    encoded_data = content.get("content")
    if encoding != "base64" or not isinstance(encoded_data, str):
        raise ReleaseError(f"Unexpected encoding for {path} at {ref}.")
    try:
        return base64.b64decode(encoded_data).decode()
    except Exception as exc:  # noqa: BLE001
        raise ReleaseError(f"Failed to decode {path} at {ref}: {exc}") from exc


def update_version_in_content(content: str, new_version: SemVer) -> str:
    pattern = re.compile(
        r'^(?P<prefix>\s*(?:version|__version__)\s*=\s*)"(?P<value>.*?)"',
        flags=re.MULTILINE,
    )
    replacement = rf'\g<prefix>"{new_version.version_string()}"'
    updated, count = pattern.subn(replacement, content)
    if count != 1:
        raise ReleaseError(
            f"Expected to update exactly one version line, but replaced {count} occurrences."
        )
    return updated


def create_blob(repo: str, content: str) -> str:
    payload = {
        "content": base64.b64encode(content.encode()).decode(),
        "encoding": "base64",
    }
    blob = run_gh_api_json(f"repos/{repo}/git/blobs", method="POST", input_body=payload)
    sha = blob.get("sha")
    if not sha:
        raise ReleaseError("Blob creation did not return a sha.")
    return sha


def create_tree(repo: str, base_tree: str, path: str, blob_sha: str) -> str:
    payload = {
        "base_tree": base_tree,
        "tree": [
            {
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            }
        ],
    }
    tree = run_gh_api_json(f"repos/{repo}/git/trees", method="POST", input_body=payload)
    sha = tree.get("sha")
    if not sha:
        raise ReleaseError("Tree creation did not return a sha.")
    return sha


def create_commit(repo: str, message: str, tree_sha: str, parent_sha: str) -> str:
    payload = {"message": message, "tree": tree_sha, "parents": [parent_sha]}
    commit = run_gh_api_json(
        f"repos/{repo}/git/commits", method="POST", input_body=payload
    )
    sha = commit.get("sha")
    if not sha:
        raise ReleaseError("Commit creation did not return a sha.")
    return sha


def create_tag(repo: str, tag_name: str, message: str, object_sha: str) -> str:
    payload = {
        "tag": tag_name,
        "message": message,
        "object": object_sha,
        "type": "commit",
    }
    tag = run_gh_api_json(f"repos/{repo}/git/tags", method="POST", input_body=payload)
    sha = tag.get("sha")
    if not sha:
        raise ReleaseError("Tag creation did not return a sha.")
    return sha


def create_tag_ref(repo: str, tag_name: str, sha: str) -> None:
    payload = {
        "ref": f"refs/tags/{tag_name}",
        "sha": sha,
    }
    run_gh_api_json(f"repos/{repo}/git/refs", method="POST", input_body=payload)


def determine_mode(args: argparse.Namespace) -> str:
    if args.publish_release:
        return "publish_release"
    if args.publish_alpha:
        return "publish_alpha"
    if args.promote_alpha:
        return "promote_alpha"
    if args.emergency_version_override:
        return "emergency"
    raise ReleaseError("No mode selected.")


def configure_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage release versions and GitHub tagging."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--publish-release", action="store_true", help="Publish next stable release."
    )
    group.add_argument(
        "--publish-alpha", action="store_true", help="Publish next alpha release."
    )
    group.add_argument(
        "--promote-alpha",
        metavar="SEMVER",
        help="Promote an existing alpha tag to stable (format vX.Y.Z-alpha.N).",
    )
    group.add_argument(
        "--emergency-version-override",
        metavar="SEMVER",
        help="Force a specific version (format vX.Y.Z[-alpha.N|-beta.N]).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Compute changes without writing."
    )
    parser.add_argument(
        "--repo",
        help="Repository in owner/name form. Defaults to RELEASE_REPO environment variable.",
    )
    parser.add_argument(
        "--branch",
        help="Target branch (default: main or RELEASE_BRANCH env var).",
    )
    parser.add_argument(
        "--version-file",
        help="Version file path (default: pyproject.toml or RELEASE_VERSION_FILE env var).",
    )
    parser.add_argument(
        "--commit-template",
        help="Commit message template (default: Release {version} or RELEASE_COMMIT_TEMPLATE).",
    )
    parser.add_argument(
        "--tag-template",
        help="Tag message template (default: Release {version} or RELEASE_TAG_TEMPLATE).",
    )
    return parser


def resolve_config(args: argparse.Namespace) -> Dict[str, str]:
    repo = args.repo or os.environ.get("RELEASE_REPO")
    if not repo:
        raise ReleaseError(
            "Repository is not configured. Set RELEASE_REPO or pass --repo."
        )

    branch = args.branch or os.environ.get("RELEASE_BRANCH") or "main"
    version_file = (
        args.version_file or os.environ.get("RELEASE_VERSION_FILE") or "pyproject.toml"
    )
    commit_template = (
        args.commit_template
        or os.environ.get("RELEASE_COMMIT_TEMPLATE")
        or "Release {version}"
    )
    tag_template = (
        args.tag_template
        or os.environ.get("RELEASE_TAG_TEMPLATE")
        or "Release {version}"
    )

    return {
        "repo": repo,
        "branch": branch,
        "version_file": version_file,
        "commit_template": commit_template,
        "tag_template": tag_template,
    }


def main() -> int:
    parser = configure_arg_parser()
    args = parser.parse_args()

    try:
        mode = determine_mode(args)
        config = resolve_config(args)
        repo = config["repo"]
        branch = config["branch"]
        version_file = config["version_file"]
        commit_template = config["commit_template"]
        tag_template = config["tag_template"]

        target_version = compute_next_version(mode, args, repo)
        print(f"Determined next version: {target_version.tag()} (mode: {mode})")

        if mode == "promote_alpha":
            alpha_tag = SemVer.parse(args.promote_alpha).tag()
            alpha_commit = resolve_tag_to_commit(repo, alpha_tag)
            base_commit_sha = find_merge_base(repo, alpha_commit, branch)
            print(f"Resolved alpha tag {alpha_tag} to commit {alpha_commit}")
            print(f"Merge base with {branch}: {base_commit_sha}")
        else:
            base_commit_sha, base_tree_sha = get_branch_head(repo, branch)
            print(f"Base commit from {branch}: {base_commit_sha}")

        if mode == "promote_alpha":
            base_tree_sha = get_commit_tree(repo, base_commit_sha)

        file_content = fetch_file_at_ref(repo, version_file, base_commit_sha)
        updated_content = update_version_in_content(file_content, target_version)
        no_version_change = updated_content == file_content
        if no_version_change:
            print(
                f"{version_file} already at {target_version.version_string()}; tagging base commit."
            )
        else:
            print(f"Updated {version_file} version line")

        if args.dry_run:
            print(f"version={target_version.tag()}")
            print(f"base_commit={base_commit_sha}")
            if no_version_change:
                print("tag_target=base_commit")
            else:
                print("tag_target=new_commit")
            return 0

        if no_version_change:
            commit_sha = base_commit_sha
        else:
            blob_sha = create_blob(repo, updated_content)
            print(f"Created blob {blob_sha}")

            tree_sha = create_tree(repo, base_tree_sha, version_file, blob_sha)
            print(f"Created tree {tree_sha}")

            commit_message = commit_template.format(version=target_version.tag())
            commit_sha = create_commit(repo, commit_message, tree_sha, base_commit_sha)
            print(f"Created commit {commit_sha}")

        tag_message = tag_template.format(version=target_version.tag())
        tag_sha = create_tag(repo, target_version.tag(), tag_message, commit_sha)
        print(f"Created tag {target_version.tag()} with sha {tag_sha}")

        create_tag_ref(repo, target_version.tag(), tag_sha)
        print(f"Created tag ref refs/tags/{target_version.tag()}")

        print(f"version={target_version.tag()}")
        print(f"commit_sha={commit_sha}")
        print(f"tag_sha={tag_sha}")

        return 0
    except ReleaseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
