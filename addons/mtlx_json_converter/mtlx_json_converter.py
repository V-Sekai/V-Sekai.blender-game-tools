#!/usr/bin/env python
"""
mtlx_json_converter.py
"""

"""
MIT License

Copyright (c) 2024-present K. S. Ernest (Fire) Lee           

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import argparse
import json
import MaterialX as mx
from materialxjson import core as mtlxjson 
import pkg_resources

def mtlx_to_json(mtlx_file_name):
    doc = mx.createDocument()
    mx.readFromXmlFile(doc, mtlx_file_name)
    
    mtlx_json = mtlxjson.MaterialXJson()
    json_object = mtlx_json.documentToJSON(doc)
    json_string = mtlxjson.Util.jsonToJSONString(json_object, 2)
    
    return json_string

def json_to_mtlx(json_file_name):
    json_object = mtlxjson.Util.readJson(json_file_name)
    
    mtlx_json = mtlxjson.MaterialXJson()
    doc = mx.createDocument()
    mtlx_json.documentFromJSON(json_object, doc)
    
    xml_string = mtlxjson.Util.documentToXMLString(doc)
    return xml_string

def main():
    parser = argparse.ArgumentParser(description="Convert MaterialX files to JSON and vice versa.")
    parser.add_argument("input", help="Input file name")
    parser.add_argument("output", help="Output file name")
    parser.add_argument("--to-json", action="store_true", help="Convert from MaterialX to JSON")
    parser.add_argument("--to-mtlx", action="store_true", help="Convert from JSON to MaterialX")
    
    args = parser.parse_args()
    
    if args.to_json:
        json_output = mtlx_to_json(args.input)
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f"Converted {args.input} to JSON and saved as {args.output}")
    elif args.to_mtlx:
        xml_output = json_to_mtlx(args.input)
        with open(args.output, 'w') as f:
            f.write(xml_output)
        print(f"Converted {args.input} to MaterialX and saved as {args.output}")
    else:
        print("Please specify --to-json or --to-mtlx for conversion direction.")

if __name__ == "__main__":
    main()
