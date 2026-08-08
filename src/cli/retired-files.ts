/**
 * Instrument files that setup installed under a previous release and no longer
 * ships. Setup removes them, but only when the file on disk still matches one of
 * the exact contents we published — a locally modified copy is kept and reported
 * instead, so no customization is destroyed silently.
 *
 * This list only matters for installs made before the install manifest existed.
 * Once `.opencode/.omg-manifest.json` is present the manifest is authoritative
 * and this list is not consulted.
 *
 * Paths are limited to the directories setup manages (agents, commands, skills).
 * `opencode/prompts/` was never installed by setup, so removing it is not ours.
 *
 * Generated — do not edit by hand.
 * Regenerate with: node tools/generate-retired-files.mjs
 */
export const RETIRED_FILES: Readonly<Record<string, readonly string[]>> = {
  "agents/omg-build.md": [
    "4520e829bdacec55584a19c5a59523a116eed852c299bf1062ab1b1f3275c717",
    "7e3d9fe39b1d6d684cb75f6f23f66f1e5908b5079e32685338ea6521db6ba66d",
  ],
  "agents/omg-spec-writer.md": [
    "9fd14de22ed62d4448e905bc972097e96759d77db7e6196c95c936e22abe70ec",
    "c700f1e3c2c3fdf2e0338c01f714e456ba15f6b0c8937e4f6cfdc7c94567859c",
  ],
  "commands/omg-cleanup.md": [
    "01ea69e271444f50e7cdec45e40a72dbea2f4bc99cfa434617124d4023553076",
    "0ecb8e04b7cd633434b9f82726ac98da9e6e8b39545b53c5ab3fddd846dd8a62",
    "ac32467f810403e49251efb6ad8eadf5ea966565d09de5fc7fc1c303df433181",
  ],
  "commands/omg-ensure-work-finished.md": [
    "b87e10eb943d8e3d9be08df22fe48457f2fb2226dd2f53ea3073d1739bc56157",
  ],
  "commands/omg-spec-refine.md": [
    "f0695ebee12e625a81351add80e762e40fd9ddcb56559dcea6f7e667b21962c3",
  ],
  "commands/omg-spec-track.md": [
    "8611860d48460a8684afa1ae1202c3738edc01068a429a3c098368164ec5bf9d",
  ],
  "commands/omg-status.md": [
    "4f088d494163b4cb3f2ae3232313a69b0a77cfd4c379eab6888dbb092a58c5fd",
  ],
  "commands/omg-work.md": [
    "3a7b29bc79f3449607f906936cab8e3cff4785eb6d84c0ee92b23613687712e3",
    "6402166768c02bb598df988404567995f120b9b59b57312ca246dae28dd663df",
    "d6de9a0be95b86a4f4054d9577fb1e62fc0efc2c3ed55b5d7387dc5bdf09665b",
  ],
  "skills/omg-decompose/references/fresh.md": [
    "c05fafc1eee4226c0a47ab844f7998a527fb6511066172449d26b4d17ad58480",
  ],
  "skills/omg-decompose/references/refinement.md": [
    "fc59fdda031ae42ac57d9da6932dc42a9bfdda8361e3104878f9fb916c010997",
  ],
  "skills/omg-epics/SKILL.md": [
    "083ef5722be34af3caec9584e7dd195289e447e3d87b84c7096aa5c8d3eea55f",
    "248a254bb8ae4cd9e401296d2d721f75c3cfdf81e0f955d6261fb6ab1e7d0b6a",
    "3f329527197ce7a934ea87871823e1b2e4713de082044e4cefe671f2480e42f4",
    "dc4837a2e9e598ea44051e04e77a22b4ad531ae7b4f5c4286878cc9fde0466ef",
  ],
  "skills/omg-misc/scripts/ensure-test-opt-out.sh": [
    "c95b2d9aa684a4d5bff0ff9ce4663444b2889494ed046904cff9e9248995bc69",
  ],
}
