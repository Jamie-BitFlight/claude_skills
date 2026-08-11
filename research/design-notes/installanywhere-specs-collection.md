---
name: InstallAnywhere Specification Collection Process
description: 'Given a Windows-targeted InstallAnywhere installer (`.exe`), produce a complete understanding of its internal structure such that we can:'
metadata:
  topic: installanywhere-specs-collection
  category: installer-tools
  source_url: https://github.com/installanywhere-specs-collection
  version: "InstallAnywhere 2025 R2"
  verified: "2026-02-19"
  next_review: "2026-05-19"
---

## 1. Objective

Given a Windows-targeted InstallAnywhere installer (`.exe`), produce a complete
understanding of its internal structure such that we can:

1. Extract the application payload
2. Reconstruct the installation sequence on Linux
3. Configure LaunchAnywhere (`.lax`) files for a Linux JVM
4. Handle silent/unattended installation via response files
5. Resolve platform-specific rules and conditions

---

## 2. Primary Documentation Sources

### 2.1 Official Revenera Documentation (Verified 2026-02-19)

| Source | URL | Status |
|--------|-----|--------|
| Docs Portal | `https://docs.revenera.com/` | Verified |
| IA 2025 R2 Help Library | `https://docs.revenera.com/installanywhere/Default.htm` | Verified |
| IA 2025 R2 User Guide PDF | `https://docs.revenera.com/installanywhere/pdf/InstallAnywhere2025R2UserGuide.pdf` | Downloaded to `/tmp/ia_userguide.pdf` (8.7MB) |
| IA 2025 R2 Release Notes | `https://docs.revenera.com/installanywhere/rn/Default.htm` | Verified |
| Sitemap (full URL index) | `https://docs.revenera.com/installanywhere/Sitemap.xml` | Verified |
| Revenera Community Forums | `https://community.revenera.com` | Unverified |

### 2.2 Key Documentation Pages

All under `https://docs.revenera.com/installanywhere/Content/helplibrary/`:

**File Formats & Manifests:**

| Page | Topic | Collection Status |
|------|-------|-------------------|
| `ia_ref_files_and_file_formats.htm` | All file formats index | Pending |
| `ia_manifest_files.htm` | Manifest file structure | Pending |
| `ia_project_file.htm` | Project file format (`.iap_xml`) | Pending |
| `ia_ref_laxprop.htm` | LAX properties reference | Pending |
| `ia_ref_variables_lax_properties.htm` | LAX properties as variables | Pending |
| `ia_ref_files_response_files.htm` | Response files reference | Pending |
| `ia_install_log_file_formats.htm` | Install log formats | Pending |
| `ia_ref_BuildPropXML.htm` | Build properties XML | Pending |
| `ia_ref_BuildPropXML_AD.htm` | Build properties XML (Advanced Designer) | Pending |

**LaunchAnywhere & JVM:**

| Page | Topic | Collection Status |
|------|-------|-------------------|
| `ia_LaunchAnywhere.htm` | LaunchAnywhere overview | Pending |
| `ia_CreateLauncherJava.htm` | Creating Java launchers | Pending |
| `ia_customizing_indv_launcher_settings.htm` | Customizing launcher settings | Pending |
| `ia_launcher_selects_vm.htm` | How launcher selects a VM | Pending |
| `ia_launchers_vm_selection.htm` | Launchers VM selection | Pending |
| `ia_ref_command_line_launcher.htm` | Launcher CLI arguments | Pending |
| `ia_ref_actions_LAXJava.htm` | LAX Java actions reference | Pending |
| `AdvJREHandling.htm` | Advanced JRE handling | Pending |
| `ia_controlling_vm_used_to_run_installer.htm` | Controlling installer VM | Pending |
| `ia_controlling_vm_launchers_use.htm` | Controlling launcher VM | Pending |
| `ia_controlling_install_of_bundled_vm.htm` | Bundled VM install control | Pending |
| `ia_vm_changing_bundled_vm_folder.htm` | Bundled VM folder config | Pending |
| `ia_vm_custom_search_for_launchers.htm` | Custom VM search for launchers | Pending |
| `ia_choose_java_vm_panel.htm` | Choose Java VM panel | Pending |
| `jre_dirname.htm` | JRE directory naming | Pending |
| `jrevmpack-sa.htm` | JRE/VM pack standalone | Pending |

**Silent/Unattended Installation:**

| Page | Topic | Collection Status |
|------|-------|-------------------|
| `ia_silent_installers.htm` | Silent installers overview | Pending |
| `ia_response_files_silent.htm` | Response files for silent installs | Pending |
| `ia_generating_response_files.htm` | Generating response files | Pending |
| `ia_using_command_line_arguments.htm` | CLI arguments with installers | Pending |

**Command Line:**

| Page | Topic | Collection Status |
|------|-------|-------------------|
| `ia_ref_command_line_install_uninstall.htm` | Installer/Uninstaller CLI args | Pending |
| `ia_ref_command_line_build.htm` | Build CLI arguments | Pending |
| `ia_ref_command_line_launcher.htm` | Launcher CLI arguments | Pending |

**Platform & Cross-Platform:**

| Page | Topic | Collection Status |
|------|-------|-------------------|
| `ia_appl_plaforms.htm` | Application platforms | Pending |
| `ia_ref_ad_project_platforms_unix.htm` | UNIX platform settings | Pending |
| `ia_CustomizeCheckPlatformRule.htm` | Check Platform rule customization | Pending |
| `ia_ref_rules_check_platform.htm` | Check Platform rule reference | Pending |
| `ia_64bit_windows.htm` | 64-bit Windows specifics | Pending |
| `ia_console_installers.htm` | Console installers | Pending |

**XML & Actions:**

| Page | Topic | Collection Status |
|------|-------|-------------------|
| `ia_ref_actions_modifyxml.htm` | Modify XML action | Pending |
| `ia_ref_readxml_db.htm` | Read XML reference | Pending |
| `ia_ref_plugins_extracttofile.htm` | Extract to file plugin | Pending |

---

## 3. File Format Quick Reference (Known So Far)

| Format | Extension | Purpose | Spec Collected? |
|--------|-----------|---------|-----------------|
| Project file | `.iap_xml` | XML project definition (design-time, all actions/panels/rules/variables) | No |
| Legacy project | `.ia` | Older binary project format | No |
| Install descriptor | `install.xml` | Runtime installation sequence (embedded in built installer) | No |
| LAX config | `.lax` | Java properties file: JVM path, classpath, heap, env vars, stdout/stderr | No |
| Response file | `installer.properties` | Key=value pairs for silent/unattended installs | No |
| Build properties | `.xml` | CI/CD build automation parameters | No |
| Manifest files | (varies) | Platform-specific content bundling and file inclusion/exclusion | No |
| Install log | (varies) | Runtime log of actions taken, errors, variable values | No |

---

## 4. Architecture Understanding (Verified 2026-02-19)

### 4.1 Built Installer Structure

A built InstallAnywhere installer is a **self-extracting archive** containing:

<eg>
<installer>.exe / <installer>.bin
├── Native launcher stub (platform-specific)
├── Bundled JRE (optional, platform-specific)
├── install.xml (runtime descriptor)
├── Compressed payload (application files)
└── LAX configuration templates
</eg>

### 4.2 Runtime Execution Sequence

<eg>
1. Native launcher self-extracts to temp dir (configurable via -tempdir)
2. Locates JVM: bundled > LAX_VM param > system-installed (order configurable)
3. Launches Java-based installer engine
4. Java engine reads install.xml
5. Processes actions/panels/rules in sequence
6. Creates LaunchAnywhere executables + .lax files
7. Optionally generates response file (installer.properties)
</eg>

### 4.3 LaunchAnywhere Runtime (Post-Install)

<eg>
1. User runs LaunchAnywhere executable
2. Reads companion .lax file for configuration
3. Locates JVM per .lax settings
4. Configures classpath, system properties, heap, env vars
5. Launches the Java application
</eg>

---

## 5. Cross-Platform Strategy: Windows -> Linux

### 5.1 Known Approaches

| Approach | Complexity | Risk | Status |
|----------|------------|------|--------|
| Vendor provides Linux `.bin` | Low | Low | Check first |
| Extract payload with `7z` / `unzip` | Medium | Medium | Needs testing |
| Run `.exe` under Wine | Medium | Medium | Needs testing |
| Extract + edit `.lax` to point to Linux JVM | Medium-High | Medium | Needs spec detail |
| Parse `install.xml` and replay actions manually | High | High | Requires full spec |

### 5.2 Information Still Needed

- [ ] Exact binary structure of the self-extracting archive (ZIP header? custom format?)
- [ ] `install.xml` schema / DTD -- what actions are defined, what is the XML structure?
- [ ] Full `.lax` property reference with all valid keys and value formats
- [ ] Platform rule evaluation logic -- how does the installer decide what to skip on Linux?
- [ ] Registry action equivalents -- what maps to Linux (config files? symlinks?)
- [ ] Service creation actions -- Windows services vs Linux systemd/init.d
- [ ] File permission handling differences (NTFS ACLs vs POSIX permissions)
- [ ] Response file encoding requirements per platform (UTF-8 no BOM for Linux, verified)
- [ ] How `$INSTALL_DIR$` and other path variables resolve on Linux vs Windows

---

## 6. Collection Process (Iterative)

### Phase 1: Harvest Official Docs (Current)

**Method**: Fetch each page listed in Section 2.2 and extract structured content.

<eg>
For each page in Section 2.2:
  1. Fetch page content from docs.revenera.com
  2. Extract spec-relevant information (schemas, property names, value formats)
  3. Record in corresponding reference file under research/installer-tools/references/
  4. Update Collection Status in this file to "Collected" with date
  5. Note any linked pages not yet in our list -> add to Section 2.2
</eg>

**Output**: One reference file per topic area:
- `references/file-formats.md` -- All file format specifications
- `references/lax-properties.md` -- Complete LAX property reference
- `references/response-files.md` -- Response file format and encoding
- `references/manifest-structure.md` -- Manifest file structure
- `references/cli-arguments.md` -- All command-line arguments
- `references/platform-rules.md` -- Platform-specific rules and conditions
- `references/jvm-handling.md` -- JRE bundling, VM selection, LAX_VM
- `references/install-xml-schema.md` -- install.xml structure and actions

### Phase 2: Community Knowledge

**Method**: Search for community experiences with cross-platform InstallAnywhere usage.

<eg>
1. Search GitHub for "installanywhere extract" / "installanywhere linux" / ".lax file"
2. Search Stack Overflow [installanywhere] tag for cross-platform Q&A
3. Search Revenera Community forums for Linux installation topics
4. Document any open-source tools that parse IA formats
5. Record practical tips and gotchas
</eg>

**Output**: `references/community-knowledge.md`

### Phase 3: Hands-On Exploration

**Method**: Given an actual Windows InstallAnywhere installer, reverse-engineer its structure.

<eg>
1. Attempt extraction with 7z, unzip, binwalk
2. Document the actual archive structure found
3. Locate and parse install.xml
4. Locate and document .lax templates
5. Map actions to Linux equivalents
6. Test silent install with response file under Wine
7. Test native Linux execution with extracted payload + Linux JVM
</eg>

**Output**: `references/extraction-guide.md` and `references/action-mapping.md`

### Phase 4: Synthesis

**Method**: Combine all collected specs into an actionable installation procedure.

<eg>
1. Write step-by-step Linux installation procedure from Windows IA manifest
2. Document all assumptions and platform-specific translations
3. Create decision tree for handling each IA action type on Linux
4. Validate procedure against actual installer
</eg>

**Output**: `references/linux-installation-procedure.md`

---

## 7. CLI Arguments Reference (Collected 2026-02-19)

### Installer Arguments

| Argument | Description |
|----------|-------------|
| `-i <mode>` | Interface mode: `silent`, `console`, `gui` |
| `-f <path>` | Response file path (installer only, not uninstaller) |
| `-r [path]` | Generate response file at path |
| `-D<var>=<value>` | Set installer variable (installer only) |
| `-l <locale>` | Set locale (ISO-639 + optional ISO-3166) |
| `-jvmxms <size>` | Initial JVM heap (`25m`, `1g`, etc.) |
| `-jvmxmx <size>` | Maximum JVM heap |
| `-tempdir <path>` | Temporary extraction directory |
| `-?` / `-help` | Show help (Windows: console mode only) |

### Launcher Arguments

| Argument | Description |
|----------|-------------|
| `LAX_VM <path>` | Override JVM path for launcher |

All other arguments pass through to the launched application.

---

## 8. Key LAX Properties (Known So Far)

| Property | Purpose |
|----------|---------|
| `lax.nl.current.vm` | Path to Java executable the launcher uses |
| `lax.command.line.args` | Arguments passed to launched application |

> **TODO**: Full property list requires fetching `ia_ref_laxprop.htm`.

---

## 9. Self-Improvement Log

Track what changed with each iteration so the process gets better over time.

| Date | Version | Changes | What Worked | What Didn't |
|------|---------|---------|-------------|-------------|
| 2026-02-19 | v0.1 | Initial draft. Identified 40+ doc pages. Verified docs.revenera.com URLs. Documented architecture and CLI args. | Direct fetch of docs.revenera.com pages returned structured content. PDF user guide downloaded successfully. | Google/SO web searches returned CAPTCHA/JS challenges -- need alternative search approach for community content. |

### Process Improvements Backlog

- [ ] Determine if `Sitemap.xml` can be parsed to auto-discover additional pages
- [ ] Find alternative search approach for community content (GitHub API? `gh search`?)
- [ ] Evaluate whether the PDF user guide can be parsed section-by-section for faster collection than fetching individual HTML pages
- [ ] Add validation step: after collecting each spec, verify it against the PDF to catch HTML-only or PDF-only content
- [ ] Consider creating a structured schema (JSON/YAML) for the file format specs to enable programmatic use
- [ ] Add a "confidence level" column to the File Format Quick Reference table
- [ ] Determine if older version docs contain information removed from current version

---

## 10. Session Resumption Checklist

When resuming work on this process:

1. Read this file first to understand current state
2. Check Collection Status columns in Section 2.2 for next pending items
3. Check the Self-Improvement Log for known issues
4. Check the Process Improvements Backlog for meta-improvements
5. After each collection session, update:
   - Collection Status for pages fetched
   - File Format Quick Reference for new formats discovered
   - Self-Improvement Log with what worked/didn't
   - Process Improvements Backlog with new ideas
   - Section 5.2 checklist for information gaps closed

---

## References

- [Revenera InstallAnywhere Documentation](https://docs.revenera.com/installanywhere/Default.htm) (accessed 2026-02-19)
- [InstallAnywhere 2025 R2 User Guide PDF](https://docs.revenera.com/installanywhere/pdf/InstallAnywhere2025R2UserGuide.pdf) (accessed 2026-02-19)
- [Revenera Community Forums](https://community.revenera.com) (not yet accessed)
