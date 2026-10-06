"""Resume this release without replacing published releases or assets."""


def deploy(invoke):
    inspection = invoke("inspect")
    if inspection.get("push_permission") is False:
        raise RuntimeError("The configured GitHub account has no push permission for this repository")
    invoke("push")
    metadata = invoke("resume" if inspection.get("release_exists") else "draft")
    if metadata["draft"]:
        invoke("upload")
        invoke("publish")
    return invoke("verify")
