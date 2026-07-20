---
name: qnap-qpkg-dev
description: Build, validate, and troubleshoot QNAP QPKG packages with QDK
---

<Purpose>
qnap-qpkg-dev is a production-oriented workflow for developing QNAP QPKG packages from source to installable artifact.
It standardizes environment bootstrapping, qpkg metadata design, architecture packaging, install/upgrade routines, and verification.
</Purpose>

<Use_When>
- User wants to create a new QPKG from scratch
- User wants to convert an existing app into a QPKG
- User wants to debug install/upgrade/startup behavior for a QPKG
- User needs a repeatable multi-arch build flow (arm-x09/arm-x19/x86/x86_64)
- User asks for QDK/qbuild best practices and packaging guardrails
</Use_When>

<Do_Not_Use_When>
- User only needs a quick read-only explanation of one qpkg.cfg field
- User asks for non-QNAP packaging formats (Docker, Debian, RPM, etc.)
- User asks for UI/frontend coding unrelated to QPKG lifecycle
</Do_Not_Use_When>

<Why_This_Exists>
QPKG packaging has NAS-specific constraints (qpkg.conf registration, service script semantics, config file upgrade handling, architecture directory layout).
A generic packaging workflow misses these details and often causes installation failure, startup failure, or upgrade regressions.
</Why_This_Exists>

<Execution_Policy>
- Prefer QDK-native flow: `qbuild --create-env` -> configure `qpkg.cfg` -> implement `package_routines` + service script -> `qbuild`
- Keep package behavior reversible and deterministic across install/upgrade/enable/disable cycles
- Validate with both static checks (`qbuild --query`) and install-script behavior checks (`qbuild --extract` + `sh qinstall.sh`)
- Use full command paths inside install routines when reliability matters (`/sbin/getcfg`, `/bin/ln`, etc.)
- For cleanup/refactor in package scripts, preserve behavior with a fast extract/install loop before major edits
</Execution_Policy>

<Core_References>
- `QDK_Quick_Start_Guide_v4_eng.pdf`: baseline 5-step flow and default env layout
- `QDK_2.0_2.pdf`: qpkg.cfg semantics, qbuild options, install/runtime variables
- `QDK_Cookbook.pdf`: practical recipes for config handling, pre/post-build automation, faster iteration
- `QPKG_developer_FAQ.pdf`: common icon/webui/script/startup pitfalls
</Core_References>

<Canonical_Workflow>
1. **Create build skeleton**
   - `cd $(getcfg QDK Install_Path -f /etc/config/qpkg.conf)`
   - `qbuild --create-env <QPKG_NAME>`
   - Enter project dir and confirm required tree: `shared/`, `config/`, arch dirs, `qpkg.cfg`, `package_routines`

2. **Define package metadata in `qpkg.cfg`**
   - Required: `QPKG_NAME`, `QPKG_VER`, `QPKG_AUTHOR`
   - Common: `QPKG_SERVICE_PROGRAM`, `QPKG_RC_NUM`, `QPKG_WEBUI`, `QPKG_REQUIRE`, `QPKG_CONFLICT`, `QPKG_CONFIG`
   - Guardrails:
     - `QPKG_NAME` <= 20 chars, no spaces
     - `QPKG_VER` <= 10 chars, no spaces
     - Keep icon filenames exactly aligned with `QPKG_NAME` (case-sensitive)

3. **Implement lifecycle routines**
   - `package_routines`: `pkg_pre_install`, `pkg_install`, `pkg_post_install`, `pkg_pre_remove`, `pkg_post_remove`
   - `shared/<QPKG_NAME>.sh` service script must support at least `start`, `stop`, `restart`
   - Use runtime discovery when linking binaries:
     - `QPKG_DIR=$(/sbin/getcfg $QPKG_NAME Install_Path -d "" -f /etc/config/qpkg.conf)`

4. **Place files by architecture strategy**
   - Common files: `shared/`
   - Arch-specific files: `arm-x09/`, `arm-x19/`, `x86/`, `x86_64/`
   - External config paths: `config/` with full filesystem subtree (example: `config/etc/config/myapp.conf`)

5. **Build package**
   - Baseline: `qbuild`
   - Common options:
     - `--build-arch <arch>` (repeatable)
     - `--build-version <version>`
     - `--build-dir <dir>`
     - `--force-config` for config files generated at install time
     - `--strict` to treat warnings as errors
     - `--exclude <pattern>` / `--exclude-from <file>` to prevent repo metadata leakage

6. **Verify package before release**
   - Static query:
     - `qbuild --query info <pkg.qpkg>`
     - `qbuild --query dump <pkg.qpkg>`
     - `qbuild --query require <pkg.qpkg>`
   - Extract validation:
     - `qbuild --extract <pkg.qpkg> <tmp_dir>`
     - In extracted dir, run `sh qinstall.sh` for install script validation loop

7. **Harden upgrade behavior**
   - For pre-existing unmanaged configs: use `add_qpkg_config` in `pkg_init`
   - For install-time generated config files: set `QPKG_CONFIG` and build with `--force-config`
   - For intentional config migration: use `set_qpkg_config` after controlled file edits

8. **Automate repeatable builds**
   - Put reusable defaults in `~/.qdkrc` sections
   - Build with `qbuild -s <section>`
   - Use `--pre-build`/`--post-build` for architecture-specific `QDK_EXTRA_FILE` injection/removal

</Canonical_Workflow>

<Troubleshooting_Playbook>
- Icon not shown in App Center:
  - Verify `QDK_DATA_DIR_ICONS` and icon file names match `QPKG_NAME` exactly (case-sensitive)
- Web entry does not jump to app page:
  - Verify `QPKG_WEBUI` and path permissions
- Script command fails during install:
  - Use full command paths in scripts (especially `getcfg`)
- Disabled service starts after reboot:
  - Ensure service script checks enabled state on `start` and exits when disabled
- Build repeatedly slow when tuning only install routines:
  - Use `qbuild --extract` + `sh qinstall.sh` loop instead of full rebuild each iteration
</Troubleshooting_Playbook>

<Output_Contract>
When executing this skill, return:
- QPKG project path and architecture coverage
- Final `qbuild` command(s)
- Produced artifact path(s)
- Verification evidence (`--query` results + install-script test outcome)
- Known residual risks (for example, untested arch/model)
</Output_Contract>

<Final_Checklist>
- [ ] `qpkg.cfg` has required fields and valid naming/version constraints
- [ ] Service script supports `start/stop/restart`
- [ ] File layout matches shared vs arch-specific design
- [ ] Build completed and artifact exists in target build dir
- [ ] `qbuild --query` checks pass for info/dump/require
- [ ] Install/upgrade script behavior validated with extract-and-run loop
- [ ] Residual risks documented for any untested NAS model/architecture
</Final_Checklist>

Task: {{ARGUMENTS}}
