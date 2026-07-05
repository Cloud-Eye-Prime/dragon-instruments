# Enable auto-deploy -- the two dashboard clicks the CLI cannot do

Both services now have a GitHub source (the prerequisite -- done). The
Railway CLI (v4.29) has NO verb to connect a repo or toggle deploy-on-push,
and there is no API token in the environment, so the final connection is a
dashboard action. Project **Team-CoachAI** (`f9a827e0-3416-4493-bf77-b67798fe32d2`),
environment **production**.

## 1. dragon-grabber  (service 841cfbb4-5c89-4faf-9726-b083bf27c8c1)
Repo: **Cloud-Eye-Prime/dragon-grabber** (created + pushed this session).
- Railway -> project -> `dragon-grabber` service -> **Settings -> Source**.
- **Connect Repo** -> authorize the Railway GitHub App on Cloud-Eye-Prime if
  prompted -> pick `Cloud-Eye-Prime/dragon-grabber`, branch `master`.
- Leave the builder as Dockerfile (railway.json already pins it).
- Enable **"Deploy on push"** (Check Suites / auto-deploy).
- NOTE: the first auto-build compiles the Phase 1 librosa/numba wheels --
  the one stated build risk. Watch that first build log; if numba fights the
  base image, that is where it shows. The pins are cp312 manylinux.

## 2. heartbeat-pages  (service 7de1006c-a9d4-4c89-824f-0ac9ad21606c)
Repo: **Cloud-Eye-Prime/dragon-instruments**, branch `master`, root serves `public/`.
- Same path: Settings -> Source -> Connect Repo -> `dragon-instruments` `master`.
- Builder is `serve public` (package.json); no change needed.
- Enable **Deploy on push**.

## What changes after this
- `git push` to either `master` auto-builds + deploys. The manual `railway up`
  posture (and the manual verify-before-serve gate) is replaced by push-to-live.
- KEEP the discipline the plan named: probe the live domain after each push
  (`/diag` + a live `/grab?q=...&analyze=1` for the grabber; `/tempo_mixer.html`
  for the mixer). Auto-deploy removes the gate, not the need to verify.
- Both repos are in a clean deployable state right now (grabber Phase 1 code
  committed; instruments at current master).
