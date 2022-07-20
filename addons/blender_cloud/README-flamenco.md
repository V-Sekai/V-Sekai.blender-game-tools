# Flamenco

The Blender Cloud add-on has preliminary support for [Flamenco](https://flamenco.io/).
It requires a project on the [Blender Cloud](https://cloud.blender.org/) that is set up for
Flamenco, and it requires you to be logged in as a user with rights to use Flamenco.


## Quirks

Flamenco support is unpolished, so it has some quirks.

- Project selection happens through the Attract project selector. As a result, you can only
  select Attract-enabled projects (even when they are not set up for Flamenco). Be careful
  which project you select.
- The top level directory of the project is also set through the Attract properties.
- Defaults are heavily biased for our use in the Blender Institute.
- Settings that should be project-specific are not, i.e. are regular add-on preferences.
- Sending a project to Flamenco will check the "File Extensions" setting in the Output panel,
  and save the blend file to the current filename.

## Render job file locations

Rendering via Flamenco roughly comprises of two steps:

1. Packing the file to render with its dependencies, and placing them in the "job file path".
2. Rendering, and placing the output files in the "job output path".

### Job file path

The "job file path" consists of the following path components:

1. The add-on preference "job file path", e.g. `/render/_flamenco/storage`
2. The current date and time, your Blender Cloud username, and the name of the current blend file.
3. The name of the current blend file.

For example:

`/render/_flamenco/storage/2017-01-18-104841.931387-sybren-03_02_A.layout/03_02_A.layout.blend`

### Job output path

The file path of output files consists of the following path components:

1. The add-on preference "job file path", e.g. `/render/agent327/frames`
2. The path of the current blend file, relative to the project directory. The first N components
   of this path can be stripped; when N=1 it turns `scenes/03-searching/03_02_A-snooping/` into
   `03-searching/03_02_A-snooping/`.
3. The name of the current blend file, without `.blend`.
4. The file name depends on the type of output:
   - When rendering to image files: A 5-digit frame number with the required file extension.
   - When rendering to a video file: The frame range with the required file extension.

For example:

`/render/agent327/frames/03-searching/03_02_A-snooping/03_02_A.layout/00441.exr`

`/render/agent327/frames/03-searching/03_02_A-snooping/03_02_A.layout/14-51,60-133.mkv`
