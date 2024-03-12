# MaterialX JSON I/O

## Contents
- [Introduction](#Introduction)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)

## Introduction

This is a Python package for supporting interoperability of  MaterialX documents by adding support conversion to / from a `JSON` representation.

The `JSON` representation is lossless and is targeted at integrations which prefer to use `JSON` as a data exchange format instead of `XML`.

## Documentation

Visit the **[home page](https://kwokcb.github.io/materialxjson/index.html)** for For further information about this package, including links to API documentation and a Jupyter notebook with sample code that expands on the basic *Usage* example.

## Installation

The Python package is losted on **[PyPi](https://pypi.org/project/materialxjson)** and can be installed
using `pip``:

```bash
pip install materialxjson
```

or the **[source repository](https://github.com/kwokcb/materialxjson)** can be cloned and the package built from the command line:

```bash
python -m build
```

This will build a distribution folder called `dist` which contains a zip file which can be installed using:

```bash
pip --install <name of zip>
```

## Usage

The following example shows bidirectional conversion:

1. A MaterialX file in `XML` format is read in and written to a string in `JSON` format. 
2. A MaterialX file in `JSON` format is read in and written to a string in `XML` format.

Note that any `JSON` package can be used to perform `JSON` I/O. The `json` package is used by the utilities provided in this package.

### Package Setup

The `materialjson` package can be loaded as follows, along with MaterialX and json packages:

```python
import json
import MaterialX as mx
from materialxjson import core
```

### XML to JSON Format Conversion

A MaterialX document can be read in from an XML file as follows:

```python
import pkg_resources

# Read in MaterialX file
mtlxFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default.mtlx')

doc = mx.createDocument()
mx.readFromXmlFile(doc, mtlxFileName)
```

and then converted to JSON format as follows by creating a `MaterialXJson` object and calling the `documentToJSON` method:

```python
# Create I/O handler
mtlxjson = core.MaterialXJson()

# Write to JSON format
jsonObject = mtlxjson.documentToJSON(doc)
```

The contents of the JSON object can be extracted out using the `json` package as follows. (An indentation level of `2` is
used to make the output more readable.)

```python
# Convert JSON object to JSON string
jsonString = core.Util.jsonToJSONString(jsonObject)
```

### JSON to XML Format Conversion

A JSON file can be read in as follows. In this case we load the sample file included with the package:

```python
# Get file to load
jsonFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default_mtlx.json')

# Load JSON file
jsonObject = core.Util.readJson(jsonFileName)
```

The JSON object is then converted to a MaterialX document and written out to an XML string as follows:

```python
# Create I/O handler
mtlxjson = core.MaterialXJson()

# Read JSON object into document
doc = mx.createDocument()
mtlxjson.documentFromJSON(jsonObject, doc)

# Write to XML String
docstring = core.Util.documentToXMLString(doc)
```

## Caveats

The following are some caveats to be aware of when using this package:
- There is no equivalent support for "include files" for JSON conversion. The JSON representation is intended to be a single file representation.
- XML comments are not preserved in the JSON representation.

## Author

- LinkedIn: <a href="https://www.linkedin.com/in/bernard-kwok/" target="_blank">Bernard Kwok</a>
- GitHub: [kwokcb](https://github.com/kwokcb)
- Email: <a href="mailto:kwokcb@gmail.com">kwokcb@gmail.com</a>

