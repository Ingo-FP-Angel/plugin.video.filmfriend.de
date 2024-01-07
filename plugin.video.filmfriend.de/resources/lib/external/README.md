# Imported dependencies

This folder may contain files from external dependencies that have no released version that works out of the box.

## script.module.libmediathek4

Version 1.0.0 of https://github.com/sarbes/script.module.libmediathek4 by sarbes uses deprecated properties for "inputstream"
so that video playback wouldn't be possible.

If a fixed version gets released, delete files `libmediathek4.py` and `libmediathek4utils.py`, then add this depencency to `addon.xml` with the correct version:

```
               <import addon="script.module.libmediathek4" version="1.0.1"/>
```
