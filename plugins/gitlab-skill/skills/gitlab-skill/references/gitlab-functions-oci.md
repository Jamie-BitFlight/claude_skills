# GitLab Functions OCI Loading and Publication

Load functions from OCI or the file system. OCI is the recommended distribution method. Relative
file references resolve from the calling function directory, or `CI_PROJECT_DIR` when called
directly by a job. Git repository loading is deprecated and planned for removal.

```yaml
- name: echo
  func: registry.gitlab.com/example/functions/echo:1
```

The built-ins `builtin://function/oci/build` and `builtin://function/oci/publish` create and publish
`function-image.tar`:

```yaml
build_function:
  artifacts:
    paths: [function-image.tar]
  run:
    - name: build
      func: builtin://function/oci/build
      inputs:
        version: "1.2.3"
        common:
          files:
            func.yml: func.yml

publish_function:
  needs: [build_function]
  run:
    - name: publish
      func: builtin://function/oci/publish
      inputs:
        archive: function-image.tar
        to_repository: registry.example.com/my-org/my-function
```

Authenticate before private-registry publication. The documented Docker Auth function exports
`DOCKER_AUTH_CONFIG`. Stable releases update applicable semantic-version and `latest` tags;
prereleases create only the exact prerelease tag.

Completion criterion: the OCI archive exists, publication succeeds to the selected repository, and
the expected stable or prerelease tags resolve.

SOURCE: <https://docs.gitlab.com/ci/functions/#load-functions> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#build-and-publish-functions> (accessed 2026-09-21)
