# %% [markdown]
# # MaterialXJSON Examples
# 
# The examples below demonstrate how to use the MaterialXJSON library to read and write MaterialX documents in JSON format and convert between the XML and JSON representations.
# 
# ## Setup

# %% [markdown]
# The following utility is provided to display formatted data.

# %%
from IPython.display import display_markdown

def displaySource(title, string, language='xml', open=True):
    text = '<details '
    text = text + (' open' if open else '') 
    text = text + '><summary><b>' + title + '</b></summary>\n\n' + '```' + language + '\n' + string + '\n```\n' + '</details>\n' 
    display_markdown(text, raw=True)

# %% [markdown]
# The basic requirement is to import the following packages:
# - `materialxjson` 
# - `MaterialX` 
# - `json`
# 
# In the example below we import the packages and display the version of each. Additionaly we query the help on the `core` module of the `materialxjson` package.

# %%
import MaterialX as mx
from materialxjson import core
import json
import materialxjson as mtlxjson
import sys, io

stdout = sys.stdout
print("MaterialX version: " + mx.getVersionString())
print("JSON version: " + json.__version__)
print("MaterialXJSON version: " + mtlxjson.__version__)

help(core.MaterialXJson)
help(core.Util)

# %% [markdown]
# ## Package Resources

# %%
import pkg_resources

directory_name = "data"  
files = pkg_resources.resource_listdir('materialxjson', directory_name)
result = ''
for file in files:
    result = result + file + '\n'

displaySource('Available data files', result, 'text', True)

# %% [markdown]
# ## JSON to XML Conversion

# %% [markdown]
# ### XML to JSON Object

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Read XML document
mtlxFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default.mtlx')
print('Using sample file: %s' % mx.FilePath(mtlxFileName).getBaseName())
doc = mx.createDocument()
mx.readFromXmlFile(doc, mtlxFileName)

# Convert to JSON Object
jsonObject = mtlxjson.documentToJSON(doc)
# Convert to JSON String
jsondump = core.Util.jsonToJSONString(jsonObject, 2)
displaySource('Document to JSON', jsondump, 'json', True)


# %% [markdown]
# ### XML to JSON String (Direct)

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Read XML document
mtlxFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default.mtlx')
print('Using sample file: %s' % mx.FilePath(mtlxFileName).getBaseName())
doc = mx.createDocument()
mx.readFromXmlFile(doc, mtlxFileName)

# Convert to JSON String
jsonString = mtlxjson.documentToJSONString(doc)
displaySource('Document to JSON String (direct)', jsonString, 'json', True)

# %% [markdown]
# ### XML to JSON Options
# 
# There are currently a few options available for XML to JSON conversion. These include:
# 
# 1. `indent` - The number of spaces to indent the JSON output. Default is 2.
# 2. `elementPredicate` - A function that takes an element name and returns a boolean indicating whether the element should be included in the JSON output. Default is to include all elements.
# 3. `separators`` - A tuple of strings to use for separating items in a list and a dictionary respectively. Default is `(', ', ': ')`.
# 
# In the example below we skip any surface material elements and adjust the formatting to remove unnecessary spacing.
# 
# The `mtlx2json` utility script exposes options as command line arguments.

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Read XML document
mtlxFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default.mtlx')
print('Using sample file: %s' % mx.FilePath(mtlxFileName).getBaseName())
doc = mx.createDocument()
mx.readFromXmlFile(doc, mtlxFileName)

def skipMaterial(element):
    print('- Skip material element: ' + element.getName())
    return element.getCategory() != 'surfacematerial'

# Set write options
writeOptions = core.JsonWriteOptions()
writeOptions.indent = None # No indentation
writeOptions.separators = (',', ':') # No whitespace
writeOptions.elementPredicate = skipMaterial # Skip materials

# Convert to JSON String
jsonString = mtlxjson.documentToJSONString(doc, writeOptions)
displaySource('Document to JSON String (direct)', jsonString, 'json', True)

# %% [markdown]
# ## JSON to XML Conversion

# %% [markdown]
# ### Loading from JSON File

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Load a MaterialX JSON file to object
jsonFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default_mtlx.json')
print('Using sample file: %s' % mx.FilePath(jsonFileName).getBaseName())
jsonObject = core.Util.readJson(jsonFileName)

# Read JSON object into document
doc = mx.createDocument()
mtlxjson.documentFromJSON(jsonObject, doc)

# Write to JSON String
docstring = core.Util.documentToXMLString(doc)
displaySource('XML from JSON', docstring, 'xml', True)

# %% [markdown]
# ### Loading from JSON String

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Load a MaterialX JSON document
jsonFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default_mtlx.json')
print('Using sample file: %s' % mx.FilePath(jsonFileName).getBaseName())
jsonObject = core.Util.readJson(jsonFileName)
jsonString = core.Util.jsonToJSONString(jsonObject, 2)

# Read into document
doc = mx.createDocument()
mtlxjson.documentFromJSONString(jsonString, doc)

# Write out to XML string
docstring = core.Util.documentToXMLString(doc)
displaySource('XML from JSON String', docstring, 'xml', True)

# %% [markdown]
# ### JSON to MaterialX Options
# 
# The options available for JSON to XML conversion include:
# 1. `upgradeVersion` - A boolean indicating whether to upgrade the version of the MaterialX document to the latest version. Default is `True`.

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Load a MaterialX JSON document
jsonFileName = pkg_resources.resource_filename('materialxjson', 'data/standard_surface_default_mtlx.json')
print('Using sample file: %s' % mx.FilePath(jsonFileName).getBaseName())
jsonObject = core.Util.readJson(jsonFileName)
jsonString = core.Util.jsonToJSONString(jsonObject, 2)

# Read into document
doc = mx.createDocument()

# Set read options
readOptions = core.JsonReadOptions()
readOptions.upgradeVersion = False # Do not upgrade version
mtlxjson.documentFromJSONString(jsonString, doc, readOptions)

# %% [markdown]
# ## Comparisons 
# 
# This example shows the [gltf Sample Models "shoe" model](https://github.com/KhronosGroup/glTF-Sample-Models/tree/master/2.0/MaterialsVariantsShoe) read in XML format, and converted to JSON format. The sample mode was converted from gltf to MaterialX XML using the [gltf2MaterialX](https://github.com/kwokcb/materialxgltf/) converter. 

# %%
import pkg_resources
import MaterialX as mx
from materialxjson import core
from IPython.display import display_markdown

# Create I/O handler
mtlxjson = core.MaterialXJson()

# Load the MaterialX file
mtlxFileName = pkg_resources.resource_filename('materialxjson', 'data/MaterialsVariantsShoe.gltf_converted.mtlx')
doc = mx.createDocument()
mx.readFromXmlFile(doc, mtlxFileName)
xmlString = core.Util.documentToXMLString(doc)

mtlxjson = core.MaterialXJson()
writeOptions = core.JsonWriteOptions()
writeOptions.indent = 1
writeOptions.separators = (',', ':')
jsonString = mtlxjson.documentToJSONString(doc, writeOptions)

xmlString = xmlString.replace('\n', '<br>')
xmlString = xmlString.replace(' ', '&nbsp;&nbsp;')
xmlString = xmlString.replace('\"', '\\"')
jsonString = jsonString.replace('\n', '<br>')
jsonString = jsonString.replace(' ', '&nbsp;&nbsp;')

output = '| JSON Format | XML Format |\n'
output = output + '| :--- | :--- |\n'
output = output + '| ' + jsonString + '| ' + xmlString + '|\n'
text = '<details open><summary><b>JSON / XML Comparison</b></summary>\n\n' + output + '\n</details>\n'
display_markdown(text, raw=True)


# %% [markdown]
# ## Additional Examples
# 
# A few additional examples are provided in the documentation `data` folder.
# 
# 1. [glTF Boombox Example](https://kwokcb.github.io/materialxjson/docs/data/gltf_pbr_boombox_mtlx.json)
# <img src="https://kwokcb.github.io/materialxjson/docs/images/gltf_pbr_boombox_mtlx.json.svg" width=100% />
# 
# 2. [Standard Surface Tiled Wood](https://kwokcb.github.io/materialxjson/docs/data/standard_surface_wood_tiled_mtlx.json)
# <img src="https://kwokcb.github.io/materialxjson/docs/images/standard_surface_wood_tiled_mtlx.json.svg" width=100% />
# 


