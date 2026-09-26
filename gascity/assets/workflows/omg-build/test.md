Load the `omg-build` skill. Test the integrated implementation against the approved
specs and planned verification in `{{artifact_root}}`. Author missing meaningful
tests if needed and commit them before the final run. Save tests.json at the
current commit with commands, exit codes and complete hashed logs. Include
regression and failure cases appropriate to the change. Persist failing results
too, so the builder can diagnose them. After recording results, close this testing
work with gc.outcome=pass even if tests failed; the group check reads their exit
codes and decides whether another repair is needed. Failure to produce evidence
is a failed work step.
Do not invoke verify --stage quality here; the controller checks the complete group
after review has recorded its verdict for these tests.
Map test receipts to the approved development-check IDs. Assess required downstream
test artifacts with controlled inputs as appropriate, but do not run the deployment
pipeline or require its results. CI/CD and operators collect those results later.
