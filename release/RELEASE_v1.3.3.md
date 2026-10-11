# Highlight Desktop Test v1.3.3

Adds automatic local media cleanup and storage controls in Settings.

- Remove original video and audio files from completed jobs while preserving
  finished clips, transcripts, job history and publication records.
- Configure source cleanup and published-Reel cleanup independently. Turn off
  published-Reel cleanup to keep finished videos, including videos already posted.
- When published-Reel cleanup is enabled, remove a local clip only after every
  consumer has a confirmed publication. Pending schedules, active content work,
  recovery tasks, uncertain publication results and required website work protect
  media that is still needed.
- Show free disk space, cleanup counts and reclaimed bytes in Settings.
- Run cleanup locally every 20 seconds without waiting for Meta network requests.
  Locked files are deferred without changing completed jobs or published posts.
- Preserve existing configuration and queue data during upgrades. A removed source
  must be downloaded again if it is needed for a later edit.

Validation: the 14 required release-test groups passed with 549 tests and 3 skips;
this is not a claim about the entire repository test suite. JavaScript syntax and
offline browser checks passed. Installer validation also covered embedded Python,
a real FFmpeg portrait render and full decode, HTTP Range playback, shared-media
protection, cleanup policy controls and preserved publication history.

Close the old application before installing into its existing test directory.
This is a desktop-test prerelease.
