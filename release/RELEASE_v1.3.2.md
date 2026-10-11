# Highlight Desktop Test v1.3.2

Fixes the desktop application icon, makes large Jobs histories searchable and
paginated, and preserves manual render concurrency after polling and restart.

- Local favicon and application icons for the native Chrome app window.
- Filter Jobs by error, queued, running or completed. Search, show 25/50/100
  rows, page through results, and see error messages alongside each job.
- Manual 1-4 concurrency is saved with queue state and applied to actual render
  slots. Polling no longer overwrites a pending selection.
- Jobs, Dashboard and queue status avoid copying large transcript payloads.
  Jobs and clips load when their panes are opened.
- Faster portrait center-crop rendering, with the existing quality and full
  decode checks preserved.

Validation: 787 tests and 29 subtests passed, 4 skipped; browser interaction,
native Windows icon and JavaScript checks passed. A six-second synthetic CPU
render benchmark measured a 1.268 speed ratio; actual performance depends on
hardware and input. A 1,264-job fixture returned a 25-row page in 3.632 ms.

Close the old application before installing this version into its existing
test install directory. The installer preserves settings, jobs and data.
This is a desktop-test prerelease.
