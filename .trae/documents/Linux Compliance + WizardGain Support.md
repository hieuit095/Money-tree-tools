## Code Review (Against Income-Generator Docs)

### Prerequisites / Dependencies Alignment
- **Docker + Docker Compose**: your install flow ensures `docker.io` + compose plugin/v2 are installed and Docker is enabled at boot. [setup.sh](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/setup.sh)
- **ARM emulation (binfmt/qemu)**: docs recommend enabling an emulation layer on ARM to run x86 images; your setup installs `qemu-user-static` + `binfmt-support` and registers binfmt handlers using `tonistiigi/binfmt`, persisted via a systemd oneshot unit. This matches the documented intent for ARM boards (Debian/Armbian). [setup.sh](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/setup.sh)
- **Local config storage**: IGM stores config locally; your tool stores it locally too, and encrypts it (`.env.enc`). [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py)
- **Multi-platform targeting**: you infer `TARGET_PLATFORM` from `platform.machine()` and propagate per-service platform defaults. [config_manager.py:L49-L79](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L49-L79)

### Linux (Debian/Armbian) Optimization Findings
- **Swap/ZRAM ordering is suboptimal for SBCs**: `scripts/optimize.py` creates a disk swapfile first, then enables ZRAM afterward. On Armbian this can cause unnecessary SD/eMMC wear. [optimize.py:L63-L141](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/optimize.py#L63-L141)
- **ZRAM is not persistent across reboot**: both CLI optimization and UI endpoint apply ZRAM by writing `/sys/block/zram0/*` and `swapon`, but there’s no boot-time service to reapply after restart. [zram_manager.py:L75-L127](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/zram_manager.py#L75-L127)
- **Armbian detection exists but isn’t used**: `is_armbian()` exists but doesn’t influence defaults. [platform_info.py:L71-L79](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/platform_info.py#L71-L79)
- **IGM container log rotation is extremely small** (10k/1 file): this can hide failures fast, making watchdog recovery/debug harder. [compose.hosting.yml:L229-L257](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.hosting.yml#L229-L257)

## WizardGain Support Status
- **Vendored IGM includes WizardGain**: present in `apps.json` and compose definitions. [apps.json](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/apps.json), [compose.hosting.yml:L235-L257](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.hosting.yml#L235-L257)
- **Backend control exists**: container orchestration includes `ENABLE_WIZARDGAIN -> wizardgain`. [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py)
- **Env wiring exists**: `WIZARDGAIN_EMAIL` is mapped to compose `EMAIL=${WIZARDGAIN_EMAIL:-}` and profile variable is present. [igm_mapping.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/igm_mapping.py)
- **Main missing piece is UI/config persistence**: `ENABLE_WIZARDGAIN` is not part of `get_required_fields()` (so it can’t be saved) and there is no WizardGain section in `get_config_sections()` (so it can’t be configured from the dashboard). [config_manager.py:L107-L145](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L107-L145)

## Implementation Plan (After You Confirm)
### 1) Make WizardGain fully configurable
- Add `ENABLE_WIZARDGAIN` to required fields so it persists to `.env.enc`. [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py)
- Add a WizardGain section to `get_config_sections()` with:
  - `enable_key: ENABLE_WIZARDGAIN`
  - field: `WIZARDGAIN_EMAIL`
- Extend inventory verification to include `wizardgain` so CI catches regressions. [verify_required_services.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/verify_required_services.py)

### 2) Optimize Debian/Armbian swap policy
- Change `scripts/optimize.py` to:
  - configure ZRAM first
  - only create a swapfile if ZRAM cannot be enabled
  - if ZRAM becomes active, remove `/swapfile` from `/etc/fstab` (idempotently) and swapoff/delete `/swapfile`

### 3) Persist ZRAM across reboot
- Add a systemd oneshot unit (and optionally a timer) that runs at boot and applies ZRAM using the same logic as [zram_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/zram_manager.py) (honoring `ZRAM_SIZE_MB`).

### 4) (Optional but recommended) Improve log retention for debugging
- Bump IGM compose `json-file` log rotation from `10k/1` to a more practical size to avoid losing crash reasons quickly. [compose.hosting.yml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.hosting.yml)

### 5) Verify on Debian/Armbian
- Run a local lint/diagnostic pass and verify that:
  - WizardGain can be enabled and persists
  - ZRAM survives reboot
  - enabling services yields actionable error output if startup fails
