# Blender Cloud changelog


## Version 1.25 (2022-02-25)

- Compatibility with Blender 3.1 (Python 3.10).
- Bump blender-asset-tracer to version 1.11, for UDIM support.


## Version 1.24 (2022-02-04)

- Bump blender-asset-tracer version 1.8 → 1.10, for fixing a bug where files were doubly-compressed.


## Version 1.23 (2021-11-09)

- Bump blender-asset-tracer version 1.7 → 1.8, for compatibility with sending read-only blend files to Flamenco.


## Version 1.22 (2021-11-05)

- Fix Windows incompatibility when using Shaman URLs as job storage path.
- Bump blender-asset-tracer version 1.6 → 1.7, for compatibility with files compressed by Blender 3.0.


## Version 1.21 (2021-07-27)

- Bump blender-asset-tracer version 1.5.1 → 1.6, for better compatibility with Geometry Nodes.

## Version 1.20 (2021-07-22)

- Bump blender-asset-tracer version 1.3.1 -> 1.5.1.
- Blender-asset-tracer "Strict Pointer Mode" disabled, to avoid issues with
  not-entirely-synced library overrides.

## Version 1.19 (2021-02-23)

- Another Python 3.9+ compatibility fix.

## Version 1.18 (2021-02-16)

- Add compatibility with Python 3.9 (as used in Blender 2.93).
- Drop compatibility with Blender 2.79 and older. The last version of the
  Blender Cloud add-on with 2.79 and older is version 1.17.

## Version 1.17 (2021-02-04)

- This is the last version compatible with Blender 2.77a - 2.79.
- Upgrade BAT to version 1.3.1, which brings compatibility with Geometry Nodes and
  fixes some issues on Windows.

## Version 1.16 (2020-03-03)

- Fixed Windows compatibility issue with the handling of Shaman URLs.

## Version 1.15 (2019-12-12)

- Avoid creating BAT pack when the to-be-rendered file is already inside the job storage
  directory. This assumes that the paths are already correct for the Flamenco Workers.

## Version 1.14 (2019-10-10)

- Upgraded BAT to 1.2 for missing smoke caches, compatibility with Blender 2.81, and some
  Windows-specific fixes.
- Removed warnings on the terminal when running Blender 2.80+

## Version 1.13 (2019-04-18)

- Upgraded BAT to 1.1.1 for a compatibility fix with Blender 2.79
- Flamenco: Support for Flamenco Manager settings versioning + for settings version 2.
  When using Blender Cloud Add-on 1.12 or older, Flamenco Server will automatically convert the
  Manager settings to version 1.
- More Blender 2.80 compatibility fixes

## Version 1.12 (2019-03-25)

- Flamenco: Change how progressive render tasks are created. Instead of the artist setting a fixed
  number of sample chunks, they can now set a maximum number of samples for each render task.
  Initial render tasks are created with a low number of samples, and subsequent tasks have an
  increasing number of samples, up to the set maximum. The total number of samples of the final
  render is still equal to the number of samples configured in the blend file.
  Requires Flamenco Server 2.2 or newer.
- Flamenco: Added a hidden "Submit & Quit" button. This button can be enabled in the add-on
  preferences and and then be available on the Flamenco Render panel. Pressing the button will
  silently close Blender after the job has been submitted to Flamenco (for example to click,
  walk away, and free up memory for when the same machine is part of the render farm).
- Flamenco: Name render jobs just 'thefile' instead of 'Render thefile.flamenco.blend'.
  This makes the job overview on Flamenco Server cleaner.
- Flamenco: support Shaman servers. See https://www.flamenco.io/docs/user_manual/shaman/
  for more info.
- Flamenco: The 'blender-video-chunks' job type now also allows MP4 and MOV video containers.

## Version 1.11.1 (2019-01-04)

- Bundled missing Texture Browser icons.

## Version 1.11.0 (2019-01-04)

- Texture Browser now works on Blender 2.8.
- Blender Sync: Fixed compatibility issue with Blender 2.8.

## Version 1.10.0 (2019-01-02)

- Bundles Blender-Asset-Tracer 0.8.
- Fix crashing Blender when running in background mode (e.g. without GUI).
- Flamenco: Include extra job parameters to allow for encoding a video at the end of a render
  job that produced an image sequence.
- Flamenco: Compress all blend files, and not just the one we save from Blender.
- Flamenco: Store more info in the `jobinfo.json` file. This is mostly useful for debugging issues
  on the render farm, as now things like the exclusion filter and Manager settings are logged too.
- Flamenco: Allow BAT-packing of only those assets that are referred to by relative path (e.g.
  a path starting with `//`). Assets with an absolute path are ignored, and assumed to be reachable
  at the same path by the Workers.
- Flamenco: Added 'blender-video-chunks' job type, meant for rendering the edit of a film from the
  VSE. This job type requires that the file is configured for rendering to Matroska video
  files.

  Audio is only extracted when there is an audio codec configured. This is a bit arbitrary, but it's
  at least a way to tell whether the artist is considering that there is audio of any relevance in
  the current blend file.

## Version 1.9.4 (2018-11-01)

- Fixed Python 3.6 and Blender 2.79b incompatibilities accidentally introduced in 1.9.3.

## Version 1.9.3 (2018-10-30)

- Fix drawing of Attract strips in the VSE on Blender 2.8.

## Version 1.9.2 (2018-09-17)

- No changes, just a different filename to force a refresh on our
  hosting platform.

## Version 1.9.1 (2018-09-17)

- Fix issue with Python 3.7, which is used by current daily builds of Blender.

## Version 1.9 (2018-09-05)

- Last version to support Blender versions before 2.80!
- Replace BAM with BAT🦇.
- Don't crash the texture browser when an invalid texture is seen.
- Support colour strips as Attract shots.
- Flamenco: allow jobs to be created in 'paused' state.
- Flamenco: only show Flamenco Managers that are linked to the currently selected project.

## Version 1.8 (2018-01-03)

- Distinguish between 'please subscribe' (to get a new subscription) and 'please renew' (to renew an
  existing subscription).
- When re-opening the Texture Browser it now opens in the same folder as where it was when closed.
- In the texture browser, draw the components of the texture (i.e. which map types are available),
  such as 'bump, normal, specular'.
- Use Interface Scale setting from user preferences to draw the Texture Browser text.
- Store project-specific settings in the preferences, such as filesystem paths, for each project,
  and restore those settings when the project is selected again. Does not touch settings that
  haven't been set for the newly selected project. These settings are only saved when a setting
  is updated, so to save your current settings need to update a single setting; this saves all
  settings for the project.
- Added button in the User Preferences to open a Cloud project in your webbrowser.

## Version 1.7.5 (2017-10-06)

- Sorting the project list alphabetically.
- Renamed 'Job File Path' to 'Job Storage Path' so it's more explicit.
- Allow overriding the render output path on a per-scene basis.

## Version 1.7.4 (2017-09-05)

- Fix [T52621](https://developer.blender.org/T52621): Fixed class name collision upon add-on
  registration. This is checked since Blender 2.79.
- Fix [T48852](https://developer.blender.org/T48852): Screenshot no longer shows "Communicating with
  Blender Cloud".

## Version 1.7.3 (2017-08-08)

- Default to scene frame range when no frame range is given.
- Refuse to render on Flamenco before blend file is saved at least once.
- Fixed some Windows-specific issues.

## Version 1.7.2 (2017-06-22)

- Fixed compatibility with Blender 2.78c.

## Version 1.7.1 (2017-06-13)

- Fixed asyncio issues on Windows

## Version 1.7.0 (2017-06-09)

- Fixed reloading after upgrading from 1.4.4 (our last public release).
- Fixed bug handling a symlinked project path.
- Added support for Manager-defined path replacement variables.

## Version 1.6.4 (2017-04-21)

- Added file exclusion filter for Flamenco. A filter like `*.abc;*.mkv;*.mov` can be
  used to prevent certain files from being copied to the job storage directory.
  Requires a Blender that is bundled with BAM 1.1.7 or newer.

## Version 1.6.3 (2017-03-21)

- Fixed bug where local project path wasn't shown for projects only set up for Flamenco
  (and not Attract).
- Added this CHANGELOG.md file, which will contain user-relevant changes.

## Version 1.6.2 (2017-03-17)

- Flamenco: when opening non-existing file path, open parent instead
- Fix T50954: Improve Blender Cloud add-on project selector

## Version 1.6.1 (2017-03-07)

- Show error in GUI when Blender Cloud is unreachable
- Fixed sample count when using branched path tracing

## Version 1.6.0 (2017-02-14)

- Default to frame chunk size of 1 (instead of 10).
- Turn off "use overwrite" and "use placeholder" for Flamenco blend files.
- Fixed bugs when blendfile is outside the project directory


## Older versions

For the history of older versions, please refer to the
[Git history](https://developer.blender.org/diffusion/BCA/)
