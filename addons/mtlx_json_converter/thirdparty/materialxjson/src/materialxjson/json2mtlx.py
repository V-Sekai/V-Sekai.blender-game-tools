#!/usr/bin/env python
'''
Command to convert from JSON to XML representation of a MaterialX document
'''
import MaterialX as mx
from materialxjson import core
import json
import os, argparse

def main():
    '''
    Command to convert from JSON to XML representation of a MaterialX document
    '''
    parser = argparse.ArgumentParser(description="Utility to convert from JSON to XML representation of a MaterialX document")
    parser.add_argument('--outputPath', dest='outputPath', default='', help='File path to output results to.')
    parser.add_argument('--upgradeVersion', dest='upgradeVersion', type=mx.stringToBoolean, default=True, help='Upgrade document version. Default is True.')
    parser.add_argument(dest="inputFileName", help="Filename of the input document or folder containing input documents")

    opts = parser.parse_args()

     # Get absolute path of opts.outputPath
    if opts.outputPath:    
        opts.outputPath = os.path.abspath(opts.outputPath)
    outputPath = mx.FilePath(opts.outputPath)
    # Check that output path exists
    if outputPath.size() > 0:
        if os.path.isdir(outputPath.asString()):
            print('Output path "%s" does not exist.' % outputPath.asString())
            exit(-1)
        else:
            print('- Write files to outputPath: '+ opts.outputPath)

    fileList = []
    extension = 'json'
    if os.path.isdir(opts.inputFileName): 
        fileList = core.Util.getFiles(opts.inputFileName, extension)
    else:
        extension = mx.FilePath(opts.inputFileName).getExtension()
        if extension == 'json':
            fileList.append(opts.inputFileName)

    if not fileList:
        print('No files found with extension "%s"' % extension)
        exit(-1)

    ## Create I/O handler
    mtlxjson = core.MaterialXJson()
    
    for fileName in fileList:

        if extension == 'json':
            if mx.FilePath(fileName).isAbsolute():
                outputFilePath = mx.FilePath(fileName.replace('.json', '_json.mtlx'))
            else:
                outputFilePath = outputPath / mx.FilePath(fileName.replace('.json', '_json.mtlx'))
            outputFileName = outputFilePath.asString()
            readOptions = core.JsonReadOptions()
            readOptions.upgradeVersion = opts.upgradeVersion
            converted = core.Util.jsonFileToXmlFile(fileName, outputFileName, readOptions)
            print('Convert JSON file "%s" -> XML file "%s". Status: %s' % (fileName, outputFileName, converted))
           
if __name__ == '__main__':
    main()
